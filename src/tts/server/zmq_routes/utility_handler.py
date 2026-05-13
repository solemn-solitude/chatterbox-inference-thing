"""ZMQ utility handlers (health, model management)."""

import logging
import msgpack
from dataclasses import asdict

from ...services import ModelService
from ...tts.base_tts import BaseTTSEngine
from ...tts import engine as _engine_module  # ensure engine subclasses are imported

logger = logging.getLogger(__name__)


async def _send_response(identity_frames: list, send_message, data: dict):
    await send_message(identity_frames, b"response", msgpack.packb(data))


async def _send_error(identity_frames: list, send_message, error: str):
    await send_message(identity_frames, b"error", msgpack.packb({"error": error}))


async def handle_health(identity_frames: list, send_message):
    status = ModelService.get_model_status()
    await _send_response(
        identity_frames, send_message,
        {"status": "healthy", "version": "0.1.0", **asdict(status)}
    )


async def handle_ready(identity_frames: list, send_message):
    status = ModelService.get_model_status()
    ready = status.model_loaded and status.voice_dir_accessible and status.database_accessible
    await _send_response(identity_frames, send_message, {"ready": ready, **asdict(status)})


async def handle_model_unload(identity_frames: list, send_message):
    """Handle model unload request."""
    try:
        result = await ModelService.unload_model()
        await _send_response(identity_frames, send_message, result)
    except Exception as e:
        logger.error(f"Error unloading model: {e}", exc_info=True)
        await _send_error(identity_frames, send_message, str(e))


async def handle_list_engines(identity_frames: list, send_message):
    engines = [cls.engine_name for cls in BaseTTSEngine.__subclasses__()]
    await _send_response(identity_frames, send_message, {"engines": engines})


async def handle_list_engine_params(identity_frames: list, send_message, engine_name: str):
    for cls in BaseTTSEngine.__subclasses__():
        if cls.engine_name == engine_name:
            await _send_response(identity_frames, send_message, {"params": cls.engine_params})
            return
    await _send_error(identity_frames, send_message, f"Unknown engine: {engine_name!r}")
