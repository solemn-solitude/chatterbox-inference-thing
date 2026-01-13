"""ZMQ request handlers."""

from .generation_handler import handle_synthesize
from .voice_handler import handle_list_voices, handle_upload_voice, handle_delete_voice
from .utility_handler import handle_health, handle_ready, handle_model_unload

__all__ = [
    "handle_synthesize",
    "handle_list_voices",
    "handle_upload_voice",
    "handle_delete_voice",
    "handle_health",
    "handle_ready",
    "handle_model_unload"
]
