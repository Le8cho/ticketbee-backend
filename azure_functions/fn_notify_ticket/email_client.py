import logging
import os

from azure.communication.email import EmailClient

logger = logging.getLogger(__name__)


def enviar_email(destinatario: str, nombre_destinatario: str, asunto: str, cuerpo: str) -> None:
    if not destinatario:
        logger.warning("No hay destinatario, no se envia email. asunto=%s", asunto)
        return

    client = EmailClient.from_connection_string(os.environ["ACS_CONNECTION_STR"])

    mensaje = {
        "senderAddress": os.environ["ACS_FROM_ADDRESS"],
        "recipients": {"to": [{"address": destinatario, "displayName": nombre_destinatario or ""}]},
        "content": {"subject": asunto, "plainText": cuerpo},
    }

    poller = client.begin_send(mensaje)
    resultado = poller.result()
    logger.info(
        "Email enviado: destinatario=%s asunto=%s status=%s",
        destinatario, asunto, resultado.get("status"),
    )
