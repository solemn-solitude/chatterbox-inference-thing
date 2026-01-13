"""ZMQ TTS generation handler."""

import json
import logging

from ...models import TTSRequest
from ...services import TTSService, VoiceService
from ...utils.audio_utils import AudioStreamEncoder

logger = logging.getLogger(__name__)


async def handle_synthesize(client_id: bytes, request_dict: dict, voice_service: VoiceService, send_message):
    """Handle TTS synthesis request.
    
    Args:
        client_id: Client identity
        request_dict: Request dictionary
        voice_service: Voice service instance
        send_message: Callback to send messages
    """
    try:
        # Parse TTS request
        request = TTSRequest(**request_dict)
        
        logger.info(f"TTS synthesis request from client {client_id.hex()[:8]}: mode={request.voice_mode}")
        
        # Load voice reference if needed
        voice_reference = None
        if request.voice_mode == "clone":
            voice_reference = await voice_service.load_voice_reference(request.voice_config.voice_id)
            if voice_reference is None:
                await send_message(client_id, b"error", json.dumps({"error": f"Voice not found: {request.voice_config.voice_id}"}).encode())
                return
        
        # Get output sample rate
        from ...tts import get_tts_engine
        tts_engine = get_tts_engine()
        output_sr = request.sample_rate or tts_engine.sample_rate
        
        # Send metadata first
        metadata = {
            "status": "streaming",
            "sample_rate": output_sr,
            "audio_format": request.audio_format
        }
        await send_message(client_id, b"metadata", json.dumps(metadata).encode('utf-8'))
        
        # Create encoder
        encoder = AudioStreamEncoder(request.audio_format, output_sr)
        
        # Stream audio chunks
        chunk_count = 0
        async for audio_chunk, sample_rate in TTSService.synthesize_streaming(request, voice_reference):
            encoded_chunk = encoder.encode_chunk(audio_chunk)
            await send_message(client_id, b"audio", encoded_chunk)
            chunk_count += 1
        
        # Send completion message
        completion = {"status": "complete", "chunks": chunk_count}
        await send_message(client_id, b"complete", json.dumps(completion).encode('utf-8'))
        
        logger.info(f"TTS synthesis complete for client {client_id.hex()[:8]}: {chunk_count} chunks sent")
        
    except Exception as e:
        logger.error(f"Error in synthesize handler: {e}", exc_info=True)
        await send_message(client_id, b"error", json.dumps({"error": str(e)}).encode())
