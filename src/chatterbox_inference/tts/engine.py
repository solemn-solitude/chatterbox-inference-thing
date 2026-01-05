"""TTS Engine wrapper for Chatterbox TTS."""

import torch
import numpy as np
from pathlib import Path
from typing import Optional, AsyncIterator, Tuple
import logging

logger = logging.getLogger(__name__)


class TTSEngine:
    """Wrapper for ChatterboxTTS engine with voice cloning and turbo support."""
    
    def __init__(self):
        """Initialize TTS engine."""
        self.model_regular: Optional[object] = None
        self.model_turbo: Optional[object] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._default_sr: int = 24000  # ChatterboxTTS default sample rate
        
    async def initialize(self):
        """Initialize and load the TTS model (regular by default)."""
        logger.info("Loading ChatterboxTTS model on {}...".format(self.device))
        try:
            from chatterbox.tts import ChatterboxTTS
            self.model_regular = ChatterboxTTS.from_pretrained(device=self.device)
            
            # Get sample rate from model
            self._default_sr = getattr(self.model_regular, 'sr', 24000)
            
            logger.info("ChatterboxTTS model loaded successfully. Sample rate: {}".format(self._default_sr))
        except Exception as e:
            logger.error("Failed to load ChatterboxTTS model: {}".format(e))
            raise
    
    async def _ensure_turbo_loaded(self):
        """Load turbo model if not already loaded."""
        if self.model_turbo is None:
            logger.info("Loading ChatterboxTurboTTS model on {}...".format(self.device))
            try:
                from chatterbox.tts_turbo import ChatterboxTurboTTS
                self.model_turbo = ChatterboxTurboTTS.from_pretrained(device=self.device)
                logger.info("ChatterboxTurboTTS model loaded successfully")
            except Exception as e:
                logger.error("Failed to load ChatterboxTurboTTS model: {}".format(e))
                raise
    
    @property
    def sample_rate(self) -> int:
        """Get the model's default sample rate."""
        return self._default_sr
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model_regular is not None
    
    async def synthesize_streaming(
        self,
        text: str,
        voice_mode: str = "default",
        voice_reference: Optional[np.ndarray] = None,
        voice_name: Optional[str] = None,
        speed: float = 1.0,
        sample_rate: Optional[int] = None,
        use_turbo: bool = False,
    ) -> AsyncIterator[Tuple[np.ndarray, int]]:
        """Generate speech audio with streaming support.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_reference: Reference audio for voice cloning (numpy array)
            voice_name: Name of default voice to use
            speed: Speech speed multiplier
            sample_rate: Output sample rate (defaults to model.sr)
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            
        Yields:
            Tuple of (audio_chunk, sample_rate)
        """
        if not self.is_loaded():
            raise RuntimeError("TTS model not loaded")
        
        # Select model based on turbo flag
        if use_turbo:
            await self._ensure_turbo_loaded()
            model = self.model_turbo
            model_name = "ChatterboxTurboTTS"
        else:
            model = self.model_regular
            model_name = "ChatterboxTTS"
        
        try:
            output_sr = sample_rate or self.sample_rate
            
            # Prepare audio prompt path if voice cloning is requested
            audio_prompt_path = None
            if voice_mode == "clone" and voice_reference is not None:
                logger.info("Voice cloning mode requested but not yet implemented")
                # TODO: Save voice_reference to a temporary file and use as audio_prompt_path
                # For now, we'll use default voice
            
            logger.info("Generating speech with {} for text: {}...".format(model_name, text[:50]))
            
            # ChatterboxTTS.generate returns a single wav tensor/array
            # The signature is: generate(text, audio_prompt_path=None)
            if audio_prompt_path:
                wav = model.generate(text, audio_prompt_path=audio_prompt_path)
            else:
                wav = model.generate(text)
            
            # Convert to numpy array if needed
            if isinstance(wav, torch.Tensor):
                audio_array = wav.cpu().numpy()
            else:
                audio_array = np.array(wav)
            
            # Ensure correct shape (flatten if needed)
            if len(audio_array.shape) > 1:
                audio_array = audio_array.flatten()
            
            # Convert to float32 if needed
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)
            
            # Chunk the audio for streaming (e.g., 1 second chunks)
            chunk_size = output_sr  # 1 second chunks
            for i in range(0, len(audio_array), chunk_size):
                chunk = audio_array[i:i + chunk_size]
                yield chunk, output_sr
                    
        except Exception as e:
            logger.error("Error during TTS synthesis with {}: {}".format(model_name, e))
            raise
    
    async def synthesize(
        self,
        text: str,
        voice_mode: str = "default",
        voice_reference: Optional[np.ndarray] = None,
        voice_name: Optional[str] = None,
        speed: float = 1.0,
        sample_rate: Optional[int] = None,
        use_turbo: bool = False,
    ) -> Tuple[np.ndarray, int]:
        """Generate complete speech audio (non-streaming).
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_reference: Reference audio for voice cloning
            voice_name: Name of default voice to use
            speed: Speech speed multiplier
            sample_rate: Output sample rate
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        chunks = []
        output_sr = sample_rate or self.sample_rate
        
        async for chunk, sr in self.synthesize_streaming(
            text=text,
            voice_mode=voice_mode,
            voice_reference=voice_reference,
            voice_name=voice_name,
            speed=speed,
            sample_rate=sample_rate,
            use_turbo=use_turbo,
        ):
            chunks.append(chunk)
            output_sr = sr
        
        if chunks:
            full_audio = np.concatenate(chunks)
            return full_audio, output_sr
        else:
            return np.array([]), output_sr


# Global TTS engine instance
tts_engine = TTSEngine()
