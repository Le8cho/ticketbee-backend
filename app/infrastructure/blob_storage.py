import logging
from datetime import datetime, timezone, timedelta

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import (
    BlobSasPermissions,
    ContentSettings,
    generate_blob_sas,
)
from azure.storage.blob.aio import BlobServiceClient

from app.config import settings

logger = logging.getLogger(__name__)

MAX_SIZE_IMAGEN = 5 * 1024 * 1024     # 5 MB
MAX_SIZE_ADJUNTO = 10 * 1024 * 1024   # 10 MB

MIME_IMAGENES = frozenset({"image/jpeg", "image/png", "image/webp"})
MIME_ADJUNTOS = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
})


def validar_imagen(data: bytes, content_type: str) -> None:
    """Lanza ValueError si el archivo no cumple restricciones de foto de dispositivo."""
    if content_type not in MIME_IMAGENES:
        raise ValueError(f"Tipo no permitido: {content_type}. Solo jpeg, png o webp.")
    if len(data) > MAX_SIZE_IMAGEN:
        raise ValueError("La imagen supera el límite de 5 MB.")


def validar_adjunto(data: bytes, content_type: str) -> None:
    """Lanza ValueError si el archivo no cumple restricciones de adjunto de ticket."""
    if content_type not in MIME_ADJUNTOS:
        raise ValueError(f"Tipo no permitido: {content_type}.")
    if len(data) > MAX_SIZE_ADJUNTO:
        raise ValueError("El adjunto supera el límite de 10 MB.")


def _parse_connection_string() -> tuple[str, str]:
    """Extrae AccountName y AccountKey del connection string."""
    parts = dict(
        item.split("=", 1)
        for item in settings.AZURE_STORAGE_CONNECTION_STR.split(";")
        if "=" in item
    )
    return parts.get("AccountName", ""), parts.get("AccountKey", "")


async def upload_blob(
    container: str,
    blob_name: str,
    data: bytes,
    content_type: str,
) -> str:
    """Sube bytes al container indicado. Devuelve la URL base del blob (sin SAS)."""
    if not settings.AZURE_STORAGE_CONNECTION_STR:
        logger.info("[BlobStorage-DEV] upload container=%s blob=%s", container, blob_name)
        return f"http://localhost/dev-blobs/{container}/{blob_name}"

    async with BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_CONNECTION_STR
    ) as client:
        blob = client.get_blob_client(container=container, blob=blob_name)
        await blob.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob.url


async def generate_sas_url(
    container: str,
    blob_name: str,
    hours: int = 1,
) -> str:
    """Devuelve una URL firmada (SAS) válida por `hours` horas.
    El frontend nunca recibe la URL directa del blob."""
    if not settings.AZURE_STORAGE_CONNECTION_STR:
        return f"http://localhost/dev-blobs/{container}/{blob_name}"

    account_name, account_key = _parse_connection_string()
    expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
    )
    return f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"


async def delete_blob(container: str, blob_name: str) -> bool:
    """Elimina un blob. Devuelve True si se eliminó, False si no existía."""
    if not settings.AZURE_STORAGE_CONNECTION_STR:
        logger.info("[BlobStorage-DEV] delete container=%s blob=%s", container, blob_name)
        return True

    try:
        async with BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STR
        ) as client:
            blob = client.get_blob_client(container=container, blob=blob_name)
            await blob.delete_blob()
        return True
    except ResourceNotFoundError:
        logger.warning("[BlobStorage] blob no encontrado container=%s blob=%s", container, blob_name)
        return False
