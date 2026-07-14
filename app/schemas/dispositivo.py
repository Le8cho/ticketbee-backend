from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class TipoDispositivoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tipo_dispositivo_id: int
    nombre: str


class ClienteBasico(BaseModel):
    """Datos mínimos del cliente dueño, para mostrar en listados de técnico."""
    model_config = ConfigDict(from_attributes=True)

    cliente_id: UUID
    nombre: str
    email: str


class DispositivoCreate(BaseModel):
    tipo_dispositivo_id: int
    marca: str = Field(..., min_length=1, max_length=80)
    modelo: str = Field(..., min_length=1, max_length=120)
    numero_serie: str | None = Field(None, max_length=100)
    foto_url: str | None = None


class DispositivoUpdate(BaseModel):
    marca: str | None = Field(None, min_length=1, max_length=80)
    modelo: str | None = Field(None, min_length=1, max_length=120)
    numero_serie: str | None = Field(None, max_length=100)
    foto_url: str | None = None


class DispositivoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dispositivo_id: UUID
    cliente_id: UUID
    cliente: ClienteBasico
    tipo_dispositivo_id: int
    tipo_dispositivo: TipoDispositivoOut
    marca: str
    modelo: str
    numero_serie: str | None
    foto_url: str | None
    activo: bool
    creado_en: datetime
    inactivado_en: datetime | None
