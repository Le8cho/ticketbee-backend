# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

**TechFix** — backend FastAPI para una plataforma de gestión de reparaciones técnicas. Los clientes registran dispositivos y crean tickets de servicio; el técnico los revisa, aprueba y gestiona el ciclo completo hasta el archivado automático.

## Comandos

```bash
# Arrancar el servidor de desarrollo
uv run uvicorn main:app --reload

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

Los tests corren contra **Supabase real** (no hay mocks de BD). Requieren `.env` configurado con `DATABASE_URL` válido.

## Arquitectura

### Stack
- **FastAPI** con rutas async, **SQLAlchemy 2.0** async ORM, **PostgreSQL** en Supabase (driver `asyncpg`)
- **Alembic** para migraciones con soporte multi-schema
- **PyJWT** + **passlib[bcrypt]** para autenticación
- **Azure Service Bus** (notificaciones) y **Azure Blob Storage** (adjuntos) — stubs en `app/infrastructure/`

### Capas (por módulo)
```
router → service → repository → model (ORM)
                              → schema (Pydantic)
```
Cada módulo sigue exactamente esta jerarquía. El router nunca toca el repositorio directamente.

### Schemas de base de datos (Supabase)
Las tablas están divididas en tres schemas PostgreSQL:

| Schema | Tablas |
|--------|--------|
| `owner` | `tecnico`, `tipo_dispositivo`, `servicio` |
| `clientes` | `cliente`, `dispositivo`, `ticket`, `ticket_dispositivo`, `garantia`, `adjunto`, `comprobante` |
| `pagos` | `pago`, `pago_parcial` |

**Importante:** todos los modelos SQLAlchemy deben declarar `__table_args__ = {"schema": "..."}`. Las FK deben usar la forma `schema.tabla.columna` (ej. `"clientes.cliente.cliente_id"`).

### Tipos PostgreSQL personalizados
La BD usa ENUMs nativos. Los modelos deben declararlos con `ENUM(name="...", schema="...", create_type=False)` — `create_type=False` es obligatorio porque los tipos ya existen en Supabase.

| Enum | Schema | Valores |
|------|--------|---------|
| `ticket_estado_enum` | `clientes` | `CREADO`, `EN_ESPERA_PAGO`, `EN_PROGRESO`, `FINALIZADO`, `RECHAZADO`, `ARCHIVADO` |
| `tipo_servicio_enum` | `owner` | `PREVENTIVO`, `CORRECTIVO`, `SUSCRIPCION_SOFTWARE` |
| `pago_estado_enum` | `pagos` | `CONFIRMADO` |
| `pago_parcial_estado_enum` | `pagos` | `PENDIENTE`, `RESUELTO` |
| `subido_por_enum` | `clientes` | `TECNICO`, `CLIENTE` |

### Tipos de UUID
Todos los modelos usan `PG_UUID(as_uuid=True)` de `sqlalchemy.dialects.postgresql`. **Pendiente:** migrar a `sqlalchemy.Uuid` (portable) cuando se migre a Azure SQL Server.

### Autenticación
`app/utils/security.py` expone dos dependencias FastAPI:
- `get_current_cliente` → devuelve `uuid.UUID` del cliente autenticado, exige `rol="cliente"` en el JWT
- `get_current_tecnico` → igual, exige `rol="tecnico"`

El JWT tiene payload `{sub: uuid, rol: str, exp, iat}`. Usarlo así en cualquier endpoint protegido:
```python
from app.utils.security import get_current_tecnico

async def mi_endpoint(
    tecnico_id: Annotated[uuid.UUID, Depends(get_current_tecnico)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
```

### Respuestas HTTP
Usar siempre `success()` y `error()` de `app/utils/responses.py`:
```python
return success(data.model_dump(mode="json"))      # mode="json" serializa datetime/UUID
return error("mensaje", status_code=404)
```
Estructura de respuesta: `{"ok": bool, "message": str, "data": any}`.

### Tests de integración
El `conftest.py` reemplaza el engine por uno con `NullPool` para evitar conflictos de event loop entre tests. El patrón estándar para mockear auth:
```python
app.dependency_overrides[get_current_tecnico] = lambda: uuid.UUID("00000000-0000-0000-0000-000000000001")
```

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

## Variables de entorno
Ver `.env.example`. La única obligatoria para desarrollo es `DATABASE_URL` (formato `postgresql+asyncpg://...`). Supabase requiere el host del **pooler** (`aws-1-us-east-2.pooler.supabase.com`), no el host directo (solo IPv6).
