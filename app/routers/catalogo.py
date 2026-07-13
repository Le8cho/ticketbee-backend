from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success
from app.core.security import UsuarioActual, get_current_tecnico, get_current_user
from app.schemas.servicio import ServicioCreate, ServicioUpdate
from app.services.catalogo_service import CatalogoService

router = APIRouter()


def _service(db: AsyncSession = Depends(get_db)) -> CatalogoService:
    return CatalogoService(db)


@router.get("/servicios", tags=["Catalogo-Compartido"])
async def listar_servicios(
    usuario: UsuarioActual = Depends(get_current_user),
    service: CatalogoService = Depends(_service),
):
    """Técnico/admin ven el catálogo completo (incl. inactivos). Cliente ve solo los activos (selector de ticket)."""
    if usuario.rol in ("tecnico", "admin"):
        data = await service.listar_todos()
    else:
        data = await service.listar_activos()
    return success([s.model_dump(mode="json") for s in data])


@router.post("/servicios", status_code=status.HTTP_201_CREATED, tags=["Catalogo-Tecnico"])
async def crear_servicio(
    body: ServicioCreate,
    _: UUID = Depends(get_current_tecnico),
    service: CatalogoService = Depends(_service),
):
    """Agrega un nuevo servicio al catálogo."""
    data = await service.crear(body)
    return success(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.patch("/servicios/{servicio_id}", tags=["Catalogo-Tecnico"])
async def actualizar_servicio(
    servicio_id: UUID,
    body: ServicioUpdate,
    _: UUID = Depends(get_current_tecnico),
    service: CatalogoService = Depends(_service),
):
    """Edita nombre/tipo/precio de un servicio, o lo activa/desactiva (campo `activo`)."""
    data = await service.actualizar(servicio_id, body)
    return success(data.model_dump(mode="json"))
