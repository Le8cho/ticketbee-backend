import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import TicketEstado
from app.repositories import ticket_repository as repo
from app.schemas.ticket import (
    TicketAceptar,
    TicketCrear,
    TicketListItem,
    TicketRechazar,
    TicketResponse,
)

from app.infrastructure.service_bus import publicar_evento_ticket


# Helper interno
# -------------------------------------------

def _a_response(ticket, ocultar_motivo: bool = False) -> TicketResponse:
    dispositivo_id = (
        ticket.dispositivos[0].dispositivo_id if ticket.dispositivos else None
    )
    return TicketResponse(
        ticket_id=ticket.ticket_id,
        cliente_id=ticket.cliente_id,
        servicio_id=ticket.servicio_id,
        tecnico_id=ticket.tecnico_id,
        dispositivo_id=dispositivo_id,
        estado=ticket.estado,
        descripcion=ticket.descripcion,
        precio_base=ticket.precio_base,
        precio_final=ticket.precio_final,
        motivo_rechazo=None if ocultar_motivo else ticket.motivo_rechazo,
        confirmado_tecnico=ticket.confirmado_tecnico,
        confirmado_cliente=ticket.confirmado_cliente,
        fecha_finalizacion=ticket.fecha_finalizacion,
        creado_en=ticket.creado_en,
        actualizado_en=ticket.actualizado_en,
    )


def _a_list_item(ticket) -> TicketListItem:
    dispositivo_id = (
        ticket.dispositivos[0].dispositivo_id if ticket.dispositivos else None
    )
    return TicketListItem(
        ticket_id=ticket.ticket_id,
        estado=ticket.estado,
        servicio_id=ticket.servicio_id,
        dispositivo_id=dispositivo_id,
        precio_base=ticket.precio_base,
        precio_final=ticket.precio_final,
        creado_en=ticket.creado_en,
    )


# Queries auxiliares
# -------------------------------------------

async def _obtener_precio_base(db: AsyncSession, servicio_id: uuid.UUID) -> float:
    result = await db.execute(
        text("SELECT precio_base FROM owner.SERVICIO WHERE servicio_id = :id AND activo = 1"),
        {"id": str(servicio_id)},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado o inactivo.",
        )
    return float(row[0])


async def _validar_dispositivo_del_cliente(
    db: AsyncSession,
    dispositivo_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> None:
    result = await db.execute(
        text(
            "SELECT 1 FROM clientes.DISPOSITIVO "
            "WHERE dispositivo_id = :did AND cliente_id = :cid AND activo = 1"
        ),
        {"did": str(dispositivo_id), "cid": str(cliente_id)},
    )
    if not result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El dispositivo no pertenece al cliente o está inactivo.",
        )


async def _validar_garantia_activa(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> None:
    result = await db.execute(
        text(
            "SELECT fecha_vencimiento FROM clientes.GARANTIA "
            "WHERE ticket_id = :tid"
        ),
        {"tid": str(ticket_id)},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe garantía registrada para este ticket.",
        )
    if row[0] < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La garantía de este ticket ya venció.",
        )
    

# Casos de uso
# -------------------------------------------

async def crear_ticket(
        db: AsyncSession,
        cliente_id: uuid.UUID,
        payload: TicketCrear,
) -> TicketResponse:
    await _validar_dispositivo_del_cliente(db, payload.dispositivo_id, cliente_id)
    precio_base = await _obtener_precio_base(db, payload.servicio_id)

    ticket = await repo.crear_ticket(
        db=db,
        cliente_id=cliente_id,
        servicio_id=payload.servicio_id,
        dispositivo_id=payload.dispositivo_id,
        precio_base=precio_base,
        descripcion=payload.descripcion,
    )
    await db.commit()

    await publicar_evento_ticket("ticket.creado", {
        "ticket_id": str(ticket.ticket_id),
        "cliente_id": str(ticket.cliente_id),
        "servicio_id": str(ticket.servicio_id),
    })

    return _a_response(ticket)


async def obtener_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    usuario_id: uuid.UUID,
    es_tecnico: bool,
) -> TicketResponse:
    ticket = await repo.obtener_por_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")

    if not es_tecnico and ticket.cliente_id != usuario_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")

    return _a_response(ticket, ocultar_motivo=not es_tecnico)


async def listar_tickets_cliente(
    db: AsyncSession,
    cliente_id: uuid.UUID,
) -> list[TicketListItem]:
    tickets = await repo.listar_por_cliente(db, cliente_id)
    return [_a_list_item(t) for t in tickets]


async def listar_tickets_tecnico(
    db: AsyncSession,
    estado: Optional[TicketEstado] = None,
) -> list[TicketListItem]:
    tickets = await repo.listar_todos(db, estado=estado)
    return [_a_list_item(t) for t in tickets]


async def aceptar_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    tecnico_id: uuid.UUID,
    payload: TicketAceptar,
) -> TicketResponse:
    ticket = await repo.obtener_por_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    if ticket.estado != TicketEstado.EN_REVISION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede aceptar un ticket en estado '{ticket.estado}'.",
        )

    await repo.aceptar_ticket(db, ticket_id, tecnico_id, float(payload.precio_final))
    await db.commit()

    ticket = await repo.obtener_por_id(db, ticket_id)

    await publicar_evento_ticket("ticket.aceptado", {
        "ticket_id": str(ticket.ticket_id),
        "cliente_id": str(ticket.cliente_id),
        "precio_final": str(ticket.precio_final),
    })
    
    return _a_response(ticket)


async def rechazar_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    tecnico_id: uuid.UUID,
    payload: TicketRechazar,
) -> TicketResponse:
    ticket = await repo.obtener_por_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    if ticket.estado != TicketEstado.EN_REVISION:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede rechazar un ticket en estado '{ticket.estado}'.",
        )

    await repo.rechazar_ticket(db, ticket_id, tecnico_id, payload.motivo_rechazo)
    await db.commit()

    ticket = await repo.obtener_por_id(db, ticket_id)

    await publicar_evento_ticket("ticket.rechazado", {
        "ticket_id": str(ticket.ticket_id),
        "cliente_id": str(ticket.cliente_id),
    })

    return _a_response(ticket)


async def confirmar_entrega_tecnico(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    tecnico_id: uuid.UUID,
) -> TicketResponse:
    ticket = await repo.obtener_por_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    if ticket.estado != TicketEstado.EN_PROGRESO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede confirmar entrega en tickets 'En proceso'.",
        )
    if ticket.confirmado_tecnico:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El técnico ya confirmó la entrega.",
        )

    await repo.confirmar_entrega_tecnico(db, ticket_id)
    await db.commit()

    ticket = await repo.obtener_por_id(db, ticket_id)

    await publicar_evento_ticket("ticket.entrega_confirmada", {
        "ticket_id": str(ticket.ticket_id),
        "cliente_id": str(ticket.cliente_id),
    })

    return _a_response(ticket)


async def confirmar_recepcion_cliente(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> TicketResponse:
    ticket = await repo.obtener_por_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    if ticket.cliente_id != cliente_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")
    if ticket.estado != TicketEstado.EN_PROGRESO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede confirmar recepción en tickets 'En proceso'.",
        )
    if not ticket.confirmado_tecnico:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El técnico aún no ha confirmado la entrega del dispositivo.",
        )
    if ticket.confirmado_cliente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente ya confirmó la recepción.",
        )

    await repo.confirmar_recepcion_cliente(db, ticket_id)
    await db.commit()

    ticket = await repo.obtener_por_id(db, ticket_id)
    return _a_response(ticket)


async def reabrir_por_garantia(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    cliente_id: uuid.UUID,
) -> TicketResponse:
    ticket = await repo.obtener_por_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    if ticket.cliente_id != cliente_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado.")
    if ticket.estado != TicketEstado.FINALIZADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden reabrir tickets en estado 'Finalizado'.",
        )

    await _validar_garantia_activa(db, ticket_id)
    await repo.reabrir_ticket(db, ticket_id)
    await db.commit()

    ticket = await repo.obtener_por_id(db, ticket_id)

    await publicar_evento_ticket("ticket.reabierto", {
        "ticket_id": str(ticket.ticket_id),
        "cliente_id": str(ticket.cliente_id),
    })

    return _a_response(ticket)


async def archivar_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> None:
    ticket = await repo.obtener_por_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    if ticket.estado != TicketEstado.FINALIZADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden archivar tickets en estado 'Finalizado'.",
        )

    await repo.archivar_ticket(db, ticket_id)
    await db.commit()