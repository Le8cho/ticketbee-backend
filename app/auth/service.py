"""
Lógica de negocio de autenticación.
"""
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.tecnico import Tecnico
from app.repositories.cliente_repository import ClienteRepository
from app.schemas.cliente import ClienteLogin, ClienteOut, ClienteRegister, TokenResponse
from app.core.security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)
TOKEN_EXPIRY_HOURS = 24


def _gen_token() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
    return token, expira


# ── Registro ────────────────────────────────────────────────────
async def register_cliente(data: ClienteRegister, db: AsyncSession) -> dict:
    repo = ClienteRepository(db)

    if await repo.get_by_email(data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Ya existe una cuenta con ese email")

    token, expira = _gen_token()
    cliente = await repo.create(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        distrito=data.distrito,
        token_verificacion=token,
        token_expira_en=expira,
    )

    # En desarrollo: imprimir el token en consola (no hay Azure aún)
    logger.info(
        "\n[EMAIL VERIFICACION] Para: %s\n"
        "  Token: %s\n"
        "  Llama: GET /api/v1/auth/verify-email?token=%s",
        cliente.email, token, token,
    )
    print(f"\n  >>> TOKEN VERIFICACION para {cliente.email}:\n"
          f"      GET /api/v1/auth/verify-email?token={token}\n")

    return {
        "mensaje": "Cuenta creada. Verifica tu email para activarla.",
        "email": cliente.email,
        "dev_token": token,          # solo en dev — quitar en prod
    }


# ── Verificar email ─────────────────────────────────────────────
async def verify_email(token: str, db: AsyncSession) -> dict:
    repo = ClienteRepository(db)
    cliente = await repo.get_by_token(token)

    if not cliente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Token invalido o ya utilizado")

    now = datetime.now(timezone.utc)
    expira = cliente.token_expira_en
    if expira is not None:
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        if now > expira:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="El enlace expiro. Solicita uno nuevo.")

    await repo.verificar_email(cliente)
    return {"mensaje": "Email verificado. Ya puedes iniciar sesion."}


# ── Reenviar verificación ───────────────────────────────────────
async def resend_verification(email: str, db: AsyncSession) -> dict:
    repo = ClienteRepository(db)
    cliente = await repo.get_by_email(email)

    if not cliente or cliente.email_verificado:
        return {"mensaje": "Si el email existe y no esta verificado, recibiras el enlace."}

    token, expira = _gen_token()
    await repo.renovar_token(cliente, token, expira)

    print(f"\n  >>> NUEVO TOKEN para {cliente.email}:\n"
          f"      GET /api/v1/auth/verify-email?token={token}\n")
    return {"mensaje": "Nuevo enlace generado.", "dev_token": token}


# ── Login cliente ───────────────────────────────────────────────
async def login_cliente(data: ClienteLogin, db: AsyncSession) -> TokenResponse:
    repo = ClienteRepository(db)
    cliente = await repo.get_by_email(data.email)

    if not cliente or not verify_password(data.password, cliente.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Email o contrasena incorrectos",
                            headers={"WWW-Authenticate": "Bearer"})

    if not cliente.email_verificado:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Debes verificar tu email antes de iniciar sesion")

    if not cliente.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Cuenta suspendida. Contacta al soporte.")

    token = create_access_token(cliente.cliente_id, "cliente")
    return TokenResponse(access_token=token, token_type="bearer", rol="cliente")


# ── Login técnico ───────────────────────────────────────────────
async def login_tecnico(email: str, password: str, db: AsyncSession) -> TokenResponse:
    result = await db.execute(
        select(Tecnico).where(Tecnico.email == email.lower())
    )
    tecnico = result.scalar_one_or_none()

    if not tecnico or not verify_password(password, tecnico.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Email o contrasena incorrectos",
                            headers={"WWW-Authenticate": "Bearer"})

    token = create_access_token(tecnico.tecnico_id, "tecnico")
    return TokenResponse(access_token=token, token_type="bearer", rol="tecnico")


# ── Perfil /me ──────────────────────────────────────────────────
async def get_me(cliente_id: uuid.UUID, db: AsyncSession) -> ClienteOut:
    cliente = await ClienteRepository(db).get_by_id(cliente_id)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Cliente no encontrado")
    return ClienteOut.model_validate(cliente)
