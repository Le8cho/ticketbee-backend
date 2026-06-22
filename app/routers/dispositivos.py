from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dispositivo import DispositivoCreate, DispositivoUpdate
from app.services.dispositivo_service import DispositivoService
from app.core.responses import success
from app.core.security import get_current_cliente, get_current_user, UsuarioActual

router = APIRouter()


def _service(db: AsyncSession = Depends(get_db)) -> DispositivoService:
    return DispositivoService(db)


@router.get("/tipos")
async def listar_tipos(service: DispositivoService = Depends(_service)):
    """Devuelve los tipos de dispositivo activos del catálogo."""
    data = await service.listar_tipos()
    return success([t.model_dump() for t in data])


@router.post("", status_code=status.HTTP_201_CREATED)
async def registrar_dispositivo(
    body: DispositivoCreate,
    cliente_id: UUID = Depends(get_current_cliente),
    service: DispositivoService = Depends(_service),
):
    """Registra un nuevo dispositivo en el inventario del cliente autenticado."""
    data = await service.registrar(cliente_id, body)
    return success(data.model_dump(mode="json"), status_code=status.HTTP_201_CREATED)


@router.get("")
async def listar_dispositivos(
    usuario: UsuarioActual = Depends(get_current_user),
    service: DispositivoService = Depends(_service),
    tipo_dispositivo_id: int | None = None,
    estado_ticket: str | None = None,
    servicio_id: UUID | None = None,
    cliente_id: UUID | None = None,
):
    """Técnico: todos los dispositivos activos (con filtros opcionales). Cliente: solo los suyos."""
    if usuario.rol == "tecnico":
        data = await service.listar_todos(
            tipo_dispositivo_id=tipo_dispositivo_id,
            estado_ticket=estado_ticket,
            servicio_id=servicio_id,
            cliente_id=cliente_id,
        )
    else:
        data = await service.listar(
            cliente_id=usuario.user_id,
            tipo_dispositivo_id=tipo_dispositivo_id,
            estado_ticket=estado_ticket,
            servicio_id=servicio_id,
        )
    return success([d.model_dump(mode="json") for d in data])


@router.patch("/{dispositivo_id}")
async def actualizar_dispositivo(
    dispositivo_id: UUID,
    body: DispositivoUpdate,
    cliente_id: UUID = Depends(get_current_cliente),
    service: DispositivoService = Depends(_service),
):
    """Actualiza marca, modelo, número de serie o foto de un dispositivo del cliente."""
    data = await service.actualizar(dispositivo_id, cliente_id, body)
    return success(data.model_dump(mode="json"))


@router.delete("/{dispositivo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def desactivar_dispositivo(
    dispositivo_id: UUID,
    cliente_id: UUID = Depends(get_current_cliente),
    service: DispositivoService = Depends(_service),
):
    """Borrado lógico manual: marca el dispositivo como inactivo (activo=False)."""
    await service.desactivar(dispositivo_id, cliente_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
