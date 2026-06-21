import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator, field_serializer


# ── Auth schemas (usados por Persona 1 — auth_service) ────────────────────────

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
    activo: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


# ── Gestión de clientes — SD-17 (Persona 4) ───────────────────────────────────

class ClienteListItem(BaseModel):
    """Ítem del listado de clientes para el panel del técnico."""
    cliente_id: uuid.UUID
    nombre: str
    email: str
    distrito: str
    tickets_activos: int
    ultimo_ticket_estado: str | None
    creado_en: datetime

    model_config = {"from_attributes": True}

    @field_serializer("cliente_id")
    def serialize_uuid(self, v: uuid.UUID) -> str:
        return str(v)


class TicketResumen(BaseModel):
    ticket_id: uuid.UUID
    estado: str
    servicio_nombre: str | None
    precio_base: float | None
    precio_final: float | None
    creado_en: datetime

    model_config = {"from_attributes": True}

    @field_serializer("ticket_id")
    def serialize_uuid(self, v: uuid.UUID) -> str:
        return str(v)


class DispositivoConTickets(BaseModel):
    dispositivo_id: uuid.UUID
    tipo_nombre: str | None
    marca: str
    modelo: str
    numero_serie: str | None
    activo: bool
    tickets: list[TicketResumen]

    model_config = {"from_attributes": True}

    @field_serializer("dispositivo_id")
    def serialize_uuid(self, v: uuid.UUID) -> str:
        return str(v)


class ClienteProfile(BaseModel):
    """Perfil completo del cliente con dispositivos e historial de tickets."""
    cliente_id: uuid.UUID
    nombre: str
    email: str
    distrito: str
    activo: bool
    creado_en: datetime
    dispositivos: list[DispositivoConTickets]

    model_config = {"from_attributes": True}

    @field_serializer("cliente_id")
    def serialize_uuid(self, v: uuid.UUID) -> str:
        return str(v)
    
    
class PerfilOut(BaseModel):
    id: uuid.UUID
    nombre: str
    email: str
    rol: str
    creado_en: datetime

    model_config = {"from_attributes": True}