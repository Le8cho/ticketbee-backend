"""
Router de autenticación — /api/v1/auth/

POST   /register                 Registro de cliente
POST   /login                    Login de cliente  → JWT rol=cliente
POST   /login/tecnico            Login del técnico → JWT rol=tecnico
GET    /verify-email?token=...   Activar cuenta
POST   /resend-verification      Reenviar token de verificación
GET    /me                       Perfil del cliente autenticado
"""
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.cliente import ClienteLogin, ClienteOut, ClienteRegister, TokenResponse
from app.services import auth_service
from app.utils.security import get_current_cliente

router = APIRouter()


@router.post("/register", status_code=201)
async def register(body: ClienteRegister, db: AsyncSession = Depends(get_db)):
    return await auth_service.register_cliente(body, db)


@router.post("/login", response_model=TokenResponse)
async def login(body: ClienteLogin, db: AsyncSession = Depends(get_db)):
    return await auth_service.login_cliente(body, db)


@router.post("/login/tecnico", response_model=TokenResponse)
async def login_tecnico(body: ClienteLogin, db: AsyncSession = Depends(get_db)):
    return await auth_service.login_tecnico(body.email, body.password, db)


@router.get("/verify-email")
async def verify_email(
    token: str = Query(..., description="Token del email de registro"),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.verify_email(token, db)


@router.post("/resend-verification")
async def resend_verification(body: dict, db: AsyncSession = Depends(get_db)):
    return await auth_service.resend_verification(body.get("email", ""), db)


@router.get("/me", response_model=ClienteOut)
async def get_me(
    cliente_id: uuid.UUID = Depends(get_current_cliente),
    db: AsyncSession = Depends(get_db),
):
    return await auth_service.get_me(cliente_id, db)
