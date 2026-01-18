"""Model lifecycle service - shared business logic."""

import logging
from typing import Dict, Any

from ..tts import get_tts_engine
from ..utils.config import CONFIG

logger = logging.getLogger(__name__)


class ModelService:
    """Service for model lifecycle operations."""
    
    @staticmethod
    async def unload_model() -> Dict[str, Any]:
        """Unload model from memory.
        
        Returns:
            Dictionary with success status and info
        """
        tts_engine = get_tts_engine()
        
        if not tts_engine.is_loaded():
            return {
                "success": True,
                "message": "Model is already unloaded",
                "was_loaded": False
            }
        
        await tts_engine.offload_model()
        
        return {
            "success": True,
            "message": "Model unloaded successfully",
            "was_loaded": True
        }
    
    @staticmethod
    def get_model_status() -> Dict[str, Any]:
        """Get current model status.
        
        Returns:
            Dictionary with model status information
        """
        tts_engine = get_tts_engine()
        
        return {
            "model_loaded": tts_engine.is_loaded(),
            "voice_dir_accessible": CONFIG.voice_audio_dir.exists(),
            "database_accessible": CONFIG.database_path.exists(),
        }
