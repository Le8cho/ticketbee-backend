import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

EstadoTicket = Literal["EN_REVISION", "EN_ESPERA_PAGO", "EN_PROGRESO", "FINALIZADO", "RECHAZADO", "ARCHIVADO", "CANCELADO"]
TipoServicio = Literal["PREVENTIVO", "CORRECTIVO", "SUSCRIPCION_SOFTWARE"]

from app.core.database import get_db
from app.schemas.cliente import ClienteListItem, ClienteProfile
from app.services.cliente_service import ClienteService
from app.core.responses import success, error
from app.core.security import get_current_tecnico

router = APIRouter()


@router.get(
    "",
    summary="Listar clientes",
    description="Devuelve todos los clientes activos con su conteo de tickets activos y estado "
                "del último ticket. Solo accesible para el técnico. Admite filtros opcionales.",
)
async def list_clientes(
    tecnico_id: Annotated[uuid.UUID, Depends(get_current_tecnico)],
    db: Annotated[AsyncSession, Depends(get_db)],
    estado_ticket: Annotated[EstadoTicket | None, Query(description="Filtrar por estado de ticket (EN_REVISION, EN_ESPERA_PAGO, EN_PROGRESO, FINALIZADO, RECHAZADO, ARCHIVADO, CANCELADO)")] = None,
    distrito: Annotated[str | None, Query(description="Filtrar por distrito del cliente")] = None,
    fecha_desde: Annotated[datetime | None, Query(description="Filtrar clientes registrados desde esta fecha (ISO 8601)")] = None,
    tipo_ultimo_ticket: Annotated[TipoServicio | None, Query(description="Filtrar por tipo del último servicio (PREVENTIVO, CORRECTIVO, SUSCRIPCION_SOFTWARE)")] = None,
):
    service = ClienteService(db)
    clientes = await service.list_clientes(
        estado_ticket=estado_ticket,
        distrito=distrito,
        fecha_desde=fecha_desde,
        tipo_ultimo_ticket=tipo_ultimo_ticket,
    )
    return success([c.model_dump(mode="json") for c in clientes])


@router.get(
    "/{cliente_id}",
    summary="Perfil de cliente",
    description="Devuelve el perfil completo del cliente: datos de contacto, dispositivos "
                "registrados y el historial de tickets agrupado por dispositivo. Solo técnico.",
)
async def get_cliente_profile(
    cliente_id: uuid.UUID,
    tecnico_id: Annotated[uuid.UUID, Depends(get_current_tecnico)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    service = ClienteService(db)
    profile = await service.get_cliente_profile(cliente_id)
    if not profile:
        return error("Cliente no encontrado", status_code=status.HTTP_404_NOT_FOUND)
    return success(profile.model_dump(mode="json"))
