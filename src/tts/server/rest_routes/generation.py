"""TTS generation endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from ...models import TTSRequest
from ...models.schemas import OmniVoiceVoiceConfig
from ...auth import verify_api_key
from ...services import TTSService, VoiceService
from ...utils.config import CONFIG
from ...utils.audio_utils import AudioStreamEncoder
from ..common import load_voice_reference_or_raise, get_output_sample_rate
from ..dependencies import get_voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["generation"])


async def _resolve_voice(
    request: TTSRequest,
    voice_service: VoiceService,
    raise_on_not_found: bool = True,
) -> tuple:
    """Return (voice_reference, voice_transcript) for either clone or design mode."""
    voice_id = request.voice_config.voice_id

    if voice_id:
        voice_reference = await load_voice_reference_or_raise(
            voice_service, voice_id, raise_on_not_found=raise_on_not_found
        )
        voice_transcript = await voice_service.get_voice_transcript(voice_id) if voice_reference is not None else None
        return voice_reference, voice_transcript

    if isinstance(request.voice_config, OmniVoiceVoiceConfig) and request.voice_config.voice_description:
        return None, None

    if raise_on_not_found:
        raise HTTPException(
            status_code=400,
            detail="Provide voice_id (clone mode) or voice_description (OmniVoice design mode)"
        )
    return None, None


@router.post("/synthesize")
async def synthesize_tts(
    request: TTSRequest,
    voice_service: VoiceService = Depends(get_voice_service),
    api_key: str = Depends(verify_api_key)
):
    voice_reference, voice_transcript = await _resolve_voice(request, voice_service)

    async def generate_audio():
        async for chunk in TTSService.encode_audio_stream(request, voice_reference, voice_transcript):
            yield chunk

    output_sr = get_output_sample_rate(request)

    return StreamingResponse(
        generate_audio(),
        media_type=TTSService.get_media_type(request.audio_format),
        headers={
            "X-Sample-Rate": str(output_sr),
            "X-Audio-Format": request.audio_format,
        }
    )


@router.websocket("/stream")
async def websocket_tts(
    websocket: WebSocket,
    voice_service: VoiceService = Depends(get_voice_service),
):
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        data = await websocket.receive_json()

        api_key = data.get("api_key")
        if not api_key or api_key != CONFIG.api_key:
            await websocket.send_json({"error": "Invalid API key"})
            await websocket.close(code=1008)
            return

        request_data = {k: v for k, v in data.items() if k != "api_key"}

        try:
            request = TTSRequest(**request_data)
        except Exception:
            await websocket.send_json({"error": "Invalid request"})
            await websocket.close(code=1003)
            return

        voice_reference, voice_transcript = await _resolve_voice(
            request, voice_service, raise_on_not_found=False
        )

        voice_id = request.voice_config.voice_id
        if voice_id and voice_reference is None:
            await websocket.send_json({"error": f"Voice not found: {voice_id}"})
            await websocket.close(code=1003)
            return

        has_design = (
            isinstance(request.voice_config, OmniVoiceVoiceConfig)
            and request.voice_config.voice_description
        )
        if not voice_id and not has_design:
            await websocket.send_json({"error": "Provide voice_id or voice_description"})
            await websocket.close(code=1003)
            return

        output_sr = get_output_sample_rate(request)

        await websocket.send_json({
            "status": "streaming",
            "sample_rate": output_sr,
            "audio_format": request.audio_format
        })

        encoder = AudioStreamEncoder(request.audio_format, output_sr)
        async for audio_chunk, sample_rate in TTSService.synthesize_streaming(
            request, voice_reference, voice_transcript
        ):
            encoded_chunk = encoder.encode_chunk(audio_chunk)
            if encoded_chunk:
                await websocket.send_bytes(encoded_chunk)

        final_chunk = encoder.finalize()
        if final_chunk:
            await websocket.send_bytes(final_chunk)

        await websocket.send_json({"status": "complete"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except RuntimeError as e:
        logger.warning(f"WebSocket synthesis error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({"error": "Internal server error"})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
