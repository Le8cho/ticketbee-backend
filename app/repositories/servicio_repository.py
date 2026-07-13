from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.servicio import Servicio

# noqa: E712 -- se usa `== True` a propósito: en el dialecto mssql, `.is_(True)`
# compila a "IS 1", que es sintaxis inválida en T-SQL (mismo criterio que el
# resto de repositories del proyecto).


class ServicioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_activos(self) -> list[Servicio]:
        result = await self.db.execute(
            select(Servicio).where(Servicio.activo == True).order_by(Servicio.nombre)  # noqa: E712
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[Servicio]:
        result = await self.db.execute(select(Servicio).order_by(Servicio.nombre))
        return list(result.scalars().all())

    async def get_by_id(self, servicio_id: UUID) -> Servicio | None:
        result = await self.db.execute(
            select(Servicio).where(Servicio.servicio_id == servicio_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **data) -> Servicio:
        servicio = Servicio(**data)
        self.db.add(servicio)
        await self.db.commit()
        await self.db.refresh(servicio)
        return servicio

    async def update(self, servicio: Servicio, **data) -> Servicio:
        for key, value in data.items():
            setattr(servicio, key, value)
        await self.db.commit()
        await self.db.refresh(servicio)
        return servicio
