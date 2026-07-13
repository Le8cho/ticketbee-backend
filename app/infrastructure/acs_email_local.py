import logging
import os
from azure.communication.email import EmailClient
from app.core.config import settings

logger = logging.getLogger(__name__)

def enviar_email_acs(destinatario: str, asunto: str, cuerpo: str) -> None:
    """
    Atajo temporal para enviar correos directamente desde FastAPI usando ACS
    hasta que se tenga Azure Service Bus configurado.
    """
    if not destinatario:
        logger.warning(f"No hay destinatario, no se envía email. Asunto: {asunto}")
        return

    acs_connection_str = settings.ACS_CONNECTION_STR
    acs_from = settings.ACS_FROM_ADDRESS

    if not acs_connection_str or not acs_from:
        logger.error("Faltan credenciales ACS_CONNECTION_STR o ACS_FROM_ADDRESS en el .env")
        return

    try:
        client = EmailClient.from_connection_string(acs_connection_str)
        mensaje = {
            "senderAddress": acs_from,
            "recipients": {"to": [{"address": destinatario, "displayName": destinatario}]},
            "content": {"subject": asunto, "plainText": cuerpo},
        }

        logger.info(f"Enviando correo vía ACS a {destinatario}...")
        poller = client.begin_send(mensaje)
        resultado = poller.result()
        logger.info(f"✅ Email ACS enviado a {destinatario}: status={resultado.get('status')}")
    except Exception as e:
        logger.error(f"Error al enviar email por ACS: {str(e)}")
