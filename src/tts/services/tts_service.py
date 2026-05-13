"""TTS synthesis service - shared business logic."""

from pathlib import Path
import logging
import numpy as np

from tts.tts import get_tts_engine
from tts.tts.voice_manager import VoiceManager
from tts.models import TTSRequest
from tts.models.schemas import ChatterboxVoiceConfig, OmniVoiceVoiceConfig, FishSpeechVoiceConfig
from tts.models.database import VoiceDatabase
from tts.utils.audio_utils import AudioStreamEncoder
from tts.utils.config import CONFIG
from tts.models.service_dataclasses import TestSamplesResult, TestSamplesFile
from tts.services.synthesis_queue import get_synthesis_queue

logger = logging.getLogger(__name__)


class TTSService:

    @staticmethod
    def _chatterbox_params(request: TTSRequest, voice_reference: np.ndarray) -> dict:
        cfg = request.voice_config
        assert isinstance(cfg, ChatterboxVoiceConfig)
        return {
            "text": request.text,
            "voice_id": cfg.voice_id,
            "voice_reference": voice_reference,
            "speed": cfg.speed,
            "sample_rate": request.sample_rate,
            "use_turbo": cfg.use_turbo,
            "exaggeration": cfg.exaggeration,
            "cfg_weight": cfg.cfg_weight,
            "temperature": cfg.temperature,
            "repetition_penalty": cfg.repetition_penalty,
        }

    @staticmethod
    def _omnivoice_params(
        request: TTSRequest,
        voice_reference: np.ndarray | None,
        voice_transcript: str | None = None,
    ) -> dict:
        cfg = request.voice_config
        assert isinstance(cfg, OmniVoiceVoiceConfig)
        return {
            "text": request.text,
            "voice_id": cfg.voice_id,
            "voice_reference": voice_reference,
            "voice_transcript": voice_transcript,
            "voice_description": cfg.voice_description,
            "speed": cfg.speed,
            "sample_rate": request.sample_rate,
            "language": cfg.language,
            "num_step": cfg.num_step,
            "guidance_scale": cfg.guidance_scale,
        }

    @staticmethod
    def _fish_speech_params(
        request: TTSRequest,
        voice_reference: np.ndarray | None,
        voice_transcript: str | None = None,
    ) -> dict:
        cfg = request.voice_config
        assert isinstance(cfg, FishSpeechVoiceConfig)
        return {
            "text": request.text,
            "voice_id": cfg.voice_id,
            "voice_reference": voice_reference,
            "voice_transcript": voice_transcript,
            "speed": cfg.speed,
            "sample_rate": request.sample_rate,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "repetition_penalty": cfg.repetition_penalty,
            "chunk_length": cfg.chunk_length,
            "seed": cfg.seed,
            "normalize": cfg.normalize,
        }

    @staticmethod
    def _build_params(
        request: TTSRequest,
        voice_reference: np.ndarray | None,
        voice_transcript: str | None = None,
    ) -> dict:
        match request.voice_config:
            case OmniVoiceVoiceConfig():
                return TTSService._omnivoice_params(request, voice_reference, voice_transcript)
            case FishSpeechVoiceConfig():
                return TTSService._fish_speech_params(request, voice_reference, voice_transcript)
            case ChatterboxVoiceConfig():
                return TTSService._chatterbox_params(request, voice_reference)
            case _:
                raise ValueError(f"Unknown voice config type: {type(request.voice_config)}")

    @staticmethod
    async def synthesize_streaming(
        request: TTSRequest,
        voice_reference: np.ndarray | None,
        voice_transcript: str | None = None,
    ):
        params = TTSService._build_params(request, voice_reference, voice_transcript)
        async for chunk, sr in get_synthesis_queue().submit(params):
            yield chunk, sr

    @staticmethod
    async def encode_audio_stream(
        request: TTSRequest,
        voice_reference: np.ndarray | None,
        voice_transcript: str | None = None,
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
        list_available: bool = False,
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
    ) -> TestSamplesResult:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if db is None:
            db = VoiceDatabase(CONFIG.database_path)
            await db.initialize()
        if voice_manager is None:
            voice_manager = VoiceManager(db)

        voice_reference, voice_transcript = await TTSService._load_voice_ref_and_transcript(
            voice_manager, db, voice_id
        )

        params = {
            "text": text,
            "voice_id": voice_id,
            "voice_reference": voice_reference,
            "voice_transcript": voice_transcript,
        }

        chunks = []
        async for chunk, sr in get_synthesis_queue().submit(params):
            chunks.append(chunk)

        full_audio = np.concatenate(chunks)
        sample_rate = get_tts_engine().sample_rate

        return TTSService._save_test_samples(chunks, sample_rate, output_path, full_audio)

    @staticmethod
    def _save_test_samples(
        chunks: list[np.ndarray],
        sample_rate: int,
        output_path: Path,
        full_audio: np.ndarray,
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

            with open(filepath, "wb") as f:
                f.write(encoded_data)

            files[fmt] = TestSamplesFile(path=str(filepath), size=len(encoded_data))

        return TestSamplesResult(
            sample_rate=sample_rate,
            duration=len(full_audio) / sample_rate,
            samples=len(full_audio),
            files=files,
        )
