import uuid
import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from app.core.database import Base

class PagoEstado(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    RECHAZADO = "RECHAZADO"

class Pago(Base):
    __tablename__ = "pago"
    __table_args__ = {"schema": "pagos"}

    pago_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("clientes.ticket.ticket_id"),
        nullable=False,
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    monto_esperado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    referencia_culqi: Mapped[str | None] = mapped_column(String(255), nullable=True) # Usado para MP tmb
    estado: Mapped[PagoEstado] = mapped_column(
        SAEnum(PagoEstado, native_enum=False, length=30),
        nullable=False,
        default=PagoEstado.PENDIENTE
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    recibido_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
