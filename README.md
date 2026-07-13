# TechFix Backend

Backend FastAPI para **TechFix**, una plataforma de gestión de reparaciones técnicas. Los clientes registran dispositivos y crean tickets de servicio; el técnico los revisa, aprueba y gestiona el ciclo completo hasta el archivado automático.

## Comandos

```bash
# Arrancar el servidor de desarrollo
uv run uvicorn app.main:app --reload

# Ejecutar todos los tests de integración
uv run pytest tests/integration/ -v

# Ejecutar un test específico
uv run pytest tests/integration/test_clientes.py::TestListarClientes::test_devuelve_200 -v

# Ejecutar una clase de tests completa
uv run pytest tests/integration/test_clientes.py::TestPerfilCliente -v

# Linter
uv run ruff check .
uv run ruff format .

# Migraciones Alembic
uv run alembic current                          # ver versión actual en BD
uv run alembic revision --autogenerate -m "descripcion"   # generar migración
uv run alembic upgrade head                     # aplicar migraciones pendientes
uv run alembic downgrade -1                     # revertir última migración
```

Los tests corren contra la **base de datos real de Azure SQL** (no hay mocks de BD). Requieren `.env` configurado con `DATABASE_URL` válido.

## Arquitectura

### Stack
- **FastAPI** con rutas async, **SQLAlchemy 2.0** async ORM, **Azure SQL Server** (driver `pyodbc`/`aioodbc`, dialecto `mssql+aioodbc`)
- **Alembic** para migraciones con soporte multi-schema
- **Supabase Auth** para identidad (el backend valida JWTs firmados por Supabase vía JWKS; no hay password ni tablas de auth locales)
- **Azure Service Bus** (notificaciones), **Azure Blob Storage** (adjuntos) y **Azure Communication Services** (envío de correo) — infraestructura en `app/infrastructure/`
- **Mercado Pago** para el checkout de pagos (webhook + preferencias)

> **Nota histórica:** el proyecto arrancó sobre Supabase/PostgreSQL y luego migró a Azure SQL Server. La base de datos, los tipos de columna (`UNIQUEIDENTIFIER`, enums como `VARCHAR` vía `SAEnum(..., native_enum=False)`) y Alembic ya reflejan Azure SQL. **La autenticación sigue siendo Supabase Auth** (JWT + JWKS) — eso no cambió con la migración de base de datos.

### Capas (por módulo)
```
router → service → repository → model (ORM)
                              → schema (Pydantic)
```
Cada módulo sigue exactamente esta jerarquía. El router nunca toca el repositorio directamente.

### Schemas de base de datos (Azure SQL)
Las tablas están divididas en tres schemas:

| Schema | Tablas |
|--------|--------|
| `owner` | `tecnico`, `tipo_dispositivo`, `servicio` |
| `clientes` | `cliente`, `dispositivo`, `ticket`, `ticket_dispositivo`, `garantia`, `adjunto` |
| `pagos` | `pago` |

**Importante:** todos los modelos SQLAlchemy deben declarar `__table_args__ = {"schema": "..."}`. Las FK deben usar la forma `schema.tabla.columna` (ej. `"clientes.cliente.cliente_id"`).

### Tipos de UUID
Todos los modelos usan `UNIQUEIDENTIFIER` de `sqlalchemy.dialects.mssql`.

### Enums
No se usan enums nativos de BD. Se declaran como `Enum` de Python (`str, enum.Enum`) mapeados con `SAEnum(MiEnum, native_enum=False, length=N)`, que SQLAlchemy almacena como `VARCHAR` con validación a nivel de aplicación. Enums actuales: `TicketEstado` (`app/models/ticket.py`), `PagoEstado` (`app/models/pago.py`), `SubidoPor` (`app/models/adjunto.py`), y el `tipo_servicio` de `Servicio` (`app/models/servicio.py`, sin clase Python dedicada).

### Autenticación
`app/core/security.py` valida el JWT de Supabase Auth contra las JWKS de `SUPABASE_URL` y expone tres dependencias FastAPI:
- `get_current_user` → devuelve `UsuarioActual(user_id, rol)`, para endpoints donde varios roles pueden entrar pero el comportamiento cambia según `rol`
- `get_current_cliente` → devuelve `uuid.UUID` del cliente en cuyo nombre se actúa, exige `rol="cliente"` (o `rol="admin"`, ver abajo) en el JWT (`user_metadata.rol`)
- `get_current_tecnico` → igual, exige `rol="tecnico"` (o `rol="admin"`)

El JWT lo emite Supabase; el rol se lee de `payload["user_metadata"]["rol"]`.

**Rol `admin`:** no tiene fila propia en `cliente` ni `tecnico` (sin nombre/email/perfil) y no puede usar `GET /auth/me` (responde 403). Tiene acceso a todos los demás endpoints. Para los endpoints que dependen de `get_current_cliente`/`get_current_tecnico` — que insertan o filtran filas por una FK real (`dispositivo.cliente_id`, `ticket.cliente_id`, `ticket.tecnico_id`) — el admin no puede actuar con su propia identidad porque no existe como fila en esas tablas. En su lugar, indica explícitamente en cuyo nombre actúa vía query param:
- `?actuar_como_cliente_id=<uuid>` — para endpoints cliente-scoped (crear ticket, registrar dispositivo, etc.); debe ser un `cliente_id` que exista en `clientes.cliente`.
- `?actuar_como_tecnico_id=<uuid>` — para endpoints técnico-scoped (aceptar ticket, confirmar entrega, etc.); debe ser un `tecnico_id` que exista en `owner.tecnico`.

Si el rol es `admin` y falta el query param correspondiente, la dependencia responde `400`. Para `cliente`/`tecnico` el parámetro se ignora (usan su propio `user_id`). En los endpoints "Compartido" (`get_current_user`, ej. listar tickets/dispositivos, adjuntos), el admin ve todo lo que ve un técnico — no necesita parámetro adicional porque esos endpoints no insertan filas propias.

En modo `DEBUG_MODE=true` + `APP_ENV=development`, las tres dependencias devuelven identidades fijas (`_DEBUG_CLIENTE_ID` / `_DEBUG_TECNICO_ID`) sin validar ningún token — útil para desarrollo local, pero hay que tenerlo presente al escribir tests: sobreescribir `get_current_cliente` en un test **no** cubre los endpoints que dependen de `get_current_user`, porque son dependencias distintas (ver la sección de tests). El bypass de `DEBUG_MODE` no tiene equivalente para `admin`; para probar ese rol hace falta un JWT real con `user_metadata.rol="admin"` (`DEBUG_MODE=false`) o un `dependency_overrides` en tests.

Usarlo así en cualquier endpoint protegido:
```python
from app.core.security import get_current_tecnico

async def mi_endpoint(
    tecnico_id: Annotated[uuid.UUID, Depends(get_current_tecnico)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
```

### Convención de tags en Swagger (`/docs`)
Cada endpoint declara su propio `tags=["<Módulo>-<Rol>"]` en el decorador de ruta (no a nivel de router), para que en Swagger quede claro de un vistazo qué rol necesitás simular para probarlo:

- `<Módulo>-Cliente` — requiere `get_current_cliente` (JWT con `rol="cliente"`)
- `<Módulo>-Tecnico` — requiere `get_current_tecnico` (JWT con `rol="tecnico"`)
- `<Módulo>-Compartido` — requiere `get_current_user` (cualquier rol autenticado); el comportamiento puede variar según `usuario.rol` dentro del handler
- `<Módulo>-Publico` — sin dependencia de autenticación

Ejemplo: `Tickets-Cliente` agrupa `POST /tickets`, `PATCH /tickets/{id}/confirmar-recepcion` y `PATCH /tickets/{id}/reabrir`; `Tickets-Tecnico` agrupa `aceptar`, `rechazar`, `confirmar-entrega`, `archivar` y `garantia`; `Tickets-Compartido` agrupa las lecturas y los adjuntos.

No hay tag `Admin` por endpoint: el admin tiene acceso a todos los endpoints salvo `GET /auth/me`, así que no hace falta anotarlo caso por caso. Al probar un endpoint `-Cliente` o `-Tecnico` como admin en Swagger, agregar el query param `actuar_como_cliente_id`/`actuar_como_tecnico_id` correspondiente (ver sección de Autenticación).

### Respuestas HTTP
Usar siempre `success()` y `error()` de `app/core/responses.py`:
```python
return success(data.model_dump(mode="json"))      # mode="json" serializa datetime/UUID
return error("mensaje", status_code=404)
```
Estructura de respuesta: `{"ok": bool, "message": str, "data": any}`.

### Tests de integración
El `conftest.py` reemplaza el engine por uno con `NullPool` para evitar conflictos de event loop entre tests. Los tests usan `app.dependency_overrides`, que es un diccionario **global y compartido** por todos los archivos de test dentro del mismo proceso de pytest — hay que scoparlo con una fixture `module`-scoped y limpiarlo al terminar, o un archivo puede pisar el override de otro:
```python
@pytest.fixture(scope="module", autouse=True)
def _override_auth():
    app.dependency_overrides[get_current_tecnico] = lambda: uuid.UUID("00000000-0000-0000-0000-000000000001")
    yield
    app.dependency_overrides.pop(get_current_tecnico, None)
```
Ojo: `get_current_user_dev` es literalmente el mismo objeto que `get_current_user` (alias definido en `app/core/security.py`); sobreescribir uno sobreescribe el otro.

### Modelos stub
Varios modelos tienen comentarios `# Persona N: agregar aquí...` — son stubs mínimos creados para satisfacer FKs entre módulos. Cada persona completa su propio modelo sin eliminar las columnas y relaciones ya declaradas.

## Estructura de ramas
El equipo trabaja con ramas por módulo. No hacer push directo a `main`.

| Rama | Módulo |
|------|--------|
| `emir-auth` | Autenticación, modelos base |
| `alexoo-dispositivos` | Dispositivos y tipos |
| `back-n2/tickets` | Tickets y ciclo de vida |
| `back-n4-clientes` | Gestión de clientes (panel técnico) |
| `pagos` | Integración de pagos (Mercado Pago, webhook, Service Bus) |

## Variables de entorno
Ver `.env.example`. La única obligatoria para desarrollo es `DATABASE_URL`, en formato `mssql+aioodbc://usuario:password@servidor:1433/basedatos?driver=ODBC+Driver+18+for+SQL+Server` (Azure SQL). `SUPABASE_URL` es obligatoria para que la validación de JWT funcione fuera de `DEBUG_MODE`.
