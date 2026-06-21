from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, UsuarioActual
from app.schemas.cliente import PerfilOut
from app.auth import service as auth_service

router = APIRouter()


@router.get("/me", response_model=PerfilOut)
async def get_me(
    usuario: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.get_me(usuario, db)