"""ZMQ utility handlers (health, model management)."""

import logging
import msgpack

from ...services import ModelService

logger = logging.getLogger(__name__)


async def _send_response(identity_frames: list, send_message, data: dict):
    await send_message(identity_frames, b"response", msgpack.packb(data))


async def _send_error(identity_frames: list, send_message, error: str):
    await send_message(identity_frames, b"error", msgpack.packb({"error": error}))


async def handle_health(identity_frames: list, send_message):
    """Handle health check request."""
    status = ModelService.get_model_status()
    await _send_response(
        identity_frames, send_message,
        {"status": "healthy", "model_loaded": status["model_loaded"], "version": "0.1.0"}
    )


async def handle_ready(identity_frames: list, send_message):
    """Handle readiness check request."""
    status = ModelService.get_model_status()
    
    ready = (
        status["model_loaded"] and 
        status["voice_dir_accessible"] and 
        status["database_accessible"]
    )
    
    await _send_response(identity_frames, send_message, {"ready": ready, **status})


async def handle_model_unload(identity_frames: list, send_message):
    """Handle model unload request."""
    try:
        result = await ModelService.unload_model()
        await _send_response(identity_frames, send_message, result)
    except Exception as e:
        logger.error(f"Error unloading model: {e}", exc_info=True)
        await _send_error(identity_frames, send_message, str(e))
