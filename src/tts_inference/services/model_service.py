"""Model lifecycle service - shared business logic."""

import logging

from ..tts import get_tts_engine
from ..utils.config import CONFIG
from ..models.service_dataclasses import ModelStatus, UnloadResult

logger = logging.getLogger(__name__)


class ModelService:
    """Service for model lifecycle operations."""
    
    @staticmethod
    async def unload_model() -> UnloadResult:
        """Unload model from memory."""
        tts_engine = get_tts_engine()
        
        if not tts_engine.is_loaded():
            return UnloadResult(
                success=True,
                message="Model is already unloaded",
                was_loaded=False
            )
        
        await tts_engine.offload_model()
        
        return UnloadResult(
            success=True,
            message="Model unloaded successfully",
            was_loaded=True
        )
    
    @staticmethod
    def get_model_status() -> ModelStatus:
        """Get current model status."""
        tts_engine = get_tts_engine()
        
        return ModelStatus(
            model_loaded=tts_engine.is_loaded(),
            voice_dir_accessible=CONFIG.voice_audio_dir.exists(),
            database_accessible=CONFIG.database_path.exists(),
        )
