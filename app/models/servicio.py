"""
Modelo Servicio (catálogo) — responsable del catálogo completa este archivo.
Stub mínimo definido por Persona 4 para mostrar nombre del servicio en el historial.
"""
import uuid
from sqlalchemy import String, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ENUM
from app.database import Base


class Servicio(Base):
    __tablename__ = "servicio"
    __table_args__ = {"schema": "owner"}

    servicio_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo_servicio: Mapped[str] = mapped_column(
        ENUM(name="tipo_servicio_enum", schema="owner", create_type=False),
        nullable=False,
    )
    precio_base: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Responsable del catálogo: agrega descripcion, relacion servicio_tipo_dispositivo, etc.

    tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        "Ticket", back_populates="servicio"
    )
