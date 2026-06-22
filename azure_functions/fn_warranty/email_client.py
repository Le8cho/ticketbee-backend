import logging
import os

from azure.communication.email import EmailClient

logger = logging.getLogger(__name__)


def enviar_email_garantia_activada(
    cliente_email: str,
    cliente_nombre: str,
    ticket_id: str,
    fecha_vencimiento: str,
) -> None:
    if not cliente_email:
        logger.warning("No hay email de cliente, no se envia notificacion. ticket_id=%s", ticket_id)
        return

    client = EmailClient.from_connection_string(os.environ["ACS_CONNECTION_STR"])

    mensaje = {
        "senderAddress": os.environ["ACS_FROM_ADDRESS"],
        "recipients": {"to": [{"address": cliente_email, "displayName": cliente_nombre or ""}]},
        "content": {
            "subject": f"TechFix — Tu servicio ha sido finalizado #{ticket_id}",
            "plainText": (
                f"Hola {cliente_nombre or ''}, el técnico confirmó la entrega de tu dispositivo. "
                "Tu servicio está completo y cuenta con garantía activa.\n"
                f"Vencimiento de la garantía: {fecha_vencimiento}\n\n"
                "— Equipo TechFix"
            ),
        },
    }

    poller = client.begin_send(mensaje)
    resultado = poller.result()
    logger.info("Email de garantia enviado: ticket_id=%s status=%s", ticket_id, resultado.get("status"))
