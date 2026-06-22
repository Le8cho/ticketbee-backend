import logging
import os

import requests

from auth_client import auth_headers
from email_client import enviar_email

logger = logging.getLogger(__name__)


def obtener_cliente(cliente_id: str) -> dict:
    """fn-notify-ticket nunca toca la BD directamente, consulta al backend."""
    url = f"{os.environ['BACKEND_URL']}/api/v1/clientes/{cliente_id}"
    resp = requests.get(url, headers=auth_headers(), timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(f"El backend rechazo la consulta del cliente: {resp.status_code} {resp.text}")

    return resp.json().get("data", {})


def obtener_tecnico(tecnico_id: str) -> dict:
    url = f"{os.environ['BACKEND_URL']}/api/v1/tecnicos/{tecnico_id}"
    resp = requests.get(url, headers=auth_headers(), timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(f"El backend rechazo la consulta del tecnico: {resp.status_code} {resp.text}")

    return resp.json().get("data", {})


def _notificar_creado(payload: dict) -> None:
    cliente = obtener_cliente(payload["cliente_id"])
    ticket_id = payload["ticket_id"]
    enviar_email(
        destinatario=cliente.get("email"),
        nombre_destinatario=cliente.get("nombre"),
        asunto=f"TechFix — Tu ticket #{ticket_id} fue recibido",
        cuerpo=(
            f"Hola {cliente.get('nombre', '')}, tu solicitud de servicio fue enviada exitosamente. "
            "Nuestro técnico la revisará pronto y te enviaremos la cotización a este correo.\n\n"
            "— Equipo TechFix"
        ),
    )


def _notificar_aceptado(payload: dict) -> None:
    cliente = obtener_cliente(payload["cliente_id"])
    ticket_id = payload["ticket_id"]
    enviar_email(
        destinatario=cliente.get("email"),
        nombre_destinatario=cliente.get("nombre"),
        asunto=f"TechFix — Cotización para tu ticket #{ticket_id}",
        cuerpo=(
            f"Hola {cliente.get('nombre', '')}, tu ticket fue revisado y aquí está la cotización:\n"
            f"Monto a pagar: S/ {payload.get('precio_final')}\n"
            "Por favor realiza el pago por Yape para continuar con el servicio.\n\n"
            "— Equipo TechFix"
        ),
    )


def _notificar_rechazado(payload: dict) -> None:
    cliente = obtener_cliente(payload["cliente_id"])
    ticket_id = payload["ticket_id"]
    enviar_email(
        destinatario=cliente.get("email"),
        nombre_destinatario=cliente.get("nombre"),
        asunto=f"TechFix — Actualización sobre tu ticket #{ticket_id}",
        cuerpo=(
            f"Hola {cliente.get('nombre', '')}, lamentablemente no podemos atender tu solicitud "
            "por el siguiente motivo:\n"
            f"{payload.get('motivo_rechazo', '')}\n"
            "Si tienes consultas puedes escribirnos. Gracias por tu confianza en TechFix."
        ),
    )


def _notificar_entrega_confirmada(payload: dict) -> None:
    cliente = obtener_cliente(payload["cliente_id"])
    enviar_email(
        destinatario=cliente.get("email"),
        nombre_destinatario=cliente.get("nombre"),
        asunto="Tu dispositivo está listo",
        cuerpo=(
            f"Hola {cliente.get('nombre', '')},\n\n"
            f"Tu dispositivo del ticket {payload['ticket_id']} está listo. "
            "Por favor confirma la recepción desde tu panel.\n\n"
            "Equipo TechFix"
        ),
    )


def _notificar_reabierto(payload: dict) -> None:
    """Busca al tecnico especifico asignado al ticket (no un correo fijo de soporte)."""
    ticket_id = payload["ticket_id"]
    tecnico_id = payload.get("tecnico_id")

    if not tecnico_id:
        logger.warning("ticket.reabierto sin tecnico_id, no se puede notificar. ticket_id=%s", ticket_id)
        return

    tecnico = obtener_tecnico(tecnico_id)
    enviar_email(
        destinatario=tecnico.get("email"),
        nombre_destinatario=tecnico.get("nombre"),
        asunto=f"TechFix — Reingreso por garantía #{ticket_id}",
        cuerpo=(
            f"Hola {tecnico.get('nombre', '')}, el cliente reportó un incidente dentro del período "
            f"de garantía. El ticket #{ticket_id} vuelve a estar En progreso para tu revisión."
        ),
    )


# ticket.finalizado queda sin handler a proposito: fn-warranty ya notifica
# en ese momento (garantia activada), para no duplicar el correo al cliente.
_HANDLERS = {
    "ticket.creado": _notificar_creado,
    "ticket.aceptado": _notificar_aceptado,
    "ticket.rechazado": _notificar_rechazado,
    "ticket.entrega_confirmada": _notificar_entrega_confirmada,
    "ticket.reabierto": _notificar_reabierto,
}


def procesar_evento(payload: dict) -> dict:
    """Punto de entrada testeable, separado del trigger de Azure Functions."""
    evento = payload.get("evento")
    handler = _HANDLERS.get(evento)

    if handler is None:
        return {"processed": False, "reason": f"evento '{evento}' sin handler"}

    handler(payload)
    return {"processed": True, "evento": evento}
