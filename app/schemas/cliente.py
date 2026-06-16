import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class ClienteRegister(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    distrito: str

    @field_validator("nombre")
    @classmethod
    def nombre_valido(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def password_segura(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("La contrasena debe tener al menos 6 caracteres")
        return v

    @field_validator("distrito")
    @classmethod
    def distrito_valido(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El distrito es requerido")
        return v


class ClienteLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str


class ClienteOut(BaseModel):
    cliente_id: uuid.UUID
    nombre: str
    email: str
    distrito: str
    email_verificado: bool
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}
