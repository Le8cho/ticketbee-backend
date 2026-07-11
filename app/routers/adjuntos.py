import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.attachment_service import AttachmentService
from app.utils.responses import success
from app.utils.security import UsuarioActual, get_current_user_dev as get_current_user

router = APIRouter()


def _service(db: AsyncSession = Depends(get_db)) -> AttachmentService:
    return AttachmentService(db)


@router.get("/{adjunto_id}/url")
async def obtener_url_adjunto(
    adjunto_id: uuid.UUID,
    usuario: UsuarioActual = Depends(get_current_user),
    service: AttachmentService = Depends(_service),
):
    """Devuelve una SAS URL firmada (1 hora) para descargar o visualizar el adjunto."""
    sas_url = await service.obtener_sas_url(adjunto_id)
    return success({"url": sas_url})


@router.delete("/{adjunto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_adjunto(
    adjunto_id: uuid.UUID,
    usuario: UsuarioActual = Depends(get_current_user),
    service: AttachmentService = Depends(_service),
):
    """Elimina el adjunto del blob storage y de la base de datos. Solo técnico."""
    await service.eliminar_adjunto(adjunto_id, usuario.rol)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
