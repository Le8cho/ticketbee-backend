import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente


class ClienteRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Cliente | None:
        result = await self.db.execute(
            select(Cliente).where(Cliente.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, cliente_id: uuid.UUID) -> Cliente | None:
        result = await self.db.execute(
            select(Cliente).where(Cliente.cliente_id == cliente_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Cliente | None:
        result = await self.db.execute(
            select(Cliente).where(Cliente.token_verificacion == token)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        nombre: str,
        email: str,
        password_hash: str,
        distrito: str,
        token_verificacion: str,
        token_expira_en: datetime,
    ) -> Cliente:
        cliente = Cliente(
            cliente_id=uuid.uuid4(),
            nombre=nombre.strip(),
            email=email.lower(),
            password_hash=password_hash,
            distrito=distrito.strip(),
            email_verificado=False,
            token_verificacion=token_verificacion,
            token_expira_en=token_expira_en,
            activo=True,
        )
        self.db.add(cliente)
        await self.db.commit()
        await self.db.refresh(cliente)
        return cliente

    async def verificar_email(self, cliente: Cliente) -> Cliente:
        cliente.email_verificado = True
        cliente.token_verificacion = None
        cliente.token_expira_en = None
        await self.db.commit()
        await self.db.refresh(cliente)
        return cliente

    async def renovar_token(
        self, cliente: Cliente, nuevo_token: str, nueva_expiracion: datetime
    ) -> Cliente:
        cliente.token_verificacion = nuevo_token
        cliente.token_expira_en = nueva_expiracion
        await self.db.commit()
        await self.db.refresh(cliente)
        return cliente
