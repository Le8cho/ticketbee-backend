import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Para desarrollo con usuarios ficticios
from fastapi import Request

from app.config import settings

bearer_scheme = HTTPBearer()


@dataclass
class UsuarioActual:
    user_id: uuid.UUID
    rol: str        # cliente | tecnico


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UsuarioActual:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return UsuarioActual(
            user_id=uuid.UUID(payload["sub"]),
            rol=payload["rol"],
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    

# BORRAR DESPUÉS DE PRUEBAS
async def get_current_user_dev(request: Request) -> UsuarioActual:
    rol = request.headers.get("X-Dev-Rol", "cliente")
    uid = request.headers.get("X-Dev-UserId", "00000000-0000-0000-0000-000000000001")
    return UsuarioActual(user_id=uuid.UUID(uid), rol=rol)


async def require_tecnico(
    usuario: UsuarioActual = Depends(get_current_user),
) -> UsuarioActual:
    if usuario.rol != "tecnico":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol técnico.",
        )
    return usuario


async def require_cliente(
    usuario: UsuarioActual = Depends(get_current_user),
) -> UsuarioActual:
    if usuario.rol != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol cliente.",
        )
    return usuario