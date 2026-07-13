"""Modelo Servicio (catálogo de servicios ofrecidos)."""
import uuid
from sqlalchemy import Enum as SAEnum, String, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from app.core.database import Base


class Servicio(Base):
    __tablename__ = "servicio"
    __table_args__ = {"schema": "owner"}

    servicio_id: Mapped[uuid.UUID] = mapped_column(
        UNIQUEIDENTIFIER, primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo_servicio: Mapped[str] = mapped_column(
        SAEnum("PREVENTIVO", "CORRECTIVO", "SUSCRIPCION_SOFTWARE", native_enum=False, length=30),
        nullable=False,
    )
    precio_base: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        "Ticket", back_populates="servicio"
    )
