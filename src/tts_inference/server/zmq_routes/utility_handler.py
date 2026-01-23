"""ZMQ utility handlers (health, model management)."""

import json
import logging

from ...services import ModelService

logger = logging.getLogger(__name__)


async def handle_health(identity_frames: list, send_message):
    """Handle health check request.
    
    Args:
        identity_frames: Client identity frames from ROUTER
        send_message: Callback to send messages
    """
    status = ModelService.get_model_status()
    response = {
        "status": "healthy",
        "model_loaded": status["model_loaded"],
        "version": "0.1.0"
    }
    await send_message(identity_frames, b"response", json.dumps(response).encode('utf-8'))


async def handle_ready(identity_frames: list, send_message):
    """Handle readiness check request.
    
    Args:
        identity_frames: Client identity frames from ROUTER
        send_message: Callback to send messages
    """
    status = ModelService.get_model_status()
    
    ready = (
        status["model_loaded"] and 
        status["voice_dir_accessible"] and 
        status["database_accessible"]
    )
    
    response = {
        "ready": ready,
        **status
    }
    await send_message(identity_frames, b"response", json.dumps(response).encode('utf-8'))


async def handle_model_unload(identity_frames: list, send_message):
    """Handle model unload request.
    
    Args:
        identity_frames: Client identity frames from ROUTER
        send_message: Callback to send messages
    """
    try:
        result = await ModelService.unload_model()
        await send_message(identity_frames, b"response", json.dumps(result).encode('utf-8'))
    except Exception as e:
        logger.error(f"Error unloading model: {e}", exc_info=True)
        await send_message(identity_frames, b"error", json.dumps({"error": str(e)}).encode())
