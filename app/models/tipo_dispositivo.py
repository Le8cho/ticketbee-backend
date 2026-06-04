from sqlalchemy import SmallInteger, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TipoDispositivo(Base):
    __tablename__ = "tipo_dispositivo"
    __table_args__ = {"schema": "owner"}

    tipo_dispositivo_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
