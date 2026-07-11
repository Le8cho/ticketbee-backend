from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dispositivo import DispositivoCreate, DispositivoUpdate
from app.services.dispositivo_service import DispositivoService
from app.utils.responses import success
from app.utils.security import get_current_cliente

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB — igual que blob_storage.MAX_SIZE_IMAGEN

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
    cliente_id: UUID = Depends(get_current_cliente),
    service: DispositivoService = Depends(_service),
):
    """Devuelve todos los dispositivos activos del cliente autenticado."""
    data = await service.listar(cliente_id)
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


@router.post("/{dispositivo_id}/foto", status_code=status.HTTP_200_OK)
async def subir_foto_dispositivo(
    dispositivo_id: UUID,
    foto: UploadFile = File(...),
    cliente_id: UUID = Depends(get_current_cliente),
    service: DispositivoService = Depends(_service),
):
    """Sube o reemplaza la foto del dispositivo. Devuelve SAS URL válida 1 hora."""
    data = await foto.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen supera el límite de 5 MB.",
        )
    sas_url = await service.subir_foto(dispositivo_id, cliente_id, data, foto.content_type or "")
    return success({"url": sas_url})


@router.get("/{dispositivo_id}/foto")
async def obtener_foto_dispositivo(
    dispositivo_id: UUID,
    cliente_id: UUID = Depends(get_current_cliente),
    service: DispositivoService = Depends(_service),
):
    """Devuelve una SAS URL firmada (1 hora) para ver la foto del dispositivo."""
    sas_url = await service.obtener_url_foto(dispositivo_id, cliente_id)
    return success({"url": sas_url})
