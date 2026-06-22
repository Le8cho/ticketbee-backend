import uuid
from datetime import datetime

from sqlalchemy import select, func, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cliente import Cliente
from app.models.dispositivo import Dispositivo
from app.models.ticket import Ticket, ticket_dispositivo
from app.models.servicio import Servicio



class ClienteRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Cliente | None:
        result = await self.db.execute(
            select(Cliente).where(Cliente.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, cliente_id: uuid.UUID) -> Cliente | None:
        result = await self.db.execute(
            select(Cliente).where(Cliente.cliente_id == cliente_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Cliente | None:
        result = await self.db.execute(
            select(Cliente).where(Cliente.token_verificacion == token)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        nombre: str,
        email: str,
        password_hash: str,
        distrito: str,
        token_verificacion: str,
        token_expira_en: datetime,
    ) -> Cliente:
        cliente = Cliente(
            cliente_id=uuid.uuid4(),
            nombre=nombre.strip(),
            email=email.lower(),
            password_hash=password_hash,
            distrito=distrito.strip(),
            email_verificado=False,
            token_verificacion=token_verificacion,
            token_expira_en=token_expira_en,
            activo=True,
        )
        self.db.add(cliente)
        await self.db.commit()
        await self.db.refresh(cliente)
        return cliente

    async def verificar_email(self, cliente: Cliente) -> Cliente:
        cliente.email_verificado = True
        cliente.token_verificacion = None
        cliente.token_expira_en = None
        await self.db.commit()
        await self.db.refresh(cliente)
        return cliente

    async def renovar_token(
        self, cliente: Cliente, nuevo_token: str, nueva_expiracion: datetime
    ) -> Cliente:
        cliente.token_verificacion = nuevo_token
        cliente.token_expira_en = nueva_expiracion
        await self.db.commit()
        await self.db.refresh(cliente)
        return cliente

    # ── Gestión de clientes — SD-17 ─────────────────────────────────────────

    _ESTADOS_ACTIVOS = ("CREADO", "EN_ESPERA_PAGO", "EN_PROGRESO")

    async def list_clientes(
        self,
        estado_ticket: str | None = None,
        distrito: str | None = None,
        fecha_desde: datetime | None = None,
        tipo_ultimo_ticket: str | None = None,
    ) -> list[tuple]:
        """Devuelve (Cliente, tickets_activos, ultimo_ticket_estado) con filtros opcionales."""
        tickets_activos_sq = (
            select(func.count(Ticket.ticket_id))
            .where(
                Ticket.cliente_id == Cliente.cliente_id,
                Ticket.estado.in_(self._ESTADOS_ACTIVOS),
            )
            .correlate(Cliente)
            .scalar_subquery()
        )

        ultimo_estado_sq = (
            select(Ticket.estado)
            .where(Ticket.cliente_id == Cliente.cliente_id)
            .order_by(Ticket.creado_en.desc())
            .limit(1)
            .correlate(Cliente)
            .scalar_subquery()
        )

        stmt = (
            select(
                Cliente,
                tickets_activos_sq.label("tickets_activos"),
                ultimo_estado_sq.label("ultimo_ticket_estado"),
            )
            .where(Cliente.activo == True)  # noqa: E712
            .order_by(Cliente.creado_en.desc())
        )

        if distrito:
            stmt = stmt.where(Cliente.distrito == distrito)

        if fecha_desde:
            stmt = stmt.where(Cliente.creado_en >= fecha_desde)

        if estado_ticket:
            stmt = stmt.where(
                exists(
                    select(Ticket.ticket_id).where(
                        Ticket.cliente_id == Cliente.cliente_id,
                        Ticket.estado == estado_ticket,
                    )
                )
            )

        if tipo_ultimo_ticket:
            ultimo_servicio_sq = (
                select(Ticket.servicio_id)
                .where(Ticket.cliente_id == Cliente.cliente_id)
                .order_by(Ticket.creado_en.desc())
                .limit(1)
                .correlate(Cliente)
                .scalar_subquery()
            )
            stmt = stmt.where(
                exists(
                    select(Servicio.servicio_id).where(
                        Servicio.servicio_id == ultimo_servicio_sq,
                        Servicio.tipo_servicio == tipo_ultimo_ticket,
                    )
                )
            )

        result = await self.db.execute(stmt)
        return result.all()

    async def get_cliente_profile(self, cliente_id: uuid.UUID) -> Cliente | None:
        """Devuelve el cliente con dispositivos y tipo_dispositivo cargados via selectinload."""
        stmt = (
            select(Cliente)
            .where(Cliente.cliente_id == cliente_id)
            .options(
                selectinload(Cliente.dispositivos).selectinload(Dispositivo.tipo_dispositivo)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tickets_por_dispositivos(
        self, dispositivo_ids: list[uuid.UUID]
    ) -> list[tuple]:
        """Devuelve (Ticket, dispositivo_id, servicio_nombre) para los dispositivos dados."""
        if not dispositivo_ids:
            return []

        stmt = (
            select(
                Ticket,
                ticket_dispositivo.c.dispositivo_id,
                Servicio.nombre.label("servicio_nombre"),
            )
            .join(ticket_dispositivo, ticket_dispositivo.c.ticket_id == Ticket.ticket_id)
            .outerjoin(Servicio, Servicio.servicio_id == Ticket.servicio_id)
            .where(ticket_dispositivo.c.dispositivo_id.in_(dispositivo_ids))
            .order_by(Ticket.creado_en.desc())
        )
        result = await self.db.execute(stmt)
        return result.all()
