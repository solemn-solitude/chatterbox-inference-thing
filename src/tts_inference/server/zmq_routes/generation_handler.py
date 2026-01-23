"""ZMQ TTS generation handler."""

import json
import logging

from ...models import TTSRequest
from ...services import TTSService, VoiceService
from ...utils.audio_utils import AudioStreamEncoder

logger = logging.getLogger(__name__)


async def handle_synthesize(identity_frames: list, request_dict: dict, voice_service: VoiceService, send_message):
    """Handle TTS synthesis request.
    
    Args:
        identity_frames: Client identity frames from ROUTER
        request_dict: Request dictionary
        voice_service: Voice service instance
        send_message: Callback to send messages
    """
    try:
        # Parse TTS request
        request = TTSRequest(**request_dict)
        
        # Get client ID for logging (first identity frame)
        client_id_hex = identity_frames[0].hex()[:8] if identity_frames else "unknown"
        logger.info(f"TTS synthesis request from client {client_id_hex}: mode={request.voice_mode}")
        
        # Load voice reference if needed
        voice_reference = None
        if request.voice_mode == "clone":
            voice_reference = await voice_service.load_voice_reference(request.voice_config.voice_id)
            if voice_reference is None:
                await send_message(identity_frames, b"error", json.dumps({"error": f"Voice not found: {request.voice_config.voice_id}"}).encode())
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
        await send_message(identity_frames, b"metadata", json.dumps(metadata).encode('utf-8'))
        
        # Create encoder
        encoder = AudioStreamEncoder(request.audio_format, output_sr)
        
        # Stream audio chunks
        chunk_count = 0
        async for audio_chunk, sample_rate in TTSService.synthesize_streaming(request, voice_reference):
            encoded_chunk = encoder.encode_chunk(audio_chunk)
            if encoded_chunk:  # Only send non-empty chunks (PCM returns data, WAV/Vorbis return empty)
                await send_message(identity_frames, b"audio", encoded_chunk)
                chunk_count += 1
        
        # Finalize encoding (critical for WAV/Vorbis formats that accumulate chunks)
        final_chunk = encoder.finalize()
        if final_chunk:
            await send_message(identity_frames, b"audio", final_chunk)
            chunk_count += 1
            logger.info(f"Sent finalized audio chunk: {len(final_chunk)} bytes")
        
        # Send completion message
        completion = {"status": "complete", "chunks": chunk_count}
        await send_message(identity_frames, b"complete", json.dumps(completion).encode('utf-8'))
        
        logger.info(f"TTS synthesis complete for client {client_id_hex}: {chunk_count} chunks sent")
        
    except Exception as e:
        logger.error(f"Error in synthesize handler: {e}", exc_info=True)
        await send_message(identity_frames, b"error", json.dumps({"error": str(e)}).encode())
