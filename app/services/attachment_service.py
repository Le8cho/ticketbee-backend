import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.blob_storage import (
    delete_blob,
    generate_sas_url,
    upload_blob,
    validar_adjunto,
)
from app.models.adjunto import SubidoPor
from app.models.ticket import Ticket, TicketEstado
from app.repositories.adjunto_repository import AdjuntoRepository
from app.schemas.adjunto import AdjuntoOut


class AttachmentService:
    def __init__(self, db: AsyncSession):
        self.repo = AdjuntoRepository(db)
        self.db = db

    async def _get_ticket_en_progreso(self, ticket_id: uuid.UUID) -> Ticket:
        result = await self.db.execute(
            select(Ticket).where(Ticket.ticket_id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado")
        if ticket.estado != TicketEstado.EN_PROGRESO:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo se pueden subir adjuntos a tickets en estado EN_PROGRESO",
            )
        return ticket

    async def subir_adjunto(
        self,
        ticket_id: uuid.UUID,
        rol: str,
        nombre_archivo: str,
        data: bytes,
        content_type: str,
    ) -> tuple[AdjuntoOut, str]:
        """Valida, sube el archivo y registra el adjunto. Devuelve (AdjuntoOut, sas_url)."""
        try:
            validar_adjunto(data, content_type)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        await self._get_ticket_en_progreso(ticket_id)

        subido_por = SubidoPor.TECNICO if rol == "tecnico" else SubidoPor.CLIENTE
        adjunto_id = uuid.uuid4()
        blob_name = f"{ticket_id}/{adjunto_id}"

        blob_url = await upload_blob(
            settings.AZURE_STORAGE_CONTAINER_TICKETS,
            blob_name,
            data,
            content_type,
        )

        adjunto = await self.repo.create(
            adjunto_id=adjunto_id,
            ticket_id=ticket_id,
            nombre=nombre_archivo,
            tipo_mime=content_type,
            tamanio_bytes=len(data),
            blob_url=blob_url,
            subido_por=subido_por,
        )
        sas_url = await generate_sas_url(settings.AZURE_STORAGE_CONTAINER_TICKETS, blob_name)
        return AdjuntoOut.model_validate(adjunto), sas_url

    async def listar_adjuntos(self, ticket_id: uuid.UUID) -> list[AdjuntoOut]:
        adjuntos = await self.repo.get_by_ticket(ticket_id)
        return [AdjuntoOut.model_validate(a) for a in adjuntos]

    async def obtener_sas_url(self, adjunto_id: uuid.UUID) -> str:
        adjunto = await self.repo.get_by_id(adjunto_id)
        if not adjunto:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjunto no encontrado")
        blob_name = f"{adjunto.ticket_id}/{adjunto.adjunto_id}"
        return await generate_sas_url(settings.AZURE_STORAGE_CONTAINER_TICKETS, blob_name)

    async def eliminar_adjunto(self, adjunto_id: uuid.UUID, rol: str) -> None:
        if rol != "tecnico":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el técnico puede eliminar adjuntos")
        adjunto = await self.repo.get_by_id(adjunto_id)
        if not adjunto:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjunto no encontrado")
        blob_name = f"{adjunto.ticket_id}/{adjunto.adjunto_id}"
        await delete_blob(settings.AZURE_STORAGE_CONTAINER_TICKETS, blob_name)
        await self.repo.delete(adjunto)
