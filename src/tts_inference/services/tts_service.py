"""TTS synthesis service - shared business logic."""

from pathlib import Path
import logging
from typing import AsyncIterator
import numpy as np

from ..tts import create_tts_engine, get_tts_engine
from ..tts.voice_manager import VoiceManager
from ..models import TTSRequest, ChatterboxVoiceConfig, QwenVoiceConfig
from ..models.database import VoiceDatabase
from ..utils.audio_utils import AudioStreamEncoder
from ..utils.config import CONFIG

logger = logging.getLogger(__name__)


class TTSService:
    """Service for TTS synthesis operations."""
    
    @staticmethod
    async def synthesize_streaming(
        request: TTSRequest,
        voice_reference: np.ndarray,
        voice_transcript: str | None = None
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        """Synthesize speech with streaming.
        
        Args:
            request: TTS request with all parameters
            voice_reference: Voice reference audio for cloning (from DB)
            voice_transcript: Transcript of the reference audio (used as ref_text for Qwen)
            
        Yields:
            Tuple of (audio_chunk, sample_rate)
        """
        # Determine model type
        model_type = request.model_type or "chatterbox"
        
        # Create appropriate engine
        engine = create_tts_engine(
            model_type=model_type,
            inactivity_timeout=None,  # Use config defaults
            keep_warm=None
        )
        
        # Extract parameters based on config type
        if isinstance(request.voice_config, ChatterboxVoiceConfig):
            # Chatterbox-specific parameters
            params = {
                "text": request.text,
                "voice_id": request.voice_config.voice_id,
                "voice_reference": voice_reference,
                "speed": request.voice_config.speed,
                "sample_rate": request.sample_rate,
                "use_turbo": request.use_turbo,
                "exaggeration": request.voice_config.exaggeration,
                "cfg_weight": request.voice_config.cfg_weight,
                "temperature": request.voice_config.temperature,
                "repetition_penalty": request.voice_config.repetition_penalty
            }
        elif isinstance(request.voice_config, QwenVoiceConfig):
            # Use transcript as ref_text if ref_text not provided
            ref_text = request.voice_config.ref_text or voice_transcript
            
            # Qwen-specific parameters
            params = {
                "text": request.text,
                "voice_id": request.voice_config.voice_id,
                "voice_reference": voice_reference,
                "speed": request.voice_config.speed,
                "sample_rate": request.sample_rate,
                "language": request.voice_config.language,
                "ref_text": ref_text,
                "max_new_tokens": request.voice_config.max_new_tokens,
                "top_p": request.voice_config.top_p,
                "top_k": request.voice_config.top_k,
                "temperature": request.voice_config.temperature,
                "repetition_penalty": request.voice_config.repetition_penalty
            }
        else:
            raise ValueError(f"Unknown voice config type: {type(request.voice_config)}")
        
        # Stream generation
        async for audio_chunk, sample_rate in engine.synthesize_streaming(**params):
            yield audio_chunk, sample_rate
    
    @staticmethod
    async def encode_audio_stream(
        request: TTSRequest,
        voice_reference: np.ndarray,
        voice_transcript: str | None = None
    ) -> AsyncIterator[bytes]:
        """Encode audio stream in requested format.
        
        Args:
            request: TTS request with format specification
            voice_reference: Voice reference for cloning
            voice_transcript: Transcript of the reference audio
            
        Yields:
            Encoded audio bytes
        """
        tts_engine = get_tts_engine()
        output_sr = request.sample_rate or tts_engine.sample_rate
        encoder = AudioStreamEncoder(request.audio_format, output_sr)
        
        if request.audio_format == "pcm":
            # PCM can be truly streamed chunk by chunk
            async for audio_chunk, sample_rate in TTSService.synthesize_streaming(
                request, voice_reference, voice_transcript
            ):
                encoded_chunk = encoder.encode_chunk(audio_chunk)
                yield encoded_chunk
        else:
            # WAV and Vorbis need complete audio - accumulate chunks
            async for audio_chunk, sample_rate in TTSService.synthesize_streaming(
                request, voice_reference, voice_transcript
            ):
                encoder.encode_chunk(audio_chunk)
            
            # Finalize encoding
            encoded_data = encoder.finalize()
            if encoded_data:
                yield encoded_data
    
    @staticmethod
    def get_media_type(audio_format: str) -> str:
        """Get media type for audio format.
        
        Args:
            audio_format: Audio format (pcm, wav, vorbis)
            
        Returns:
            Media type string
        """
        if audio_format == "pcm":
            return "audio/pcm"
        elif audio_format == "wav":
            return "audio/wav"
        elif audio_format == "vorbis":
            return "audio/ogg"
        else:
            return "application/octet-stream"
    
    @staticmethod
    async def generate_test_samples(
        text: str,
        voice_id: str,
        output_dir: str,
        use_turbo: bool = False,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        repetition_penalty: float | None = None
    ) -> dict:
        """Generate test audio samples in all formats.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use for cloning
            output_dir: Directory to save files
            use_turbo: Whether to use turbo model
            temperature: Sampling temperature (override default)
            top_p: Top-p sampling (override default)
            top_k: Top-k sampling (override default)
            repetition_penalty: Repetition penalty (override default)
            
        Returns:
            Dictionary with results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Load voice from database
        db = VoiceDatabase(CONFIG.database_path)
        await db.initialize()
        voice_manager = VoiceManager(db)
        
        voice_reference = await voice_manager.load_voice_reference(voice_id)
        if voice_reference is None:
            raise ValueError(f"Voice not found: {voice_id}")
        
        # Get voice info for transcript (used as ref_text for Qwen)
        voice_info = await db.get_voice(voice_id)
        voice_transcript = voice_info.get("voice_transcript") if voice_info else None
        
        tts_engine = get_tts_engine()
        await tts_engine.initialize()
        
        # Build generation parameters with overrides
        gen_params = {
            "text": text,
            "voice_id": voice_id,
            "voice_reference": voice_reference,
            "ref_text": voice_transcript,  # Use transcript as ref_text
            "use_turbo": use_turbo
        }
        
        # Add optional parameters if provided
        if temperature is not None:
            gen_params["temperature"] = temperature
        if top_p is not None:
            gen_params["top_p"] = top_p
        if top_k is not None:
            gen_params["top_k"] = top_k
        if repetition_penalty is not None:
            gen_params["repetition_penalty"] = repetition_penalty
        
        # Generate audio
        chunks = []
        async for chunk, sr in tts_engine.synthesize_streaming(**gen_params):
            chunks.append(chunk)
        
        full_audio = np.concatenate(chunks)
        sample_rate = tts_engine.sample_rate
        
        # Save in all formats
        results = {
            'sample_rate': sample_rate,
            'duration':  len(full_audio) / sample_rate,
            'samples': len(full_audio),
            'files': {}
        }
        
        formats = ["pcm", "wav", "vorbis"]
        for fmt in formats:
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
            
            results['files'][fmt] = {
                'path': str(filepath),
                'size': len(encoded_data)
            }
        
        return results
