import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from app.core.database import Base


class Dispositivo(Base):
    __tablename__ = "dispositivo"
    __table_args__ = (
        UniqueConstraint("cliente_id", "numero_serie", name="uq_dispositivo_cliente_serie"),
        {"schema": "clientes"},
    )

    dispositivo_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("clientes.cliente.cliente_id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo_dispositivo_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("owner.tipo_dispositivo.tipo_dispositivo_id", ondelete="RESTRICT"),
        nullable=False,
    )
    marca: Mapped[str] = mapped_column(String(80), nullable=False)
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    numero_serie: Mapped[str | None] = mapped_column(String(100), nullable=True)
    foto_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    inactivado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="dispositivos")  # noqa: F821
    tipo_dispositivo: Mapped["TipoDispositivo"] = relationship("TipoDispositivo")  # noqa: F821
