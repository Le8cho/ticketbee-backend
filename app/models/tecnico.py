import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TIMESTAMP
from app.database import Base


class Tecnico(Base):
    __tablename__ = "tecnico"
    __table_args__ = {"schema": "owner"}

    tecnico_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default="NOW()"
    )
