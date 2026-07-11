from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.adjunto import SubidoPor


class AdjuntoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    adjunto_id: UUID
    ticket_id: UUID
    nombre: str
    tipo_mime: str
    tamanio_bytes: int
    subido_por: SubidoPor
    subido_en: datetime
    # blob_url nunca se expone — el cliente siempre pide una SAS URL aparte
