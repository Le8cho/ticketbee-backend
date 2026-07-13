from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.servicio_repository import ServicioRepository
from app.schemas.servicio import ServicioCreate, ServicioOut, ServicioUpdate


class CatalogoService:
    def __init__(self, db: AsyncSession):
        self.repo = ServicioRepository(db)

    async def listar_activos(self) -> list[ServicioOut]:
        servicios = await self.repo.get_activos()
        return [ServicioOut.model_validate(s) for s in servicios]

    async def listar_todos(self) -> list[ServicioOut]:
        servicios = await self.repo.get_all()
        return [ServicioOut.model_validate(s) for s in servicios]

    async def crear(self, data: ServicioCreate) -> ServicioOut:
        servicio = await self.repo.create(**data.model_dump())
        return ServicioOut.model_validate(servicio)

    async def actualizar(self, servicio_id: UUID, data: ServicioUpdate) -> ServicioOut:
        servicio = await self.repo.get_by_id(servicio_id)
        if not servicio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servicio no encontrado",
            )
        updates = data.model_dump(exclude_unset=True)
        if updates:
            servicio = await self.repo.update(servicio, **updates)
        return ServicioOut.model_validate(servicio)
