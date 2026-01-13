"""ZMQ voice management handler."""

import json
import logging

from ...services import VoiceService

logger = logging.getLogger(__name__)


async def handle_list_voices(client_id: bytes, voice_service: VoiceService, send_message):
    """Handle list voices request.
    
    Args:
        client_id: Client identity
        voice_service: Voice service instance
        send_message: Callback to send messages
    """
    try:
        voices_data = await voice_service.list_voices()
        response = {
            "status": "success",
            "voices": voices_data,
            "total": len(voices_data)
        }
        await send_message(client_id, b"response", json.dumps(response).encode('utf-8'))
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        await send_message(client_id, b"error", json.dumps({"error": str(e)}).encode())
