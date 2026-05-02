"""TTS synthesis service - shared business logic."""

from pathlib import Path
import logging
import numpy as np

from ..tts import get_tts_engine
from ..tts.voice_manager import VoiceManager
from ..models import TTSRequest
from ..models.database import VoiceDatabase
from ..utils.audio_utils import AudioStreamEncoder
from ..utils.config import CONFIG
from ..models.service_dataclasses import TestSamplesResult, TestSamplesFile
from .synthesis_queue import get_synthesis_queue

logger = logging.getLogger(__name__)


class TTSService:
    """Service for TTS synthesis operations."""

    @staticmethod
    def _chatterbox_params(request: TTSRequest, voice_reference: np.ndarray) -> dict:
        return {
            "text": request.text,
            "voice_id": request.voice_config.voice_id,
            "voice_reference": voice_reference,
            "speed": request.voice_config.speed,
            "sample_rate": request.sample_rate,
            "use_turbo": request.use_turbo,
            "exaggeration": request.voice_config.exaggeration,
            "cfg_weight": request.voice_config.cfg_weight,
            "temperature": request.voice_config.temperature,
            "repetition_penalty": request.voice_config.repetition_penalty,
        }

    @staticmethod
    async def synthesize_streaming(
        request: TTSRequest,
        voice_reference: np.ndarray,
        voice_transcript: str | None = None,
    ):
        params = TTSService._chatterbox_params(request, voice_reference)
        async for chunk, sr in get_synthesis_queue().submit(params):
            yield chunk, sr

    @staticmethod
    async def encode_audio_stream(
        request: TTSRequest,
        voice_reference: np.ndarray,
        voice_transcript: str | None = None
    ):
        output_sr = request.sample_rate or get_tts_engine().sample_rate
        encoder = AudioStreamEncoder(request.audio_format, output_sr)

        if request.audio_format == "pcm":
            async for audio_chunk, sample_rate in TTSService.synthesize_streaming(
                request, voice_reference, voice_transcript
            ):
                yield encoder.encode_chunk(audio_chunk)
        else:
            async for audio_chunk, sample_rate in TTSService.synthesize_streaming(
                request, voice_reference, voice_transcript
            ):
                encoder.encode_chunk(audio_chunk)

            encoded_data = encoder.finalize()
            if encoded_data:
                yield encoded_data

    @staticmethod
    def get_media_type(audio_format: str) -> str:
        media_types = {
            "pcm": "audio/pcm",
            "wav": "audio/wav",
            "vorbis": "audio/ogg",
        }
        return media_types.get(audio_format, "application/octet-stream")

    @staticmethod
    async def _load_voice_ref_and_transcript(
        voice_manager: VoiceManager,
        db: VoiceDatabase,
        voice_id: str,
        list_available: bool = False
    ) -> tuple[np.ndarray, str | None]:
        voice_reference = await voice_manager.load_voice_reference(voice_id)
        if voice_reference is None:
            if list_available:
                voices = await db.list_voices()
                available = [v.voice_id for v in voices]
                raise ValueError(f"Voice not found: {voice_id}. Available: {', '.join(available)}")
            raise ValueError(f"Voice not found: {voice_id}")

        record = await db.get_voice(voice_id)
        return voice_reference, record.voice_transcript if record else None

    @staticmethod
    async def generate_test_samples(
        text: str,
        voice_id: str,
        output_dir: str,
        voice_manager: VoiceManager | None = None,
        db: VoiceDatabase | None = None,
        use_turbo: bool = False,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        repetition_penalty: float | None = None,
    ) -> TestSamplesResult:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if db is None:
            db = VoiceDatabase(CONFIG.database_path)
            await db.initialize()
        if voice_manager is None:
            voice_manager = VoiceManager(db)

        voice_reference, _ = await TTSService._load_voice_ref_and_transcript(
            voice_manager, db, voice_id
        )

        gen_params = TTSService._gen_params(
            text, voice_id, voice_reference, use_turbo,
            temperature, top_p, top_k, repetition_penalty,
        )

        chunks = []
        async for chunk, sr in get_synthesis_queue().submit(gen_params):
            chunks.append(chunk)

        full_audio = np.concatenate(chunks)
        sample_rate = get_tts_engine().sample_rate

        return TTSService._save_test_samples(chunks, sample_rate, output_path, full_audio)

    @staticmethod
    def _gen_params(
        text: str,
        voice_id: str,
        voice_reference: np.ndarray,
        use_turbo: bool,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        repetition_penalty: float | None = None,
    ) -> dict:
        params: dict = {
            "text": text,
            "voice_id": voice_id,
            "voice_reference": voice_reference,
            "use_turbo": use_turbo,
        }
        optional = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repetition_penalty": repetition_penalty,
        }
        params.update({k: v for k, v in optional.items() if v is not None})
        return params

    @staticmethod
    def _save_test_samples(
        chunks: list[np.ndarray],
        sample_rate: int,
        output_path: Path,
        full_audio: np.ndarray
    ) -> TestSamplesResult:
        files = {}
        for fmt in ["pcm", "wav", "vorbis"]:
            encoder = AudioStreamEncoder(fmt, sample_rate)

            for chunk in chunks:
                encoder.encode_chunk(chunk)

            encoded_data = encoder.finalize()
            if fmt == "pcm":
                encoded_data = encoder.encode_complete(full_audio)

            filename = f"test.{fmt if fmt != 'vorbis' else 'ogg'}"
            filepath = output_path / filename

            with open(filepath, 'wb') as f:
                f.write(encoded_data)

            files[fmt] = TestSamplesFile(path=str(filepath), size=len(encoded_data))

        return TestSamplesResult(
            sample_rate=sample_rate,
            duration=len(full_audio) / sample_rate,
            samples=len(full_audio),
            files=files
        )
