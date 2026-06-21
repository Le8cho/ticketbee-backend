import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.servicio import Servicio

from app.database import Base


class TicketEstado(str, enum.Enum):
    EN_REVISION = "EN_REVISION"
    EN_ESPERA_PAGO = "EN_ESPERA_PAGO"
    EN_PROGRESO = "EN_PROGRESO"
    FINALIZADO = "FINALIZADO"
    ARCHIVADO = "ARCHIVADO"
    RECHAZADO = "RECHAZADO"


class TicketDispositivo(Base):
    __tablename__ = "ticket_dispositivo"
    __table_args__ = {"schema": "clientes"}

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("clientes.ticket.ticket_id"),
        primary_key=True,
    )
    dispositivo_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="dispositivos")


class Ticket(Base):
    __tablename__ = "ticket"
    __table_args__ = {"schema": "clientes"}

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("clientes.cliente.cliente_id"),
        nullable=False,
    )
    servicio_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("owner.servicio.servicio_id"),
        nullable=False,
    )
    tecnico_id: Mapped[uuid.UUID | None] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("owner.tecnico.tecnico_id"),
        nullable=True,
    )
    estado: Mapped[TicketEstado] = mapped_column(
        SAEnum(TicketEstado, native_enum=False, length=30),
        nullable=False,
        default=TicketEstado.EN_REVISION
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    precio_base: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    precio_final: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmado_tecnico: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    confirmado_cliente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    fecha_finalizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    actualizado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cliente: Mapped["Cliente"] = relationship(back_populates="tickets")
    servicio: Mapped["Servicio"] = relationship(back_populates="tickets")
    dispositivos: Mapped[list["TicketDispositivo"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


ticket_dispositivo = TicketDispositivo.__table__