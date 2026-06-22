import json
import logging

import azure.functions as func

from garantia_logic import procesar_evento

app = func.FunctionApp()

logger = logging.getLogger(__name__)


@app.service_bus_topic_trigger(
    arg_name="msg",
    topic_name="%SERVICEBUS_TOPIC_NAME%",
    subscription_name="%SERVICEBUS_SUBSCRIPTION_WARRANTY%",
    connection="SERVICEBUS_CONNECTION",
)
def fn_warranty(msg: func.ServiceBusMessage):
    body = msg.get_body().decode("utf-8")
    payload = json.loads(body)

    logger.info("Mensaje recibido: %s", payload.get("evento"))

    resultado = procesar_evento(payload)

    logger.info("Resultado: %s", resultado)
