import asyncio
import mercadopago
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize the SDK with the access token from config
_sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN) if settings.MERCADOPAGO_ACCESS_TOKEN else None

async def get_payment_info(payment_id: str) -> dict:
    """
    Fetches the payment details from Mercado Pago using the official SDK.
    Runs asynchronously using a thread pool to avoid blocking the event loop.
    """
    if not _sdk:
        logger.error("MERCADOPAGO_ACCESS_TOKEN is not configured.")
        raise ValueError("Mercado Pago SDK is not initialized.")
        
    def _fetch_payment():
        return _sdk.payment().get(payment_id)
        
    try:
        payment_data = await asyncio.to_thread(_fetch_payment)
        
        if payment_data.get("status") == 200:
            return payment_data.get("response", {})
        else:
            logger.error(f"Error fetching payment {payment_id}: {payment_data}")
            raise Exception(f"Failed to fetch payment info for {payment_id}")
            
    except Exception as e:
        logger.error(f"Error in MercadoPago integration: {e}")
        raise e

async def create_preference(ticket_id: int, monto_soles: float, webhook_url: str, success_url: str, failure_url: str) -> str:
    """
    Generates a MercadoPago Preference ID for a given ticket and amount.
    """
    if not _sdk:
        logger.error("MERCADOPAGO_ACCESS_TOKEN is not configured.")
        raise ValueError("Mercado Pago SDK is not initialized.")
        
    preference_data = {
        "items": [
            {
                "title": f"Pago de Ticket #{ticket_id}",
                "quantity": 1,
                "unit_price": float(monto_soles),
                "currency_id": "PEN"
            }
        ],
        "back_urls": {
            "success": success_url,
            "failure": failure_url
        },
        "external_reference": str(ticket_id),
        "notification_url": webhook_url
    }
    
    def _create_pref():
        return _sdk.preference().create(preference_data)
        
    try:
        preference_response = await asyncio.to_thread(_create_pref)
        
        if preference_response.get("status") == 201:
            return preference_response["response"].get("id")
        else:
            logger.error(f"Error creating MP preference: {preference_response}")
            raise Exception("Failed to create preference")
            
    except Exception as e:
        logger.error(f"Error in MercadoPago create preference: {e}")
        raise e
