"""Abstract base class for TTS engines."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Tuple, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class BaseTTSEngine(ABC):
    """Abstract base class for TTS engines.
    
    This defines the interface that all TTS implementations must follow,
    allowing them to be used interchangeably throughout the application.
    """
    
    @abstractmethod
    async def initialize(self):
        """Load and initialize the TTS model.
        
        This method should load the model into memory and prepare it for
        generation. It may be called multiple times (e.g., after offloading).
        """
        pass
    
    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Get the model's default sample rate.
        
        Returns:
            Sample rate in Hz
        """
        pass
    
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if model is loaded in memory.
        
        Returns:
            True if model is loaded, False otherwise
        """
        pass
    
    @abstractmethod
    async def offload_model(self):
        """Release model from memory to free resources.
        
        This should clear model references and free GPU memory if applicable.
        The model can be reloaded by calling initialize() again.
        """
        pass
    
    @abstractmethod
    async def synthesize_streaming(
        self,
        text: str,
        voice_mode: str,
        voice_reference: Optional[np.ndarray] = None,
        voice_name: Optional[str] = None,
        speed: float = 1.0,
        sample_rate: Optional[int] = None,
        **model_params
    ) -> AsyncIterator[Tuple[np.ndarray, int]]:
        """Generate speech with streaming support.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_reference: Reference audio for voice cloning (numpy array)
            voice_name: Name of voice/speaker to use
            speed: Speech speed multiplier
            sample_rate: Output sample rate (defaults to model.sr)
            **model_params: Model-specific generation parameters
            
        Yields:
            Tuple of (audio_chunk, sample_rate)
        """
        pass
    
    async def synthesize(
        self,
        text: str,
        voice_mode: str = "default",
        voice_reference: Optional[np.ndarray] = None,
        voice_name: Optional[str] = None,
        speed: float = 1.0,
        sample_rate: Optional[int] = None,
        **model_params
    ) -> Tuple[np.ndarray, int]:
        """Generate complete speech audio (non-streaming).
        
        This is a convenience method that collects all chunks from
        synthesize_streaming and returns them as a single array.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_reference: Reference audio for voice cloning
            voice_name: Name of voice/speaker to use
            speed: Speech speed multiplier
            sample_rate: Output sample rate
            **model_params: Model-specific generation parameters
            
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
            **model_params
        ):
            chunks.append(chunk)
            output_sr = sr
        
        if chunks:
            full_audio = np.concatenate(chunks)
            return full_audio, output_sr
        else:
            return np.array([]), output_sr