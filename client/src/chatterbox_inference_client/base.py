"""Base interface for TTS clients."""

from abc import ABC, abstractmethod
from typing import Iterator, Dict, Any, Optional
from pathlib import Path


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
        voice_name: Optional[str] = None,
        voice_id: Optional[str] = None,
        audio_format: str = "pcm",
        sample_rate: Optional[int] = None,
        speed: float = 1.0,
        use_turbo: bool = False,
    ) -> Iterator[bytes]:
        """Synthesize speech from text with streaming.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_name: Name of default voice (for default mode)
            voice_id: ID of cloned voice (for clone mode)
            audio_format: "pcm" or "vorbis"
            sample_rate: Output sample rate
            speed: Speech speed multiplier
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            
        Yields:
            Audio data chunks
        """
        pass
    
    @abstractmethod
    def list_voices(self) -> Dict[str, Any]:
        """List available voices.
        
        Returns:
            Dictionary with voices information
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check server health.
        
        Returns:
            Health status dictionary
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
