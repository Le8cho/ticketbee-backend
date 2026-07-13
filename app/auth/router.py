from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success
from app.core.security import get_current_user, UsuarioActual
from app.auth import service as auth_service

router = APIRouter()


@router.get("/me", response_model=None, tags=["Auth-Compartido"])
async def get_me(
    usuario: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    perfil = await auth_service.get_me(usuario, db)
    return success(perfil.model_dump(mode="json"))