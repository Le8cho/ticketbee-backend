import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ticket import TicketEstado
from app.schemas.ticket import (
    TicketAceptar,
    TicketCrear,
    TicketListItem,
    TicketRechazar,
    TicketResponse,
)
from app.services import ticket_service as service
from app.core.responses import error, success

# CORREGIR CUANDO LAS PRUEBAS HAYAN TERMINADO
from app.core.security import (
    UsuarioActual,
    get_current_user_dev as get_current_user,
    get_current_user_dev as require_cliente,
    get_current_user_dev as require_tecnico,
)

router = APIRouter()


# Cliente
# --------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_ticket(
    payload: TicketCrear,
    usuario: UsuarioActual = Depends(require_cliente),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.crear_ticket(db, usuario.user_id, payload)
    return success(ticket.model_dump(mode="json"), "Ticket creado.", status.HTTP_201_CREATED)


@router.patch("/{ticket_id}/confirmar-recepcion")
async def confirmar_recepcion(
    ticket_id: uuid.UUID,
    usuario: UsuarioActual = Depends(require_cliente),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.confirmar_recepcion_cliente(db, ticket_id, usuario.user_id)
    return success(ticket.model_dump(mode="json"), "Recepción confirmada. Ticket finalizado.")


@router.patch("/{ticket_id}/reabrir")
async def reabrir_ticket(
    ticket_id: uuid.UUID,
    usuario: UsuarioActual = Depends(require_cliente),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.reabrir_por_garantia(db, ticket_id, usuario.user_id)
    return success(ticket.model_dump(mode="json"), "Ticket reabierto por incidencia de garantía.")


# Técnico
# --------------------------------------

@router.patch("/{ticket_id}/aceptar")
async def aceptar_ticket(
    ticket_id: uuid.UUID,
    payload: TicketAceptar,
    usuario: UsuarioActual = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.aceptar_ticket(db, ticket_id, usuario.user_id, payload)
    return success(ticket.model_dump(mode="json"), "Ticket aceptado.")


@router.patch("/{ticket_id}/rechazar")
async def rechazar_ticket(
    ticket_id: uuid.UUID,
    payload: TicketRechazar,
    usuario: UsuarioActual = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.rechazar_ticket(db, ticket_id, usuario.user_id, payload)
    return success(ticket.model_dump(mode="json"), "Ticket rechazado.")


@router.patch("/{ticket_id}/confirmar-entrega")
async def confirmar_entrega(
    ticket_id: uuid.UUID,
    usuario: UsuarioActual = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.confirmar_entrega_tecnico(db, ticket_id, usuario.user_id)
    return success(ticket.model_dump(mode="json"), "Entrega confirmada.")


@router.patch("/{ticket_id}/archivar")
async def archivar_ticket(
    ticket_id: uuid.UUID,
    usuario: UsuarioActual = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    await service.archivar_ticket(db, ticket_id)
    return success(None, "Ticket archivado.")


# Compartidos
# --------------------------------------

@router.get("/{ticket_id}", response_model=None)
async def obtener_ticket(
    ticket_id: uuid.UUID,
    usuario: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    es_tecnico = usuario.rol == "tecnico"
    ticket = await service.obtener_ticket(db, ticket_id, usuario.user_id, es_tecnico)
    return success(ticket.model_dump(mode="json"), "OK")


@router.get("", response_model=None)
async def listar_tickets(
    estado: Optional[TicketEstado] = None,
    usuario: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if usuario.rol == "tecnico":
        tickets = await service.listar_tickets_tecnico(db, estado)
    else:
        tickets = await service.listar_tickets_cliente(db, usuario.user_id)
    return success([t.model_dump(mode="json") for t in tickets], "OK")