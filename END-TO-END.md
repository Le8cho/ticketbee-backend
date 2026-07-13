# Prueba end-to-end en Swagger (`/docs`)

Guía paso a paso para recorrer el ciclo completo de un ticket usando la UI de Swagger del backend (`uv run uvicorn app.main:app --reload` → abrir `http://127.0.0.1:8000/docs`).

Cada paso indica: el **tag** donde está el endpoint en Swagger, el **método + ruta**, el **rol** que necesitás (ver `README.md` → Autenticación), y el body de ejemplo. Los `tag`s siguen el esquema `<Módulo>-<Rol>` (`Cliente`, `Tecnico`, `Compartido`, `Publico`).

## 0. Antes de empezar

- **Autenticación real:** cada endpoint protegido necesita un JWT de Supabase válido en el botón **Authorize** de Swagger (`Bearer <token>`), con `user_metadata.rol` en `"cliente"` o `"tecnico"` según el paso. Necesitás al menos un usuario Supabase de cada rol, con su fila correspondiente ya existente en `clientes.cliente` / `owner.tecnico` (la API no tiene endpoint de registro — la fila se crea aparte, ver `scripts/insert_dummy_data.py` o el flujo de alta que use tu equipo).
- **Atajo local:** si corrés con `.env` en `DEBUG_MODE=true` y `APP_ENV=development`, todas las dependencias de auth ignoran el token real y devuelven identidades fijas (`get_current_cliente` → cliente de prueba, `get_current_tecnico` → técnico de prueba), así que podés probar cliente/técnico sin token real. **No sirve para probar el rol `admin`** (no tiene bypass de debug) — para eso necesitás un JWT real con `user_metadata.rol="admin"`.
- **`servicio_id` requerido para crear un ticket:** no existe endpoint para listar servicios (`app/routers/catalogo.py` está vacío). Conseguilo con una consulta directa:
  ```sql
  SELECT servicio_id, nombre, precio_base FROM owner.servicio WHERE activo = 1;
  ```
- Todas las respuestas siguen el formato `{"ok": bool, "message": str, "data": any}`; los IDs que necesitás para el siguiente paso están dentro de `data`.

---

## 1. Catálogo de tipos de dispositivo *(Público)*

**`GET /api/v1/dispositivos/tipos`** — tag `Dispositivos-Publico`

Sin auth. Copiá un `tipo_dispositivo_id` de la respuesta para el paso 2.

## 2. Cliente registra un dispositivo

**`POST /api/v1/dispositivos`** — tag `Dispositivos-Cliente` — rol `cliente`

```json
{
  "tipo_dispositivo_id": 1,
  "marca": "Dell",
  "modelo": "XPS 15",
  "numero_serie": "SN-E2E-001"
}
```
Guardá el `dispositivo_id` de la respuesta.

## 3. (Opcional) Cliente sube foto del dispositivo

**`POST /api/v1/dispositivos/{dispositivo_id}/foto`** — tag `Dispositivos-Cliente` — rol `cliente`

Sube un archivo (`multipart/form-data`, campo `foto`, JPEG/PNG ≤ 5 MB). Devuelve una SAS URL válida 1 hora.

## 4. Cliente crea el ticket

**`POST /api/v1/tickets`** — tag `Tickets-Cliente` — rol `cliente`

```json
{
  "dispositivo_id": "<dispositivo_id del paso 2>",
  "servicio_id": "<servicio_id de la consulta SQL>",
  "descripcion": "El equipo no enciende al conectar el cargador."
}
```
El ticket nace en estado `EN_REVISION`. Guardá el `ticket_id`.

## 5. Técnico revisa el listado de tickets pendientes

**`GET /api/v1/tickets?estado=EN_REVISION`** — tag `Tickets-Compartido` — rol `tecnico`

Confirma que el ticket del paso 4 aparece.

## 6. Técnico acepta el ticket (fija el precio)

**`PATCH /api/v1/tickets/{ticket_id}/aceptar`** — tag `Tickets-Tecnico` — rol `tecnico`

```json
{ "precio_final": 150.00 }
```
El ticket pasa a `EN_ESPERA_PAGO` y queda asociado al técnico que aceptó.

> **Alternativa:** si en su lugar el técnico decide no atenderlo, `PATCH /api/v1/tickets/{ticket_id}/rechazar` con `{"motivo_rechazo": "..."}` (mín. 10 caracteres) lo pasa a `RECHAZADO` y termina el flujo ahí.

## 7. Generar la preferencia de pago (Mercado Pago)

**`POST /api/v1/payments/preference`** — tag `Payments-Publico`

```json
{ "ticket_id": "<ticket_id>" }
```
Devuelve un `preference_id` de Mercado Pago Checkout Pro. Requiere que el ticket esté en `EN_ESPERA_PAGO` y `MERCADOPAGO_ACCESS_TOKEN` configurado en `.env`.

## 8. Completar el pago y disparar el webhook

El paso de pago real no se hace desde Swagger: hay que completar el checkout de Mercado Pago (sandbox) con el `preference_id` del paso 7. Al aprobarse, Mercado Pago llama solo a `POST /api/v1/payments/webhook` (tag `Payments-Webhook`, sin auth — lo invoca Mercado Pago, no un usuario).

Si estás en un entorno donde el webhook no es alcanzable (sin túnel público tipo ngrok) y solo querés probar el resto del flujo, la única forma de simular la confirmación de pago es actualizar el ticket directamente en la base de datos (no hay endpoint de backend para forzarlo, por diseño — el estado solo debe cambiar por eventos reales):
```sql
UPDATE clientes.ticket SET estado = 'EN_PROGRESO' WHERE ticket_id = '<ticket_id>';
```
Cuando el webhook corre de verdad, además de mover el ticket a `EN_PROGRESO` registra el pago en `pagos.pago`, dispara un evento a Azure Service Bus y envía los correos de confirmación (cliente y técnico) vía Azure Communication Services.

## 9. Técnico sube un adjunto durante la reparación

**`POST /api/v1/tickets/{ticket_id}/adjuntos`** — tag `Tickets-Compartido` — rol `tecnico` (o `cliente`)

`multipart/form-data`, campo `archivo` (≤ 10 MB). Solo funciona con el ticket en `EN_PROGRESO`.

**`GET /api/v1/tickets/{ticket_id}/adjuntos`** — mismo tag — lista los adjuntos subidos.

## 10. Técnico confirma la entrega del dispositivo

**`PATCH /api/v1/tickets/{ticket_id}/confirmar-entrega`** — tag `Tickets-Tecnico` — rol `tecnico`

Requiere el ticket en `EN_PROGRESO`. Marca `confirmado_tecnico = true` (el ticket sigue `EN_PROGRESO` hasta que el cliente también confirme).

## 11. Cliente confirma la recepción del dispositivo

**`PATCH /api/v1/tickets/{ticket_id}/confirmar-recepcion`** — tag `Tickets-Cliente` — rol `cliente`

Requiere que el técnico ya haya confirmado (paso 10). El ticket pasa a `FINALIZADO` y se registra `fecha_finalizacion`.

## 12. Técnico registra la garantía

**`POST /api/v1/tickets/{ticket_id}/garantia`** — tag `Tickets-Tecnico` — rol `tecnico`

```json
{
  "fecha_inicio": "2026-07-12T00:00:00Z",
  "fecha_vencimiento": "2026-08-12T00:00:00Z"
}
```
Requiere el ticket en `FINALIZADO`. El número de días de garantía lo decide el técnico eligiendo `fecha_vencimiento`.

## 13. Verificar el ticket completo

**`GET /api/v1/tickets/{ticket_id}`** — tag `Tickets-Compartido` — rol `cliente` o `tecnico`

Confirmá `estado: "FINALIZADO"`, `confirmado_tecnico: true`, `confirmado_cliente: true`, `precio_final` y `fecha_finalizacion` seteados.

---

## Rama A — Incidencia cubierta por garantía

## 14. Cliente reabre el ticket por garantía

**`PATCH /api/v1/tickets/{ticket_id}/reabrir`** — tag `Tickets-Cliente` — rol `cliente`

Requiere el ticket `FINALIZADO` y la garantía del paso 12 todavía vigente (`fecha_vencimiento` en el futuro). El ticket vuelve a `EN_PROGRESO`. Repetir desde el paso 10 (confirmar entrega/recepción) para volver a cerrarlo.

## Rama B — Garantía no usada: archivado

## 15. Técnico archiva el ticket

**`PATCH /api/v1/tickets/{ticket_id}/archivar`** — tag `Tickets-Tecnico` — rol `tecnico`

Requiere el ticket `FINALIZADO`. En producción este paso lo dispara automáticamente una Azure Function cuando vence la garantía sin uso (`check warranty`, ver diagrama de arquitectura); para probarlo manualmente en Swagger simplemente se invoca aquí. El ticket pasa a `ARCHIVADO` — fin del ciclo de vida.

---

## Endpoints complementarios (fuera de la secuencia principal)

| Acción | Endpoint | Tag | Rol |
|---|---|---|---|
| Ver mi perfil | `GET /api/v1/auth/me` | `Auth-Compartido` | `cliente` / `tecnico` (no `admin`) |
| Listar mis dispositivos / todos (técnico) | `GET /api/v1/dispositivos` | `Dispositivos-Compartido` | `cliente` / `tecnico` |
| Editar un dispositivo | `PATCH /api/v1/dispositivos/{id}` | `Dispositivos-Cliente` | `cliente` |
| Dar de baja un dispositivo | `DELETE /api/v1/dispositivos/{id}` | `Dispositivos-Cliente` | `cliente` |
| Ver foto de un dispositivo | `GET /api/v1/dispositivos/{id}/foto` | `Dispositivos-Cliente` | `cliente` |
| Listar clientes (panel técnico) | `GET /api/v1/clientes` | `Clientes-Tecnico` | `tecnico` |
| Perfil completo de un cliente | `GET /api/v1/clientes/{cliente_id}` | `Clientes-Tecnico` | `tecnico` |
| Datos básicos de un técnico | `GET /api/v1/tecnicos/{tecnico_id}` | `Tecnicos-Tecnico` | `tecnico` |
| URL firmada de un adjunto | `GET /api/v1/adjuntos/{adjunto_id}/url` | `Adjuntos-Compartido` | `cliente` / `tecnico` |
| Eliminar un adjunto | `DELETE /api/v1/adjuntos/{adjunto_id}` | `Adjuntos-Tecnico` | `tecnico` |

## Probando como `admin`

El rol `admin` no tiene perfil propio y no puede usar `GET /auth/me`. Para los endpoints `-Cliente`/`-Tecnico` de esta guía (pasos 2, 3, 4, 6, 9–12, 14, 15), agregá el query param correspondiente en Swagger para indicar en nombre de quién actúa:
- `?actuar_como_cliente_id=<cliente_id existente>` en los pasos de cliente.
- `?actuar_como_tecnico_id=<tecnico_id existente>` en los pasos de técnico.

Los endpoints `-Compartido` y `-Publico` (pasos 1, 5, 7, 8, 13) funcionan igual para `admin` sin parámetros extra.
