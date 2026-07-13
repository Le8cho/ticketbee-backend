import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.cliente_service import ClienteService
from app.core.responses import success, error
from app.core.security import UsuarioActual, get_current_tecnico, get_current_user

EstadoTicket = Literal["EN_REVISION", "EN_ESPERA_PAGO", "EN_PROGRESO", "FINALIZADO", "RECHAZADO", "ARCHIVADO", "CANCELADO"]
TipoServicio = Literal["PREVENTIVO", "CORRECTIVO", "SUSCRIPCION_SOFTWARE"]

router = APIRouter()


@router.post(
    "/registro",
    summary="Auto-registro del cliente (puente Supabase -> Azure SQL)",
    description="Crea la fila en clientes.cliente para el usuario ya autenticado en Supabase "
                "(rol=cliente). Idempotente: si ya existe, la devuelve sin modificarla (200).",
    tags=["Clientes-Cliente"],
)
async def registrar_cliente(
    usuario: Annotated[UsuarioActual, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if usuario.rol != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el rol cliente puede autoregistrarse.",
        )
    service = ClienteService(db)
    cliente, creado = await service.registrar_desde_supabase(usuario)
    mensaje = "Cliente registrado." if creado else "El cliente ya estaba registrado."
    status_code = status.HTTP_201_CREATED if creado else status.HTTP_200_OK
    return success(cliente.model_dump(mode="json"), message=mensaje, status_code=status_code)


@router.get(
    "",
    summary="Listar clientes",
    description="Devuelve todos los clientes activos con su conteo de tickets activos y estado "
                "del último ticket. Solo accesible para el técnico. Admite filtros opcionales.",
    tags=["Clientes-Tecnico"],
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
    tags=["Clientes-Tecnico"],
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
