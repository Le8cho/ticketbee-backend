import logging
import os

import requests

from auth_client import auth_headers
from email_client import enviar_email_garantia_concluida

logger = logging.getLogger(__name__)


def obtener_tickets_vencidos() -> list[dict]:
    """Le pregunta al backend que tickets tienen la garantia vencida y siguen FINALIZADO.
    fn-file-ticket nunca consulta la base de datos directamente."""
    url = f"{os.environ['BACKEND_URL']}/api/v1/tickets"
    resp = requests.get(url, params={"garantia_vencida": "true"}, headers=auth_headers(), timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(f"El backend rechazo la consulta de tickets vencidos: {resp.status_code} {resp.text}")

    return resp.json().get("data", [])


def archivar_ticket(ticket_id: str) -> None:
    """Le pide al backend que archive el ticket. fn-file-ticket nunca actualiza la BD directamente."""
    url = f"{os.environ['BACKEND_URL']}/api/v1/tickets/{ticket_id}/archivar"
    resp = requests.patch(url, headers=auth_headers(), timeout=10)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"El backend rechazo el archivado de {ticket_id}: {resp.status_code} {resp.text}")

    logger.info("Ticket archivado: ticket_id=%s", ticket_id)

    datos = resp.json().get("data", {})
    enviar_email_garantia_concluida(
        cliente_email=datos.get("cliente_email"),
        cliente_nombre=datos.get("cliente_nombre"),
        ticket_id=ticket_id,
    )


def archivar_tickets_vencidos() -> dict:
    """Punto de entrada testeable, separado del trigger de Azure Functions."""
    tickets = obtener_tickets_vencidos()

    archivados = []
    fallidos = []
    for ticket in tickets:
        ticket_id = ticket["ticket_id"]
        try:
            archivar_ticket(ticket_id)
            archivados.append(ticket_id)
        except RuntimeError as exc:
            logger.error("No se pudo archivar %s: %s", ticket_id, exc)
            fallidos.append(ticket_id)

    return {"revisados": len(tickets), "archivados": archivados, "fallidos": fallidos}
