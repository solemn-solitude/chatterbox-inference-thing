"""TTS synthesis service - shared business logic."""

import logging
from typing import AsyncIterator, Tuple, Optional
import numpy as np

from ..tts import get_tts_engine
from ..models import TTSRequest
from ..utils.audio_utils import AudioStreamEncoder

logger = logging.getLogger(__name__)


class TTSService:
    """Service for TTS synthesis operations."""
    
    @staticmethod
    async def synthesize_streaming(
        request: TTSRequest,
        voice_reference: Optional[np.ndarray] = None
    ) -> AsyncIterator[Tuple[np.ndarray, int]]:
        """Synthesize speech with streaming.
        
        Args:
            request: TTS request with all parameters
            voice_reference: Optional voice reference audio for cloning
            
        Yields:
            Tuple of (audio_chunk, sample_rate)
        """
        tts_engine = get_tts_engine()
        
        async for audio_chunk, sample_rate in tts_engine.synthesize_streaming(
            text=request.text,
            voice_mode=request.voice_mode,
            voice_reference=voice_reference,
            voice_name=request.voice_config.voice_name,
            speed=request.voice_config.speed,
            sample_rate=request.sample_rate,
            use_turbo=request.use_turbo,
            exaggeration=request.voice_config.exaggeration,
            cfg_weight=request.voice_config.cfg_weight,
            temperature=request.voice_config.temperature,
            repetition_penalty=request.voice_config.repetition_penalty,
        ):
            yield audio_chunk, sample_rate
    
    @staticmethod
    async def encode_audio_stream(
        request: TTSRequest,
        voice_reference: Optional[np.ndarray] = None
    ) -> AsyncIterator[bytes]:
        """Encode audio stream in requested format.
        
        Args:
            request: TTS request with format specification
            voice_reference: Optional voice reference for cloning
            
        Yields:
            Encoded audio bytes
        """
        tts_engine = get_tts_engine()
        output_sr = request.sample_rate or tts_engine.sample_rate
        encoder = AudioStreamEncoder(request.audio_format, output_sr)
        
        if request.audio_format == "pcm":
            # PCM can be truly streamed chunk by chunk
            async for audio_chunk, sample_rate in TTSService.synthesize_streaming(
                request, voice_reference
            ):
                encoded_chunk = encoder.encode_chunk(audio_chunk)
                yield encoded_chunk
        else:
            # WAV and Vorbis need complete audio - accumulate chunks
            async for audio_chunk, sample_rate in TTSService.synthesize_streaming(
                request, voice_reference
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
        output_dir: str,
        use_turbo: bool = False
    ) -> dict:
        """Generate test audio samples in all formats.
        
        Args:
            text: Text to synthesize
            output_dir: Directory to save files
            use_turbo: Whether to use turbo model
            
        Returns:
            Dictionary with results
        """
        from pathlib import Path
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        tts_engine = get_tts_engine()
        await tts_engine.initialize()
        
        # Generate audio
        chunks = []
        async for chunk, sr in tts_engine.synthesize_streaming(text=text, use_turbo=use_turbo):
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
