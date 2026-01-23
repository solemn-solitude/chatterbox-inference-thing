"""Base interface for TTS clients."""

from abc import ABC, abstractmethod
from typing import Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import VoiceListResponse, HealthResponse, VoiceConfig


class TTSClient(ABC):
    """Abstract base class for TTS clients."""
    
    def __init__(self, server_url: str, api_key: str):
        """Initialize TTS client.
        
        Args:
            server_url: Server URL
            api_key: API key for authentication
        """
        self.server_url = server_url
        self.api_key = api_key
    
    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_mode: str = "default",
        voice_config: Optional['VoiceConfig'] = None,
        audio_format: str = "pcm",
        sample_rate: Optional[int] = None,
        use_turbo: bool = False,
    ) -> Iterator[bytes]:
        """Synthesize speech from text with streaming.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_config: Voice configuration object (contains voice_name, voice_id, speed, exaggeration, cfg_weight, etc.)
            audio_format: "pcm" or "vorbis"
            sample_rate: Output sample rate
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            
        Yields:
            Audio data chunks
        """
        pass
    
    @abstractmethod
    def list_voices(self) -> 'VoiceListResponse':
        """List available voices.
        
        Returns:
            VoiceListResponse with voices information
        """
        pass
    
    @abstractmethod
    def health_check(self) -> 'HealthResponse':
        """Check server health.
        
        Returns:
            HealthResponse with health status
        """
        pass
    
    @abstractmethod
    def close(self):
        """Close client connection."""
        pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
