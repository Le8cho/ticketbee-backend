import uuid

from pydantic import BaseModel, ConfigDict


class TecnicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tecnico_id: uuid.UUID
    nombre: str
    email: str
