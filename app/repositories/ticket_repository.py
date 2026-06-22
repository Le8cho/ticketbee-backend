import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket, TicketDispositivo, TicketEstado
from app.models.dispositivo import Dispositivo


async def crear_ticket(
        db:AsyncSession,
        cliente_id: uuid.UUID,
        servicio_id: uuid.UUID,
        dispositivo_id: uuid.UUID,
        precio_base: float,
        descripcion: Optional[str],
) -> Ticket:
    ticket = Ticket(
        cliente_id=cliente_id,
        servicio_id=servicio_id,
        precio_base=precio_base,
        descripcion=descripcion,
    )
    db.add(ticket)
    await db.flush()

    asociacion = TicketDispositivo(
        ticket_id=ticket.ticket_id,
        dispositivo_id=dispositivo_id,
    )
    db.add(asociacion)
    await db.flush()

    await db.refresh(ticket, ["dispositivos"])
    return ticket


async def obtener_por_id(
        db: AsyncSession,
        ticket_id: uuid.UUID,
) -> Optional[Ticket]:
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.dispositivos))
        .where(Ticket.ticket_id == ticket_id)
    )
    return result.scalar_one_or_none()


async def listar_todos(
    db: AsyncSession,
    estado: Optional[TicketEstado] = None,
    cliente_id: Optional[uuid.UUID] = None,
    tipo_dispositivo_id: Optional[int] = None,
    servicio_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[datetime] = None,
) -> list[Ticket]:
    query = (
        select(Ticket)
        .options(selectinload(Ticket.dispositivos))
        .order_by(Ticket.creado_en.desc())
    )
    if estado is not None:
        query = query.where(Ticket.estado == estado)
    if cliente_id is not None:
        query = query.where(Ticket.cliente_id == cliente_id)
    if servicio_id is not None:
        query = query.where(Ticket.servicio_id == servicio_id)
    if fecha_desde is not None:
        query = query.where(Ticket.creado_en >= fecha_desde)
    if tipo_dispositivo_id is not None:
        query = query.join(
            TicketDispositivo,
            TicketDispositivo.ticket_id == Ticket.ticket_id,
        ).join(
            Dispositivo,
            Dispositivo.dispositivo_id == TicketDispositivo.dispositivo_id,
        ).where(Dispositivo.tipo_dispositivo_id == tipo_dispositivo_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def listar_por_cliente(
    db: AsyncSession,
    cliente_id: uuid.UUID,
    estado: Optional[TicketEstado] = None,
    tipo_dispositivo_id: Optional[int] = None,
    servicio_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[datetime] = None,
) -> list[Ticket]:
    query = (
        select(Ticket)
        .options(selectinload(Ticket.dispositivos))
        .where(Ticket.cliente_id == cliente_id)
        .order_by(Ticket.creado_en.desc())
    )
    if estado is not None:
        query = query.where(Ticket.estado == estado)
    if servicio_id is not None:
        query = query.where(Ticket.servicio_id == servicio_id)
    if fecha_desde is not None:
        query = query.where(Ticket.creado_en >= fecha_desde)
    if tipo_dispositivo_id is not None:
        query = query.join(
            TicketDispositivo,
            TicketDispositivo.ticket_id == Ticket.ticket_id,
        ).join(
            Dispositivo,
            Dispositivo.dispositivo_id == TicketDispositivo.dispositivo_id,
        ).where(Dispositivo.tipo_dispositivo_id == tipo_dispositivo_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def actualizar_estado(
        db: AsyncSession,
        ticket_id: uuid.UUID,
        nuevo_estado: TicketEstado,
) -> None:
    await db.execute(
        update(Ticket)
        .where(Ticket.ticket_id == ticket_id)
        .values(
            estado=nuevo_estado,
            actualizado_en=datetime.now(timezone.utc),
        )
    )


async def aceptar_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    tecnico_id: uuid.UUID,
    precio_final: float,
) -> None:
    await db.execute(
        update(Ticket)
        .where(Ticket.ticket_id == ticket_id)
        .values(
            tecnico_id=tecnico_id,
            precio_final=precio_final,
            estado=TicketEstado.EN_ESPERA_PAGO,
            actualizado_en=datetime.now(timezone.utc),
        )
    )


async def rechazar_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    tecnico_id: uuid.UUID,
    motivo_rechazo: str,
) -> None:
    await db.execute(
        update(Ticket)
        .where(Ticket.ticket_id == ticket_id)
        .values(
            tecnico_id=tecnico_id,
            motivo_rechazo=motivo_rechazo,
            estado=TicketEstado.RECHAZADO,
            actualizado_en=datetime.now(timezone.utc),
        )
    )


async def confirmar_entrega_tecnico(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> None:
    await db.execute(
        update(Ticket)
        .where(Ticket.ticket_id == ticket_id)
        .values(
            confirmado_tecnico=True,
            actualizado_en=datetime.now(timezone.utc),
        )
    )


async def confirmar_recepcion_cliente(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> None:
    await db.execute(
        update(Ticket)
        .where(Ticket.ticket_id == ticket_id)
        .values(
            confirmado_cliente=True,
            estado=TicketEstado.FINALIZADO,
            fecha_finalizacion=datetime.now(timezone.utc),
            actualizado_en=datetime.now(timezone.utc),
        )
    )


async def archivar_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> None:
    await db.execute(
        update(Ticket)
        .where(Ticket.ticket_id == ticket_id)
        .values(
            estado=TicketEstado.ARCHIVADO,
            actualizado_en=datetime.now(timezone.utc),
        )
    )


async def reabrir_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
) -> None:
    await db.execute(
        update(Ticket)
        .where(Ticket.ticket_id == ticket_id)
        .values(
            estado=TicketEstado.EN_PROGRESO,
            confirmado_tecnico=False,
            confirmado_cliente=False,
            fecha_finalizacion=None,
            actualizado_en=datetime.now(timezone.utc),
        )
    )