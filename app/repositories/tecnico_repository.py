import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tecnico import Tecnico


async def obtener_por_id(db: AsyncSession, tecnico_id: uuid.UUID) -> Tecnico | None:
    result = await db.execute(
        select(Tecnico).where(Tecnico.tecnico_id == tecnico_id)
    )
    return result.scalar_one_or_none()
