import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from auth_client import auth_headers
from email_client import enviar_email_garantia_activada

logger = logging.getLogger(__name__)

DIAS_GARANTIA = 7


def calcular_vencimiento(fecha_finalizacion: datetime, dias: int = DIAS_GARANTIA) -> datetime:
    if fecha_finalizacion.tzinfo is None:
        fecha_finalizacion = fecha_finalizacion.replace(tzinfo=timezone.utc)
    return fecha_finalizacion + timedelta(days=dias)


def registrar_garantia(ticket_id: str, fecha_inicio: datetime, fecha_vencimiento: datetime) -> dict:
    """Le pide al backend que persista la garantia. fn-warranty nunca toca la BD directamente."""
    url = f"{os.environ['BACKEND_URL']}/api/v1/tickets/{ticket_id}/garantia"
    headers = auth_headers()
    payload = {
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_vencimiento": fecha_vencimiento.isoformat(),
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=10)

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"El backend rechazo el registro de garantia: {resp.status_code} {resp.text}"
        )

    logger.info(
        "Garantia registrada en backend: ticket_id=%s vencimiento=%s",
        ticket_id, fecha_vencimiento.isoformat(),
    )
    return resp.json().get("data", {})


def procesar_evento(payload: dict) -> dict:
    """Punto de entrada testeable, separado del trigger de Azure Functions."""
    evento = payload.get("evento")

    if evento != "ticket.finalizado":
        return {"processed": False, "reason": f"evento '{evento}' ignorado"}

    ticket_id = payload.get("ticket_id")
    fecha_finalizacion_str = payload.get("fecha_finalizacion")

    if not ticket_id or not fecha_finalizacion_str:
        raise ValueError("Payload incompleto: falta 'ticket_id' o 'fecha_finalizacion'")

    fecha_finalizacion = datetime.fromisoformat(fecha_finalizacion_str)
    fecha_vencimiento = calcular_vencimiento(fecha_finalizacion)
    datos_backend = registrar_garantia(ticket_id, fecha_finalizacion, fecha_vencimiento)

    enviar_email_garantia_activada(
        cliente_email=datos_backend.get("cliente_email"),
        cliente_nombre=datos_backend.get("cliente_nombre"),
        ticket_id=ticket_id,
        fecha_vencimiento=fecha_vencimiento.isoformat(),
    )

    return {"processed": True, "ticket_id": ticket_id, "fecha_vencimiento": fecha_vencimiento.isoformat()}
