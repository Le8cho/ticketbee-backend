import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adjunto import Adjunto, SubidoPor


class AdjuntoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        adjunto_id: uuid.UUID,
        ticket_id: uuid.UUID,
        nombre: str,
        tipo_mime: str,
        tamanio_bytes: int,
        blob_url: str,
        subido_por: SubidoPor,
    ) -> Adjunto:
        adjunto = Adjunto(
            adjunto_id=adjunto_id,
            ticket_id=ticket_id,
            nombre=nombre,
            tipo_mime=tipo_mime,
            tamanio_bytes=tamanio_bytes,
            blob_url=blob_url,
            subido_por=subido_por,
        )
        self.db.add(adjunto)
        await self.db.commit()
        await self.db.refresh(adjunto)
        return adjunto

    async def get_by_id(self, adjunto_id: uuid.UUID) -> Adjunto | None:
        result = await self.db.execute(
            select(Adjunto).where(Adjunto.adjunto_id == adjunto_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ticket(self, ticket_id: uuid.UUID) -> list[Adjunto]:
        result = await self.db.execute(
            select(Adjunto)
            .where(Adjunto.ticket_id == ticket_id)
            .order_by(Adjunto.subido_en.desc())
        )
        return list(result.scalars().all())

    async def delete(self, adjunto: Adjunto) -> None:
        await self.db.delete(adjunto)
        await self.db.commit()
