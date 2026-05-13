"""ZMQ TTS generation handler."""

import logging
import msgpack

from ...models import TTSRequest
from ...models.schemas import OmniVoiceVoiceConfig
from ...services import TTSService, VoiceService
from ...utils.audio_utils import AudioStreamEncoder
from ...utils.config import CONFIG
from ..common import load_voice_reference_or_raise, get_output_sample_rate

_ENGINE_DEFAULT_VOICE_CONFIG = {
    "chatterbox": {"type": "chatterbox"},
    "omnivoice": {"type": "omnivoice"},
    "fish-speech": {"type": "fish-speech"},
}

logger = logging.getLogger(__name__)


def _get_client_id(identity_frames: list) -> str:
    return identity_frames[0].hex()[:8] if identity_frames else "unknown"


async def _send_error(identity_frames: list, send_message, error_msg: str):
    await send_message(identity_frames, b"error", msgpack.packb({"error": error_msg}))


async def _send_metadata(identity_frames: list, send_message, metadata: dict):
    await send_message(identity_frames, b"metadata", msgpack.packb(metadata))


async def _send_audio_chunk(identity_frames: list, send_message, encoded_chunk: bytes):
    await send_message(identity_frames, b"audio", encoded_chunk)


async def _send_complete(identity_frames: list, send_message, chunk_count: int):
    completion = {"status": "complete", "chunks": chunk_count}
    await send_message(identity_frames, b"complete", msgpack.packb(completion))


async def _stream_audio(
    identity_frames: list,
    send_message,
    request: TTSRequest,
    voice_reference,
    voice_transcript,
) -> int:
    output_sr = get_output_sample_rate(request)
    encoder = AudioStreamEncoder(request.audio_format, output_sr)

    chunk_count = 0
    async for audio_chunk, sample_rate in TTSService.synthesize_streaming(
        request, voice_reference, voice_transcript
    ):
        encoded_chunk = encoder.encode_chunk(audio_chunk)
        if encoded_chunk:
            await _send_audio_chunk(identity_frames, send_message, encoded_chunk)
            chunk_count += 1

    final_chunk = encoder.finalize()
    if final_chunk:
        await _send_audio_chunk(identity_frames, send_message, final_chunk)
        chunk_count += 1
        logger.info(f"Sent finalized audio chunk: {len(final_chunk)} bytes")

    return chunk_count


async def handle_synthesize(identity_frames: list, request_dict: dict, voice_service: VoiceService, send_message):
    try:
        if "voice_config" not in request_dict:
            default = _ENGINE_DEFAULT_VOICE_CONFIG.get(CONFIG.tts_engine, {"type": "chatterbox"})
            request_dict = {**request_dict, "voice_config": default}

        request = TTSRequest(**request_dict)

        voice_id = request.voice_config.voice_id or CONFIG.default_voice_id
        voice_description = (
            request.voice_config.voice_description
            if isinstance(request.voice_config, OmniVoiceVoiceConfig)
            else None
        )

        if not voice_id and not voice_description:
            await _send_error(
                identity_frames, send_message,
                "No voice_id provided and no default configured (TTS_DEFAULT_VOICE_ID). "
                "For OmniVoice voice design, use OmniVoiceVoiceConfig with voice_description."
            )
            return

        client_id_hex = _get_client_id(identity_frames)
        voice_reference = None
        voice_transcript = None

        if voice_id:
            logger.info(f"TTS synthesis request from client {client_id_hex}: voice_id={voice_id}")
            voice_reference = await load_voice_reference_or_raise(
                voice_service, voice_id, raise_on_not_found=False
            )
            if voice_reference is None:
                await _send_error(
                    identity_frames, send_message,
                    f"Voice not found in database: {voice_id}"
                )
                return
            voice_transcript = await voice_service.get_voice_transcript(voice_id)
        else:
            logger.info(f"TTS synthesis request from client {client_id_hex}: voice_design mode")

        metadata = {
            "status": "streaming",
            "sample_rate": get_output_sample_rate(request),
            "audio_format": request.audio_format
        }
        await _send_metadata(identity_frames, send_message, metadata)

        chunk_count = await _stream_audio(
            identity_frames, send_message, request, voice_reference, voice_transcript
        )

        await _send_complete(identity_frames, send_message, chunk_count)
        logger.info(f"TTS synthesis complete for client {client_id_hex}: {chunk_count} chunks sent")

    except Exception as e:
        logger.error(f"Error in synthesize handler: {e}", exc_info=True)
        await _send_error(identity_frames, send_message, str(e))
