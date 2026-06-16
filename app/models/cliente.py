import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TIMESTAMP
from app.database import Base


class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = {"schema": "clientes"}

    cliente_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    distrito: Mapped[str] = mapped_column(String(100), nullable=False)
    email_verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_verificacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    token_expira_en: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    )

    dispositivos: Mapped[list["Dispositivo"]] = relationship(  # noqa: F821
        "Dispositivo", back_populates="cliente"
    )
    # tickets: relación agregada por el módulo de tickets (Persona 3)
