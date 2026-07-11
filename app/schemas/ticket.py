import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.ticket import TicketEstado


# Request
# -------------------------------

class TicketCrear(BaseModel):
    dispositivo_id: uuid.UUID
    servicio_id: uuid.UUID
    descripcion: Optional[str] = Field(default=None, max_length=1000)


class TicketAceptar(BaseModel):
    precio_final: Decimal = Field(..., gt=0, decimal_places=2)


class TicketRechazar(BaseModel):
    motivo_rechazo: str = Field(..., min_length=10, max_length=500)


# Responses
# -------------------------------

class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: uuid.UUID
    cliente_id: uuid.UUID
    servicio_id: uuid.UUID
    tecnico_id: Optional[uuid.UUID]
    dispositivo_id: Optional[uuid.UUID]
    estado: TicketEstado
    descripcion: Optional[str]
    precio_base: Optional[Decimal]
    precio_final: Optional[Decimal]
    motivo_rechazo: Optional[str]
    confirmado_tecnico: bool
    confirmado_cliente: bool
    fecha_finalizacion: Optional[datetime]
    creado_en: datetime
    actualizado_en: Optional[datetime]


class TicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: uuid.UUID
    estado: TicketEstado
    servicio_id: uuid.UUID
    dispositivo_id: Optional[uuid.UUID]
    precio_base: Optional[Decimal]
    precio_final: Optional[Decimal]
    creado_en: datetime