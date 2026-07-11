import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Garantia(Base):
    __tablename__ = "garantia"
    __table_args__ = {"schema": "clientes"}

    garantia_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("clientes.ticket.ticket_id"),
        nullable=False,
        unique=True,
    )
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_vencimiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="SYSDATETIMEOFFSET()",
    )
