"""ZMQ voice management handler."""

import base64
import dataclasses
import io
import logging
import msgpack

from ...services import VoiceService

logger = logging.getLogger(__name__)


async def _send_error(identity_frames: list, send_message, error: str):
    await send_message(identity_frames, b"error", msgpack.packb({"error": error}))


async def _send_response(identity_frames: list, send_message, data: dict):
    await send_message(identity_frames, b"response", msgpack.packb(data))


async def handle_list_voices(identity_frames: list, voice_service: VoiceService, send_message):
    """Handle list voices request."""
    try:
        voices_data = await voice_service.list_voices()
        await _send_response(
            identity_frames, send_message,
            {"status": "success", "voices": [dataclasses.asdict(v) for v in voices_data], "total": len(voices_data)}
        )
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        await _send_error(identity_frames, send_message, str(e))


async def _parse_upload_request(request_dict: dict) -> tuple[str, int, str, str]:
    voice_id = request_dict.get("voice_id")
    sample_rate = request_dict.get("sample_rate")
    voice_transcript = request_dict.get("voice_transcript")
    audio_data_b64 = request_dict.get("audio_data")
    
    if not all([voice_id, sample_rate, voice_transcript, audio_data_b64]):
        raise ValueError("Missing required fields: voice_id, sample_rate, voice_transcript, audio_data")
    
    return voice_id, int(sample_rate), str(voice_transcript), audio_data_b64


async def _decode_audio(audio_data_b64: str) -> io.BytesIO:
    try:
        audio_bytes = base64.b64decode(audio_data_b64)
        return io.BytesIO(audio_bytes)
    except Exception as e:
        raise ValueError(f"Invalid audio data encoding: {str(e)}")


async def handle_upload_voice(identity_frames: list, request_dict: dict, voice_service: VoiceService, send_message):
    """Handle voice upload request."""
    try:
        voice_id, sample_rate, voice_transcript, audio_data_b64 = _parse_upload_request(request_dict)
        
        if await voice_service.voice_exists(voice_id):
            await _send_error(
                identity_frames, send_message,
                f"Voice ID '{voice_id}' already exists."
            )
            return
        
        audio_file = await _decode_audio(audio_data_b64)
        
        success = await voice_service.upload_voice(
            voice_id=voice_id,
            audio_file=audio_file,
            sample_rate=sample_rate,
            voice_transcript=voice_transcript
        )
        
        if success:
            await _send_response(
                identity_frames, send_message,
                {"success": True, "voice_id": voice_id, "message": f"Voice '{voice_id}' uploaded successfully"}
            )
        else:
            await _send_error(
                identity_frames, send_message,
                f"Failed to upload voice '{voice_id}'"
            )
            
    except ValueError as e:
        logger.warning(f"Validation error uploading voice: {e}")
        await _send_error(identity_frames, send_message, str(e))
    except Exception as e:
        logger.error(f"Error uploading voice: {e}", exc_info=True)
        await _send_error(identity_frames, send_message, str(e))


async def _get_voice_id(request_dict: dict) -> str:
    voice_id = request_dict.get("voice_id")
    if not voice_id:
        raise ValueError("Missing required field: voice_id")
    return voice_id


async def handle_delete_voice(identity_frames: list, request_dict: dict, voice_service: VoiceService, send_message):
    """Handle voice deletion request."""
    try:
        voice_id = _get_voice_id(request_dict)
        logger.info(f"Voice deletion request: {voice_id}")
        
        success = await voice_service.delete_voice(voice_id)
        
        if success:
            await _send_response(
                identity_frames, send_message,
                {"success": True, "voice_id": voice_id, "message": f"Voice '{voice_id}' deleted successfully"}
            )
        else:
            await _send_error(
                identity_frames, send_message,
                f"Voice '{voice_id}' not found"
            )
            
    except ValueError as e:
        await _send_error(identity_frames, send_message, str(e))
    except Exception as e:
        logger.error(f"Error deleting voice: {e}", exc_info=True)
        await _send_error(identity_frames, send_message, str(e))
