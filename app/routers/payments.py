from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.responses import success
from app.models.ticket import Ticket, TicketEstado
from app.models.pago import Pago, PagoEstado
from app.models.cliente import Cliente
from app.models.tecnico import Tecnico
from app.services.mercadopago_service import get_payment_info, create_preference

# Importación de Azure Service Bus
from app.infrastructure.service_bus import publicar_evento_ticket
# Importación temporal de atajo ACS
from app.infrastructure.acs_email_local import enviar_email_acs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payments")

class PreferenceRequest(BaseModel):
    ticket_id: str

@router.post("/preference", response_model=None, tags=["Payments-Publico"])
async def generate_payment_preference(request: PreferenceRequest, db: AsyncSession = Depends(get_db)):
    """
    Genera un preference_id de Mercado Pago para inicializar el Checkout Pro (Brick).
    Valida que el ticket esté en EN_ESPERA_PAGO.
    """
    try:
        # Obtener el ticket de la DB
        result = await db.execute(select(Ticket).where(Ticket.ticket_id == request.ticket_id))
        ticket = result.scalars().first()
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
            
        if ticket.estado != TicketEstado.EN_ESPERA_PAGO:
            raise HTTPException(status_code=400, detail="El ticket no está pendiente de pago")
            
        # Generar preferencia (Monto en S/.)
        # Nota: Configura las URLs de retorno según tu frontend
        success_url = "http://localhost:3000/pago-exitoso"
        failure_url = "http://localhost:3000/pago-fallido"
        webhook_url = "https://rumor-designing-unaudited.ngrok-free.dev/api/v1/payments/webhook"
        
        preference_id = await create_preference(
            ticket_id=str(ticket.ticket_id),
            monto_soles=float(ticket.precio_final),
            webhook_url=webhook_url,
            success_url=success_url,
            failure_url=failure_url
        )
        
        return success({"preference_id": preference_id})
        
    except Exception as e:
        logger.error(f"Error generando preferencia: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al generar preferencia de pago")


@router.post("/webhook", summary="Payment Listener Webhook (Mercado Pago)", tags=["Payments-Webhook"])
async def payment_listener_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    === PAYMENT LISTENER (WEBHOOK) ===
    Esta función actúa como el 'Listener' pasivo que espera las notificaciones de Mercado Pago.
    
    ¿Cómo funciona para el próximo desarrollador?
    1. Mercado Pago envía una petición POST aquí cuando un cliente paga.
    2. El Listener extrae el payment_id y le pregunta a MP si el pago es real y está aprobado.
    3. Si es real, actualiza la base de datos (Ticket -> EN_PROGRESO y crea registro en pagos.pago).
    4. Dispara los correos (vía ACS temporalmente).
    5. Retorna 200 OK a Mercado Pago para que sepa que ya procesamos la notificación.
    """
    try:
        # Extraer query params (a veces MP los envía por query strings)
        topic = request.query_params.get("topic")
        payment_id_query = request.query_params.get("id")
        
        # Extraer body JSON (por defecto MP envía action y data.id)
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
            
        action = body.get("action")
        payment_id_body = body.get("data", {}).get("id")
        
        # Validar si es una notificación de pago actualizado o creado
        if action in ("payment.updated", "payment.created") or topic == "payment":
            payment_id = payment_id_body or payment_id_query
            
            if not payment_id:
                return {"status": "ok", "message": "No payment ID provided"}
                
            logger.info(f"Procesando webhook para payment_id: {payment_id}")
            
            # Consultar API de Mercado Pago para validar
            payment_info = await get_payment_info(str(payment_id))
            
            status = payment_info.get("status")
            external_reference = payment_info.get("external_reference") # Este es nuestro ticket_id
            monto_cobrado = float(payment_info.get("transaction_amount", 0))
            
            if status == "approved" and external_reference:
                # 1. Obtener Ticket
                result = await db.execute(select(Ticket).where(Ticket.ticket_id == external_reference))
                ticket = result.scalars().first()
                
                if not ticket:
                    logger.error(f"Ticket {external_reference} no encontrado para el pago {payment_id}")
                    return {"status": "error", "message": "Ticket not found"}
                
                if ticket.estado == TicketEstado.EN_PROGRESO:
                    logger.info(f"El ticket {ticket.ticket_id} ya fue procesado y pagado.")
                    return {"status": "ok"}
                
                # 2. Validar Montos (Sin pagos parciales)
                if float(ticket.precio_final) != monto_cobrado:
                    logger.warning(f"Monto cobrado ({monto_cobrado}) no coincide con precio final del ticket ({ticket.precio_final}). Se rechaza.")
                    return {"status": "ok", "message": "Partial payments not allowed"}
                
                # 3. Actualizar Ticket y registrar Pago
                ticket.estado = TicketEstado.EN_PROGRESO
                
                # 4. Disparar Evento a Azure Service Bus
                await publicar_evento_ticket("PAGO_CONFIRMADO", {
                    "ticket_id": str(ticket.ticket_id),
                    "monto_cobrado": monto_cobrado,
                    "payment_id": str(payment_id)
                })
                
                # 5. [ATAJO TEMPORAL] Enviar correo directo por ACS
                # Obtener correo del cliente
                cliente = (await db.execute(select(Cliente).where(Cliente.cliente_id == ticket.cliente_id))).scalars().first()
                if cliente and cliente.email:
                    enviar_email_acs(
                        destinatario=cliente.email,
                        asunto="¡Pago Confirmado! - TechFix",
                        cuerpo=f"Hola {cliente.nombre},\n\nHemos recibido exitosamente tu pago de S/ {monto_cobrado} por el ticket {ticket.ticket_id}.\nTu equipo ya está en progreso de reparación.\n\n— Equipo TechFix"
                    )
                
                # Obtener correo del tecnico
                if ticket.tecnico_id:
                    tecnico = (await db.execute(select(Tecnico).where(Tecnico.tecnico_id == ticket.tecnico_id))).scalars().first()
                    if tecnico and tecnico.email:
                        enviar_email_acs(
                            destinatario=tecnico.email,
                            asunto="Nuevo Pago Confirmado - TechFix",
                            cuerpo=f"Hola {tecnico.nombre},\n\nEl cliente acaba de pagar S/ {monto_cobrado} por el ticket {ticket.ticket_id}.\nYa puedes iniciar la reparación."
                        )
                
                # Registrar el pago oficial en la tabla de pagos
                nuevo_pago = Pago(
                    ticket_id=ticket.ticket_id,
                    monto=monto_cobrado,
                    monto_esperado=float(ticket.precio_final),
                    referencia_culqi=str(payment_id), # Guardamos el payment_id de MP aquí temporalmente
                    estado=PagoEstado.CONFIRMADO,
                    recibido_en=datetime.now(timezone.utc)
                )
                db.add(nuevo_pago)
                await db.commit()
                
                logger.info(f"✅ Pago Confirmado! Ticket {ticket.ticket_id} pasó a EN_PROGRESO.")
                
                # 4. Disparar Evento a Azure Service Bus
                # publicar_pago_confirmado(ticket.ticket_id, monto_cobrado, str(payment_id))
                
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}")
        # MP requiere un HTTP 200/201 de vuelta para saber que recibimos la notificacion. 
        # Si retornamos 500, seguira reintentando.
        return {"status": "error", "detail": str(e)}
