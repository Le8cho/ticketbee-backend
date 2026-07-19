from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

TipoServicio = Literal["PREVENTIVO", "CORRECTIVO", "SUSCRIPCION_SOFTWARE", "OTROS"]


class ServicioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    servicio_id: UUID
    nombre: str
    tipo_servicio: TipoServicio
    precio_base: Decimal
    activo: bool


class ServicioCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    tipo_servicio: TipoServicio
    precio_base: Decimal = Field(..., gt=0, decimal_places=2)


class ServicioUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=120)
    tipo_servicio: TipoServicio | None = None
    precio_base: Decimal | None = Field(None, gt=0, decimal_places=2)
    activo: bool | None = None
