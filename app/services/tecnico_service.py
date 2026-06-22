import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import tecnico_repository as repo
from app.schemas.tecnico import TecnicoOut


async def obtener_tecnico(db: AsyncSession, tecnico_id: uuid.UUID) -> TecnicoOut:
    tecnico = await repo.obtener_por_id(db, tecnico_id)
    if not tecnico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Técnico no encontrado.")
    return TecnicoOut.model_validate(tecnico)
