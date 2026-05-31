"""
Persona 1 (Auth + base) debe implementar las funciones de este módulo.

Contrato requerido por el resto de módulos:

    get_current_cliente(credentials) -> UUID
        Lee el Bearer token del header Authorization, decodifica el JWT
        con PyJWT usando settings.SECRET_KEY / settings.ALGORITHM,
        extrae el campo 'sub' del payload (cliente_id como string UUID)
        y retorna el UUID del cliente autenticado.
        Lanza HTTP 401 si el token es inválido, expirado o malformado.

    get_current_tecnico(credentials) -> UUID
        Igual que get_current_cliente pero valida que el rol en el payload
        sea 'tecnico'. Retorna el tecnico_id como UUID.
        Lanza HTTP 403 si el token pertenece a un cliente.
"""
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_bearer = HTTPBearer()


async def get_current_cliente(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UUID:
    # TODO Persona 1: implementar decode JWT real
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Auth pendiente de implementación (Persona 1)",
    )


async def get_current_tecnico(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UUID:
    # TODO Persona 1: implementar decode JWT + validación de rol tecnico
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Auth pendiente de implementación (Persona 1)",
    )
