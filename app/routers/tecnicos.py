import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_tecnico
from app.core.responses import success
from app.services import tecnico_service as service

router = APIRouter()


@router.get(
    "/{tecnico_id}",
    summary="Datos basicos de un tecnico",
    description="Devuelve nombre y email de un tecnico por su ID. Uso interno "
                "(ej. notificaciones cuando se reabre un ticket por garantia).",
)
async def obtener_tecnico(
    tecnico_id: uuid.UUID,
    _: Annotated[uuid.UUID, Depends(get_current_tecnico)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tecnico = await service.obtener_tecnico(db, tecnico_id)
    return success(tecnico.model_dump(mode="json"))
