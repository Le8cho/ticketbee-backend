"""
Utilidades de seguridad:
  - Hash/verify de contraseñas con bcrypt
  - Crear / decodificar JWT
  - Dependencias FastAPI: get_current_cliente, get_current_tecnico
    (usadas por TODOS los demás módulos)
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from app.config import settings

# ── Bcrypt ──────────────────────────────────────────────────────
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ─────────────────────────────────────────────────────────
def create_access_token(
    subject_id: uuid.UUID,
    rol: Literal["cliente", "tecnico"],
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(subject_id),
        "rol": rol,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
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


# ── Dependencias FastAPI ────────────────────────────────────────
_bearer = HTTPBearer()


async def get_current_cliente(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> uuid.UUID:
    """Retorna cliente_id (UUID) del token. Exige rol='cliente'."""
    payload = _decode_token(credentials.credentials)
    if payload.get("rol") != "cliente":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Se requiere rol cliente")
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token sin subject valido")


async def get_current_tecnico(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> uuid.UUID:
    """Retorna tecnico_id (UUID) del token. Exige rol='tecnico'."""
    payload = _decode_token(credentials.credentials)
    if payload.get("rol") != "tecnico":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Se requiere rol tecnico")
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token sin subject valido")
