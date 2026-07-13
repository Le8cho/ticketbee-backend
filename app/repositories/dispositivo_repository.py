from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dispositivo import Dispositivo
from app.models.tipo_dispositivo import TipoDispositivo

# noqa: E712 -- en todo el archivo se usa `== True` en vez de `.is_(True)` a propósito:
# en el dialecto mssql, `.is_(True)` compila a "IS 1", que es sintaxis inválida en T-SQL.


class DispositivoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tipos_activos(self) -> list[TipoDispositivo]:
        result = await self.db.execute(
            select(TipoDispositivo)
            .where(TipoDispositivo.activo == True)  # noqa: E712
            .order_by(TipoDispositivo.nombre)
        )
        return list(result.scalars().all())

    async def get_tipo_by_id(self, tipo_id: int) -> TipoDispositivo | None:
        result = await self.db.execute(
            select(TipoDispositivo).where(
                TipoDispositivo.tipo_dispositivo_id == tipo_id,
                TipoDispositivo.activo == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **data) -> Dispositivo:
        dispositivo = Dispositivo(**data)
        self.db.add(dispositivo)
        await self.db.commit()
        # Reload con relación para devolver tipo_dispositivo poblado
        result = await self.db.execute(
            select(Dispositivo)
            .options(selectinload(Dispositivo.tipo_dispositivo))
            .where(Dispositivo.dispositivo_id == dispositivo.dispositivo_id)
        )
        return result.scalar_one()

    async def get_all_by_cliente(self, cliente_id: UUID) -> list[Dispositivo]:
        result = await self.db.execute(
            select(Dispositivo)
            .options(selectinload(Dispositivo.tipo_dispositivo))
            .where(Dispositivo.cliente_id == cliente_id, Dispositivo.activo == True)  # noqa: E712
            .order_by(Dispositivo.creado_en.desc())
        )
        return list(result.scalars().all())

    async def get_all(
        self,
        tipo_dispositivo_id: int | None = None,
        estado_ticket: str | None = None,
        servicio_id: UUID | None = None,
        cliente_id: UUID | None = None,
    ) -> list[Dispositivo]:
        from app.models.ticket import Ticket, TicketDispositivo

        q = (
            select(Dispositivo)
            .options(selectinload(Dispositivo.tipo_dispositivo))
            .where(Dispositivo.activo == True)  # noqa: E712
        )

        if tipo_dispositivo_id is not None:
            q = q.where(Dispositivo.tipo_dispositivo_id == tipo_dispositivo_id)

        if cliente_id is not None:
            q = q.where(Dispositivo.cliente_id == cliente_id)

        if estado_ticket is not None or servicio_id is not None:
            q = q.join(
                TicketDispositivo,
                TicketDispositivo.dispositivo_id == Dispositivo.dispositivo_id,
            ).join(
                Ticket,
                Ticket.ticket_id == TicketDispositivo.ticket_id,
            )
            if estado_ticket is not None:
                q = q.where(Ticket.estado == estado_ticket)
            if servicio_id is not None:
                q = q.where(Ticket.servicio_id == servicio_id)

        q = q.order_by(Dispositivo.creado_en.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, dispositivo_id: UUID, cliente_id: UUID) -> Dispositivo | None:
        result = await self.db.execute(
            select(Dispositivo)
            .options(selectinload(Dispositivo.tipo_dispositivo))
            .where(
                Dispositivo.dispositivo_id == dispositivo_id,
                Dispositivo.cliente_id == cliente_id,
                Dispositivo.activo == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def numero_serie_exists(
        self, cliente_id: UUID, numero_serie: str, exclude_id: UUID | None = None
    ) -> bool:
        q = select(Dispositivo).where(
            Dispositivo.cliente_id == cliente_id,
            Dispositivo.numero_serie == numero_serie,
            Dispositivo.activo == True,  # noqa: E712
        )
        if exclude_id:
            q = q.where(Dispositivo.dispositivo_id != exclude_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none() is not None

    async def update(self, dispositivo: Dispositivo, **data) -> Dispositivo:
        for key, value in data.items():
            setattr(dispositivo, key, value)
        await self.db.commit()
        result = await self.db.execute(
            select(Dispositivo)
            .options(selectinload(Dispositivo.tipo_dispositivo))
            .where(Dispositivo.dispositivo_id == dispositivo.dispositivo_id)
        )
        return result.scalar_one()

    async def soft_delete(self, dispositivo: Dispositivo) -> None:
        dispositivo.activo = False
        dispositivo.inactivado_en = datetime.now(timezone.utc)
        await self.db.commit()
