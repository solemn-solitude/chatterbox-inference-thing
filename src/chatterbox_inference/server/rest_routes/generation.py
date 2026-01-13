"""TTS generation endpoints."""

import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from ...models import TTSRequest
from ...auth import verify_api_key
from ...services import TTSService, VoiceService
from ...utils.config import config
from ...utils.audio_utils import AudioStreamEncoder
from ..dependencies import get_voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["generation"])


@router.post("/synthesize")
async def synthesize_tts(
    request: TTSRequest,
    voice_service: VoiceService = Depends(get_voice_service),
    api_key: str = Depends(verify_api_key)
) -> StreamingResponse:
    """Synthesize TTS with streaming response."""
    logger.info(f"TTS request: mode={request.voice_mode}, format={request.audio_format}")
    
    # Load voice reference if in clone mode
    voice_reference = None
    if request.voice_mode == "clone":
        voice_reference = await voice_service.load_voice_reference(request.voice_config.voice_id)
        if voice_reference is None:
            raise HTTPException(status_code=404, detail=f"Voice not found: {request.voice_config.voice_id}")
    
    # Get output sample rate
    from ...tts import get_tts_engine
    tts_engine = get_tts_engine()
    output_sr = request.sample_rate or tts_engine.sample_rate
    
    async def generate_audio() -> AsyncIterator[bytes]:
        """Generate audio stream."""
        try:
            async for chunk in TTSService.encode_audio_stream(request, voice_reference):
                yield chunk
        except Exception as e:
            logger.error(f"Error during TTS synthesis: {e}")
            raise
    
    return StreamingResponse(
        generate_audio(),
        media_type=TTSService.get_media_type(request.audio_format),
        headers={
            "X-Sample-Rate": str(output_sr),
            "X-Audio-Format": request.audio_format,
        }
    )


@router.websocket("/stream")
async def websocket_tts(websocket: WebSocket):
    """WebSocket endpoint for bidirectional TTS streaming."""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        data = await websocket.receive_json()
        
        # Verify API key
        api_key = data.get("api_key")
        if api_key != config.api_key:
            await websocket.send_json({"error": "Invalid API key"})
            await websocket.close(code=1008)
            return
        
        # Parse request
        try:
            request = TTSRequest(**data)
        except Exception as e:
            await websocket.send_json({"error": f"Invalid request: {str(e)}"})
            await websocket.close(code=1003)
            return
        
        # Get services (manually since WebSocket doesn't support Depends)
        from ..dependencies import voice_service
        
        # Load voice reference if needed
        voice_reference = None
        if request.voice_mode == "clone":
            voice_reference = await voice_service.load_voice_reference(request.voice_config.voice_id)
            if voice_reference is None:
                await websocket.send_json({"error": f"Voice not found: {request.voice_config.voice_id}"})
                await websocket.close(code=1003)
                return
        
        # Get output sample rate
        from ...tts import get_tts_engine
        tts_engine = get_tts_engine()
        output_sr = request.sample_rate or tts_engine.sample_rate
        
        # Send start message
        await websocket.send_json({
            "status": "streaming",
            "sample_rate": output_sr,
            "audio_format": request.audio_format
        })
        
        # Create encoder
        encoder = AudioStreamEncoder(request.audio_format, output_sr)
        
        # Stream audio
        try:
            async for audio_chunk, sample_rate in TTSService.synthesize_streaming(request, voice_reference):
                encoded_chunk = encoder.encode_chunk(audio_chunk)
                await websocket.send_bytes(encoded_chunk)
            
            await websocket.send_json({"status": "complete"})
            
        except Exception as e:
            logger.error(f"Error during WebSocket TTS: {e}")
            await websocket.send_json({"error": str(e)})
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
