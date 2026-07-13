from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.blob_storage import (
    generate_sas_url,
    upload_blob,
    validar_imagen,
)
from app.repositories.dispositivo_repository import DispositivoRepository
from app.schemas.dispositivo import (
    DispositivoCreate,
    DispositivoOut,
    DispositivoUpdate,
    TipoDispositivoOut,
)


class DispositivoService:
    def __init__(self, db: AsyncSession):
        self.repo = DispositivoRepository(db)

    async def listar_tipos(self) -> list[TipoDispositivoOut]:
        tipos = await self.repo.get_tipos_activos()
        return [TipoDispositivoOut.model_validate(t) for t in tipos]

    async def registrar(self, cliente_id: UUID, data: DispositivoCreate) -> DispositivoOut:
        tipo = await self.repo.get_tipo_by_id(data.tipo_dispositivo_id)
        if not tipo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de dispositivo no válido o inactivo",
            )

        if data.numero_serie:
            duplicado = await self.repo.numero_serie_exists(cliente_id, data.numero_serie)
            if duplicado:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya tienes un dispositivo registrado con ese número de serie",
                )

        dispositivo = await self.repo.create(
            cliente_id=cliente_id,
            tipo_dispositivo_id=data.tipo_dispositivo_id,
            marca=data.marca,
            modelo=data.modelo,
            numero_serie=data.numero_serie,
            foto_url=data.foto_url,
        )
        return DispositivoOut.model_validate(dispositivo)

    async def listar_todos(
        self,
        tipo_dispositivo_id: int | None = None,
        estado_ticket: str | None = None,
        servicio_id: UUID | None = None,
        cliente_id: UUID | None = None,
    ) -> list[DispositivoOut]:
        dispositivos = await self.repo.get_all(
            tipo_dispositivo_id=tipo_dispositivo_id,
            estado_ticket=estado_ticket,
            servicio_id=servicio_id,
            cliente_id=cliente_id,
        )
        return [DispositivoOut.model_validate(d) for d in dispositivos]

    async def listar(
        self,
        cliente_id: UUID,
        tipo_dispositivo_id: int | None = None,
        estado_ticket: str | None = None,
        servicio_id: UUID | None = None,
    ) -> list[DispositivoOut]:
        dispositivos = await self.repo.get_all(
            cliente_id=cliente_id,
            tipo_dispositivo_id=tipo_dispositivo_id,
            estado_ticket=estado_ticket,
            servicio_id=servicio_id,
        )
        return [DispositivoOut.model_validate(d) for d in dispositivos]

    async def actualizar(
        self, dispositivo_id: UUID, cliente_id: UUID, data: DispositivoUpdate
    ) -> DispositivoOut:
        dispositivo = await self.repo.get_by_id(dispositivo_id, cliente_id)
        if not dispositivo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado",
            )

        updates = data.model_dump(exclude_unset=True)

        if "numero_serie" in updates and updates["numero_serie"] is not None:
            if updates["numero_serie"] != dispositivo.numero_serie:
                duplicado = await self.repo.numero_serie_exists(
                    cliente_id, updates["numero_serie"], exclude_id=dispositivo_id
                )
                if duplicado:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Ya tienes un dispositivo registrado con ese número de serie",
                    )

        if not updates:
            return DispositivoOut.model_validate(dispositivo)

        dispositivo = await self.repo.update(dispositivo, **updates)
        return DispositivoOut.model_validate(dispositivo)

    async def desactivar(self, dispositivo_id: UUID, cliente_id: UUID) -> None:
        dispositivo = await self.repo.get_by_id(dispositivo_id, cliente_id)
        if not dispositivo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispositivo no encontrado",
            )
        await self.repo.soft_delete(dispositivo)

    async def subir_foto(
        self,
        dispositivo_id: UUID,
        cliente_id: UUID,
        data: bytes,
        content_type: str,
    ) -> str:
        """Valida, sube la foto al blob y actualiza foto_url en BD. Devuelve SAS URL (1h)."""
        try:
            validar_imagen(data, content_type)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

        dispositivo = await self.repo.get_by_id(dispositivo_id, cliente_id)
        if not dispositivo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado")

        blob_name = str(dispositivo_id)
        blob_url = await upload_blob(
            settings.AZURE_STORAGE_CONTAINER_DEVICES,
            blob_name,
            data,
            content_type,
        )
        await self.repo.update(dispositivo, foto_url=blob_url)
        return await generate_sas_url(settings.AZURE_STORAGE_CONTAINER_DEVICES, blob_name)

    async def obtener_url_foto(self, dispositivo_id: UUID, cliente_id: UUID) -> str:
        """Devuelve una SAS URL (1h) para la foto del dispositivo."""
        dispositivo = await self.repo.get_by_id(dispositivo_id, cliente_id)
        if not dispositivo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado")
        if not dispositivo.foto_url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El dispositivo no tiene foto registrada")

        blob_name = str(dispositivo_id)
        return await generate_sas_url(settings.AZURE_STORAGE_CONTAINER_DEVICES, blob_name)
