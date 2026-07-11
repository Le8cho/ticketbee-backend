import logging

import azure.functions as func

from archivado_logic import archivar_tickets_vencidos

app = func.FunctionApp()

logger = logging.getLogger(__name__)


@app.timer_trigger(arg_name="timer", schedule="0 0 0 * * *")
def fn_file_ticket(timer: func.TimerRequest) -> None:
    """Corre una vez al dia (medianoche). Archiva tickets FINALIZADO cuya garantia ya vencio."""
    resultado = archivar_tickets_vencidos()
    logger.info("Archivado automatico: %s", resultado)
