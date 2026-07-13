import uuid
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings


_jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")

_bearer = HTTPBearer(auto_error=False)

_DEBUG_CLIENTE_ID = uuid.UUID("b4f8b1fe-7db6-48b6-acf3-f8f72132958c")
_DEBUG_TECNICO_ID = uuid.UUID("2ed61426-99e6-4a6f-9a8c-0b8c0edc013d")


@dataclass
class UsuarioActual:
    user_id: uuid.UUID
    rol: str


def _debug_activo() -> bool:
    return settings.DEBUG_MODE and settings.APP_ENV == "development"


def _decode_token(token: str) -> dict:
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[settings.SUPABASE_ALGORITHM],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extraer_usuario(payload: dict) -> UsuarioActual:
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin subject valido",
        )
    rol = payload.get("user_metadata", {}).get("rol", "")
    return UsuarioActual(user_id=user_id, rol=rol)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UsuarioActual:
    if _debug_activo():
        return UsuarioActual(user_id=_DEBUG_CLIENTE_ID, rol="cliente")
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")
    payload = _decode_token(credentials.credentials)
    return _extraer_usuario(payload)


async def get_current_cliente(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    actuar_como_cliente_id: uuid.UUID | None = Query(
        None,
        description="Solo rol admin: cliente_id existente en cuyo nombre actuar. "
                    "Obligatorio para admin en este endpoint, ignorado para los demás roles.",
    ),
) -> uuid.UUID:
    if _debug_activo():
        return _DEBUG_CLIENTE_ID
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")
    payload = _decode_token(credentials.credentials)
    usuario = _extraer_usuario(payload)
    if usuario.rol == "cliente":
        return usuario.user_id
    if usuario.rol == "admin":
        if actuar_como_cliente_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol admin debe indicar 'actuar_como_cliente_id' (cliente_id existente).",
            )
        return actuar_como_cliente_id
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Se requiere rol cliente",
    )


async def get_current_tecnico(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    actuar_como_tecnico_id: uuid.UUID | None = Query(
        None,
        description="Solo rol admin: tecnico_id existente en cuyo nombre actuar. "
                    "Obligatorio para admin en este endpoint, ignorado para los demás roles.",
    ),
) -> uuid.UUID:
    if _debug_activo():
        return _DEBUG_TECNICO_ID
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")
    payload = _decode_token(credentials.credentials)
    usuario = _extraer_usuario(payload)
    if usuario.rol == "tecnico":
        return usuario.user_id
    if usuario.rol == "admin":
        if actuar_como_tecnico_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol admin debe indicar 'actuar_como_tecnico_id' (tecnico_id existente).",
            )
        return actuar_como_tecnico_id
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Se requiere rol tecnico",
    )


get_current_user_dev = get_current_user
