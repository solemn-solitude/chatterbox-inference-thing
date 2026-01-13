"""FastAPI dependency injection."""

from typing import Optional

from ..services import VoiceService
from ..models import VoiceDatabase
from ..tts import VoiceManager

# Global instances (set during lifespan)
db: Optional[VoiceDatabase] = None
voice_manager: Optional[VoiceManager] = None
voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get voice service dependency.
    
    Returns:
        VoiceService instance
        
    Raises:
        RuntimeError: If service not initialized
    """
    if voice_service is None:
        raise RuntimeError("Voice service not initialized")
    return voice_service
