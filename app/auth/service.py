from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import UsuarioActual
from app.models.cliente import Cliente
from app.models.tecnico import Tecnico
from app.schemas.cliente import PerfilOut


async def get_me(usuario: UsuarioActual, db: AsyncSession) -> PerfilOut:
    if usuario.rol == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rol admin no tiene perfil propio (sin datos asociados).",
        )
    if usuario.rol == "tecnico":
        result = await db.execute(
            select(Tecnico).where(Tecnico.tecnico_id == usuario.user_id)
        )
        tecnico = result.scalar_one_or_none()
        if not tecnico:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tecnico no encontrado")
        return PerfilOut(id=tecnico.tecnico_id, nombre=tecnico.nombre, email=tecnico.email, rol="tecnico", creado_en=tecnico.creado_en)

    result = await db.execute(
        select(Cliente).where(Cliente.cliente_id == usuario.user_id)
    )
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return PerfilOut(id=cliente.cliente_id, nombre=cliente.nombre, email=cliente.email, rol="cliente", creado_en=cliente.creado_en)