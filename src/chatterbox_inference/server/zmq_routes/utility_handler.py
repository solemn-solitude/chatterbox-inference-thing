"""ZMQ utility handlers (health, model management)."""

import json
import logging

from ...services import ModelService

logger = logging.getLogger(__name__)


async def handle_health(client_id: bytes, send_message):
    """Handle health check request.
    
    Args:
        client_id: Client identity
        send_message: Callback to send messages
    """
    status = ModelService.get_model_status()
    response = {
        "status": "healthy",
        "model_loaded": status["model_loaded"],
        "version": "0.1.0"
    }
    await send_message(client_id, b"response", json.dumps(response).encode('utf-8'))


async def handle_model_unload(client_id: bytes, send_message):
    """Handle model unload request.
    
    Args:
        client_id: Client identity
        send_message: Callback to send messages
    """
    try:
        result = await ModelService.unload_model()
        await send_message(client_id, b"response", json.dumps(result).encode('utf-8'))
    except Exception as e:
        logger.error(f"Error unloading model: {e}", exc_info=True)
        await send_message(client_id, b"error", json.dumps({"error": str(e)}).encode())
