"""
Modelo Ticket — Persona 2 (Tickets) completa este archivo.
Stub mínimo definido por Persona 4 para las queries de gestión de clientes (SD-17).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Numeric, ForeignKey, TIMESTAMP, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ENUM
from app.database import Base


# Tabla de asociación Ticket ↔ Dispositivo
# Persona 2: puede mover esta definición a su propio archivo si lo prefiere
ticket_dispositivo = Table(
    "ticket_dispositivo",
    Base.metadata,
    Column("ticket_id", PG_UUID(as_uuid=True), ForeignKey("clientes.ticket.ticket_id"), primary_key=True),
    Column("dispositivo_id", PG_UUID(as_uuid=True), ForeignKey("clientes.dispositivo.dispositivo_id"), primary_key=True),
    schema="clientes",
)


class Ticket(Base):
    __tablename__ = "ticket"
    __table_args__ = {"schema": "clientes"}

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clientes.cliente.cliente_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    servicio_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("owner.servicio.servicio_id", ondelete="RESTRICT"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(
        ENUM(name="ticket_estado_enum", schema="clientes", create_type=False),
        nullable=False,
        default="CREADO",
    )
    precio_base: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    precio_final: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Persona 2: agrega descripcion, motivo_rechazo, fecha_finalizacion, etc.

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="tickets")  # noqa: F821
    servicio: Mapped["Servicio"] = relationship("Servicio", back_populates="tickets")
    dispositivos: Mapped[list["Dispositivo"]] = relationship(  # noqa: F821
        "Dispositivo", secondary=ticket_dispositivo
    )
