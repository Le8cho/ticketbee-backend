import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubidoPor(str, enum.Enum):
    TECNICO = "TECNICO"
    CLIENTE = "CLIENTE"


class Adjunto(Base):
    __tablename__ = "adjunto"
    __table_args__ = {"schema": "clientes"}

    adjunto_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("clientes.ticket.ticket_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(100), nullable=False)
    tamanio_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    blob_url: Mapped[str] = mapped_column(Text, nullable=False)
    subido_por: Mapped[SubidoPor] = mapped_column(
        SAEnum(SubidoPor, native_enum=False, length=10),
        nullable=False,
    )
    subido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ticket: Mapped["Ticket"] = relationship("Ticket")  # noqa: F821
