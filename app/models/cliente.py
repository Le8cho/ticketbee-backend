"""
Stub mínimo — Persona 4 (Clientes) debe completar este modelo.
Solo se declara la PK y la relación inversa con Dispositivo para que
SQLAlchemy pueda resolver la FK clientes.dispositivo.cliente_id.
"""
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.database import Base


class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = {"schema": "clientes"}

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Persona 4: agregar el resto de columnas (nombre, email, password_hash, distrito, etc.)

    dispositivos: Mapped[list["Dispositivo"]] = relationship(  # noqa: F821
        "Dispositivo", back_populates="cliente"
    )
