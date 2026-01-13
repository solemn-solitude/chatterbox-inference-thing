"""Voice management service - shared business logic."""

import logging
from typing import Optional, List, Dict, Any
import numpy as np

from ..tts import VoiceManager
from ..models import VoiceDatabase, VoiceInfo

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for voice management operations."""
    
    def __init__(self, voice_manager: VoiceManager, db: VoiceDatabase):
        """Initialize voice service.
        
        Args:
            voice_manager: Voice manager instance
            db: Database instance
        """
        self.voice_manager = voice_manager
        self.db = db
    
    async def load_voice_reference(self, voice_id: str) -> Optional[np.ndarray]:
        """Load voice reference by ID.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            Voice reference audio or None if not found
        """
        return await self.voice_manager.load_voice_reference(voice_id)
    
    async def voice_exists(self, voice_id: str) -> bool:
        """Check if voice exists.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if voice exists
        """
        return await self.db.voice_exists(voice_id)
    
    async def upload_voice(
        self,
        voice_id: str,
        audio_file,
        sample_rate: int
    ) -> bool:
        """Upload a new voice.
        
        Args:
            voice_id: Unique voice identifier
            audio_file: Audio file object
            sample_rate: Sample rate of audio
            
        Returns:
            True if successful
        """
        return await self.voice_manager.upload_voice(
            voice_id=voice_id,
            audio_file=audio_file,
            sample_rate=sample_rate
        )
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """List all voices.
        
        Returns:
            List of voice info dictionaries
        """
        return await self.db.list_voices()
    
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a voice.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if deleted, False if not found
        """
        return await self.voice_manager.delete_voice(voice_id)
