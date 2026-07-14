import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import TicketEstado
from app.repositories import ticket_repository as repo
from app.repositories.cliente_repository import ClienteRepository
from app.schemas.ticket import (
    GarantiaCreate,
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
    dispositivo = ticket.dispositivos[0].dispositivo if ticket.dispositivos else None
    return TicketResponse(
        ticket_id=ticket.ticket_id,
        cliente_id=ticket.cliente_id,
        servicio_id=ticket.servicio_id,
        servicio_nombre=ticket.servicio.nombre if ticket.servicio else None,
        tecnico_id=ticket.tecnico_id,
        dispositivo_id=dispositivo.dispositivo_id if dispositivo else None,
        dispositivo_marca=dispositivo.marca if dispositivo else None,
        dispositivo_modelo=dispositivo.modelo if dispositivo else None,
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
    dispositivo = ticket.dispositivos[0].dispositivo if ticket.dispositivos else None
    return TicketListItem(
        ticket_id=ticket.ticket_id,
        estado=ticket.estado,
        servicio_id=ticket.servicio_id,
        servicio_nombre=ticket.servicio.nombre if ticket.servicio else None,
        dispositivo_id=dispositivo.dispositivo_id if dispositivo else None,
        dispositivo_marca=dispositivo.marca if dispositivo else None,
        dispositivo_modelo=dispositivo.modelo if dispositivo else None,
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

    # repo.crear_ticket solo refresca la colección "dispositivos" (no sus
    # relaciones anidadas ni el servicio) — se recarga completo para la
    # respuesta, mismo patrón que el resto de las mutaciones de este archivo.
    ticket = await repo.obtener_por_id(db, ticket.ticket_id)

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


async def listar_tickets_tecnico(
    db: AsyncSession,
    estado: Optional[TicketEstado] = None,
    cliente_id: Optional[uuid.UUID] = None,
    tipo_dispositivo_id: Optional[int] = None,
    servicio_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[datetime] = None,
    garantia_vencida: Optional[bool] = None,
) -> list[TicketListItem]:
    tickets = await repo.listar_todos(
        db,
        estado=estado,
        cliente_id=cliente_id,
        tipo_dispositivo_id=tipo_dispositivo_id,
        servicio_id=servicio_id,
        fecha_desde=fecha_desde,
        garantia_vencida=garantia_vencida,
    )
    return [_a_list_item(t) for t in tickets]


async def listar_tickets_cliente(
    db: AsyncSession,
    cliente_id: uuid.UUID,
    estado: Optional[TicketEstado] = None,
    tipo_dispositivo_id: Optional[int] = None,
    servicio_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[datetime] = None,
) -> list[TicketListItem]:
    tickets = await repo.listar_por_cliente(
        db,
        cliente_id=cliente_id,
        estado=estado,
        tipo_dispositivo_id=tipo_dispositivo_id,
        servicio_id=servicio_id,
        fecha_desde=fecha_desde,
    )
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
        "motivo_rechazo": ticket.motivo_rechazo,
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

    await publicar_evento_ticket("ticket.finalizado", {
        "ticket_id": str(ticket.ticket_id),
        "cliente_id": str(ticket.cliente_id),
        "fecha_finalizacion": ticket.fecha_finalizacion.isoformat(),
    })

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
        "tecnico_id": str(ticket.tecnico_id) if ticket.tecnico_id else None,
    })

    return _a_response(ticket)


async def archivar_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> dict:
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

    cliente = await ClienteRepository(db).get_by_id(ticket.cliente_id)
    return {
        "ticket_id": str(ticket_id),
        "cliente_email": cliente.email if cliente else None,
        "cliente_nombre": cliente.nombre if cliente else None,
    }


async def registrar_garantia(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    payload: GarantiaCreate,
) -> dict:
    ticket = await repo.obtener_por_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    if ticket.estado != TicketEstado.FINALIZADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede registrar garantía para tickets en estado 'Finalizado'.",
        )

    if not await repo.existe_garantia(db, ticket_id):
        await repo.crear_garantia(db, ticket_id, payload.fecha_inicio, payload.fecha_vencimiento)
        await db.commit()

    cliente = await ClienteRepository(db).get_by_id(ticket.cliente_id)
    return {
        "ticket_id": str(ticket_id),
        "cliente_email": cliente.email if cliente else None,
        "cliente_nombre": cliente.nombre if cliente else None,
        "fecha_vencimiento": payload.fecha_vencimiento.isoformat(),
    }
