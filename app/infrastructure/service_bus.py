import json
import logging
from datetime import datetime, timezone

from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def _construir_mensaje(evento: str, datos: dict) -> ServiceBusMessage:
    body = json.dumps({
        "evento": evento,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **datos,
    }, default=str)
    return ServiceBusMessage(body, content_type="application/json")


async def publicar_evento_ticket(evento:str, datos: dict) -> None:
    if not settings.AZURE_SERVICEBUS_CONNECTION_STR:
        logger.info("[ServiceBus-DEV] event=%s datos=%s", evento, datos)
        return
    
    async with ServiceBusClient.from_connection_string(
        settings.AZURE_SERVICEBUS_CONNECTION_STR
    ) as client:
        async with client.get_topic_sender(
            topic_name=settings.AZURE_SERVICEBUS_TOPIC
        ) as sender:
            mensaje = _construir_mensaje(evento, datos)
            await sender.send_messages(mensaje)
            logger.info("[ServiceBus] publicando eveneto=%s ticket_id=%s", evento, datos.get("ticket_id"))
