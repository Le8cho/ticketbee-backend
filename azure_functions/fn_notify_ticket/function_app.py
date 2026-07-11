import json
import logging

import azure.functions as func

from notify_logic import procesar_evento

app = func.FunctionApp()

logger = logging.getLogger(__name__)


@app.service_bus_topic_trigger(
    arg_name="msg",
    topic_name="%SERVICEBUS_TOPIC_NAME%",
    subscription_name="%SERVICEBUS_SUBSCRIPTION_NOTIFY%",
    connection="SERVICEBUS_CONNECTION",
)
def fn_notify_ticket(msg: func.ServiceBusMessage):
    body = msg.get_body().decode("utf-8")
    payload = json.loads(body)

    logger.info("Mensaje recibido: %s", payload.get("evento"))

    resultado = procesar_evento(payload)

    logger.info("Resultado: %s", resultado)
