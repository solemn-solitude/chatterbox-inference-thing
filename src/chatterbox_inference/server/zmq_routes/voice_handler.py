"""ZMQ voice management handler."""

import base64
import io
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


async def handle_upload_voice(client_id: bytes, request_dict: dict, voice_service: VoiceService, send_message):
    """Handle voice upload request.
    
    Args:
        client_id: Client identity
        request_dict: Request dictionary containing voice_id, sample_rate, and audio_data (base64)
        voice_service: Voice service instance
        send_message: Callback to send messages
    """
    try:
        voice_id = request_dict.get("voice_id")
        sample_rate = request_dict.get("sample_rate")
        audio_data_b64 = request_dict.get("audio_data")
        
        if not voice_id or not sample_rate or not audio_data_b64:
            await send_message(client_id, b"error", json.dumps({
                "error": "Missing required fields: voice_id, sample_rate, audio_data"
            }).encode())
            return
        
        # Check if voice already exists
        if await voice_service.voice_exists(voice_id):
            await send_message(client_id, b"error", json.dumps({
                "error": f"Voice ID '{voice_id}' already exists. Please use a different identifier or delete the existing voice first."
            }).encode())
            return
        
        # Decode base64 audio data
        try:
            audio_bytes = base64.b64decode(audio_data_b64)
            audio_file = io.BytesIO(audio_bytes)
        except Exception as e:
            logger.error(f"Error decoding audio data: {e}")
            await send_message(client_id, b"error", json.dumps({
                "error": f"Invalid audio data encoding: {str(e)}"
            }).encode())
            return
        
        # Upload voice
        success = await voice_service.upload_voice(
            voice_id=voice_id,
            audio_file=audio_file,
            sample_rate=int(sample_rate)
        )
        
        if success:
            response = {
                "success": True,
                "voice_id": voice_id,
                "message": f"Voice '{voice_id}' uploaded successfully"
            }
            await send_message(client_id, b"response", json.dumps(response).encode('utf-8'))
        else:
            await send_message(client_id, b"error", json.dumps({
                "error": f"Failed to upload voice '{voice_id}'"
            }).encode())
            
    except ValueError as e:
        logger.warning(f"Validation error uploading voice: {e}")
        await send_message(client_id, b"error", json.dumps({"error": str(e)}).encode())
    except Exception as e:
        logger.error(f"Error uploading voice: {e}", exc_info=True)
        await send_message(client_id, b"error", json.dumps({"error": str(e)}).encode())


async def handle_delete_voice(client_id: bytes, request_dict: dict, voice_service: VoiceService, send_message):
    """Handle voice deletion request.
    
    Args:
        client_id: Client identity
        request_dict: Request dictionary containing voice_id
        voice_service: Voice service instance
        send_message: Callback to send messages
    """
    try:
        voice_id = request_dict.get("voice_id")
        
        if not voice_id:
            await send_message(client_id, b"error", json.dumps({
                "error": "Missing required field: voice_id"
            }).encode())
            return
        
        logger.info(f"Voice deletion request: {voice_id}")
        
        success = await voice_service.delete_voice(voice_id)
        
        if success:
            response = {
                "success": True,
                "voice_id": voice_id,
                "message": f"Voice '{voice_id}' deleted successfully"
            }
            await send_message(client_id, b"response", json.dumps(response).encode('utf-8'))
        else:
            await send_message(client_id, b"error", json.dumps({
                "error": f"Voice '{voice_id}' not found"
            }).encode())
            
    except Exception as e:
        logger.error(f"Error deleting voice: {e}", exc_info=True)
        await send_message(client_id, b"error", json.dumps({"error": str(e)}).encode())
