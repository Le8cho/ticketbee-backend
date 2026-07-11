import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ticket import TicketEstado
from app.schemas.ticket import (
    GarantiaCreate,
    TicketAceptar,
    TicketCrear,
    TicketListItem,
    TicketRechazar,
    TicketResponse,
)
from app.services import ticket_service as service
from app.services.attachment_service import AttachmentService

MAX_ADJUNTO_BYTES = 10 * 1024 * 1024  # 10 MB — igual que blob_storage.MAX_SIZE_ADJUNTO

from app.core.responses import error, success
from app.core.security import (
    UsuarioActual,
    get_current_user,
    get_current_cliente as require_cliente,
    get_current_tecnico as require_tecnico,
)

router = APIRouter()


# Cliente
# --------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_ticket(
    payload: TicketCrear,
    cliente_id: uuid.UUID = Depends(require_cliente),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.crear_ticket(db, cliente_id, payload)
    return success(ticket.model_dump(mode="json"), "Ticket creado.", status.HTTP_201_CREATED)


@router.patch("/{ticket_id}/confirmar-recepcion")
async def confirmar_recepcion(
    ticket_id: uuid.UUID,
    cliente_id: uuid.UUID = Depends(require_cliente),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.confirmar_recepcion_cliente(db, ticket_id, cliente_id)
    return success(ticket.model_dump(mode="json"), "Recepción confirmada. Ticket finalizado.")


@router.patch("/{ticket_id}/reabrir")
async def reabrir_ticket(
    ticket_id: uuid.UUID,
    cliente_id: uuid.UUID = Depends(require_cliente),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.reabrir_por_garantia(db, ticket_id, cliente_id)
    return success(ticket.model_dump(mode="json"), "Ticket reabierto por incidencia de garantía.")


# Técnico
# --------------------------------------

@router.patch("/{ticket_id}/aceptar")
async def aceptar_ticket(
    ticket_id: uuid.UUID,
    payload: TicketAceptar,
    tecnico_id: uuid.UUID = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.aceptar_ticket(db, ticket_id, tecnico_id, payload)
    return success(ticket.model_dump(mode="json"), "Ticket aceptado.")


@router.patch("/{ticket_id}/rechazar")
async def rechazar_ticket(
    ticket_id: uuid.UUID,
    payload: TicketRechazar,
    tecnico_id: uuid.UUID = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.rechazar_ticket(db, ticket_id, tecnico_id, payload)
    return success(ticket.model_dump(mode="json"), "Ticket rechazado.")


@router.patch("/{ticket_id}/confirmar-entrega")
async def confirmar_entrega(
    ticket_id: uuid.UUID,
    tecnico_id: uuid.UUID = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    ticket = await service.confirmar_entrega_tecnico(db, ticket_id, tecnico_id)
    return success(ticket.model_dump(mode="json"), "Entrega confirmada.")


@router.patch("/{ticket_id}/archivar")
async def archivar_ticket(
    ticket_id: uuid.UUID,
    tecnico_id: uuid.UUID = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    datos = await service.archivar_ticket(db, ticket_id)
    return success(datos, "Ticket archivado.")


@router.post("/{ticket_id}/garantia", status_code=status.HTTP_201_CREATED)
async def registrar_garantia(
    ticket_id: uuid.UUID,
    payload: GarantiaCreate,
    tecnico_id: uuid.UUID = Depends(require_tecnico),
    db: AsyncSession = Depends(get_db),
):
    datos = await service.registrar_garantia(db, ticket_id, payload)
    return success(datos, "Garantía registrada.", status.HTTP_201_CREATED)


# Compartidos
# --------------------------------------

@router.get("/{ticket_id}", response_model=None)
async def obtener_ticket(
    ticket_id: uuid.UUID,
    usuario: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    es_tecnico = usuario.rol == "tecnico"
    ticket = await service.obtener_ticket(db, ticket_id, usuario.user_id, es_tecnico)
    return success(ticket.model_dump(mode="json"), "OK")


@router.get("", response_model=None)
async def listar_tickets(
    estado: Optional[TicketEstado] = None,
    cliente_id: Optional[uuid.UUID] = None,
    tipo_dispositivo_id: Optional[int] = None,
    servicio_id: Optional[uuid.UUID] = None,
    fecha_desde: Optional[datetime] = None,
    garantia_vencida: Optional[bool] = None,
    usuario: UsuarioActual = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if usuario.rol == "tecnico":
        tickets = await service.listar_tickets_tecnico(
            db,
            estado=estado,
            cliente_id=cliente_id,
            tipo_dispositivo_id=tipo_dispositivo_id,
            servicio_id=servicio_id,
            fecha_desde=fecha_desde,
            garantia_vencida=garantia_vencida,
        )
    else:
        tickets = await service.listar_tickets_cliente(db, usuario.user_id)
    return success([t.model_dump(mode="json") for t in tickets], "OK")


# Adjuntos
# --------------------------------------

def _attachment_service(db: AsyncSession = Depends(get_db)) -> AttachmentService:
    return AttachmentService(db)


@router.post("/{ticket_id}/adjuntos", status_code=status.HTTP_201_CREATED)
async def subir_adjunto(
    ticket_id: uuid.UUID,
    archivo: UploadFile = File(...),
    usuario: UsuarioActual = Depends(get_current_user),
    service: AttachmentService = Depends(_attachment_service),
):
    """Sube un adjunto al ticket (solo en estado EN_PROGRESO). Devuelve metadatos + SAS URL (1h)."""
    data = await archivo.read()
    if len(data) > MAX_ADJUNTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El adjunto supera el límite de 10 MB.",
        )
    adjunto, sas_url = await service.subir_adjunto(
        ticket_id=ticket_id,
        rol=usuario.rol,
        nombre_archivo=archivo.filename or "adjunto",
        data=data,
        content_type=archivo.content_type or "",
    )
    return success(
        {"adjunto": adjunto.model_dump(mode="json"), "url": sas_url},
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/{ticket_id}/adjuntos")
async def listar_adjuntos(
    ticket_id: uuid.UUID,
    usuario: UsuarioActual = Depends(get_current_user),
    service: AttachmentService = Depends(_attachment_service),
):
    """Lista todos los adjuntos de un ticket (metadatos, sin URLs)."""
    adjuntos = await service.listar_adjuntos(ticket_id)
    return success([a.model_dump(mode="json") for a in adjuntos])
