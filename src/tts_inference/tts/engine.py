"""TTS Engine factory and management."""

import logging
from typing import Optional

from .base_tts import BaseTTSEngine
from ..utils.config import CONFIG

# Conditional imports based on what's installed
try:
    from .chatterbox_tts import ChatterboxTTSEngine
    CHATTERBOX_AVAILABLE = True
except ImportError:
    CHATTERBOX_AVAILABLE = False
    ChatterboxTTSEngine = None

try:
    from .qwen_tts import QwenTTSEngine
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False
    QwenTTSEngine = None

logger = logging.getLogger(__name__)


def create_tts_engine(
    model_type: str | None = None,
    **config
) -> BaseTTSEngine:
    """Factory function to create TTS engine based on model type.
    
    Args:
        model_type: Type of TTS model ("chatterbox" or "qwen").
                  If None, uses CHATTERBOX_TTS_MODEL env var or config default.
        **config: Additional configuration passed to engine constructor
        
    Returns:
        Instantiated TTS engine
        
    Raises:
        ValueError: If model_type is unknown
        ImportError: If required model dependencies are not installed
    """
    model_type = model_type or CONFIG.tts_model
    
    logger.info(f"Creating TTS engine: {model_type}")
    
    if model_type == "chatterbox":
        if not CHATTERBOX_AVAILABLE:
            raise ImportError(
                "chatterbox-tts is not installed. "
                "Install with: uv sync --extra chatterbox"
            )
        return ChatterboxTTSEngine(
            inactivity_timeout=config.get("inactivity_timeout", CONFIG.offload_timeout),
            keep_warm=config.get("keep_warm", CONFIG.keep_warm)
        )
    elif model_type == "qwen":
        if not QWEN_AVAILABLE:
            raise ImportError(
                "qwen-tts is not installed. "
                "Install with: uv sync --extra qwen"
            )
        return QwenTTSEngine(
            inactivity_timeout=config.get("inactivity_timeout", CONFIG.offload_timeout),
            keep_warm=config.get("keep_warm", CONFIG.keep_warm),
            cache_ttl_minutes=config.get("cache_ttl_minutes", 60)
        )
    else:
        raise ValueError(
            f"Unknown TTS model type: {model_type}. "
            "Supported types: 'chatterbox', 'qwen'"
        )


# Global TTS engine instance (will be initialized with config settings on startup)
tts_engine: Optional[BaseTTSEngine] = None


def get_tts_engine() -> BaseTTSEngine:
    """Get or create the global TTS engine instance.
    
    The engine type is determined by CHATTERBOX_TTS_MODEL environment
    variable or config setting. This ensures all parts of the application
    use the same TTS model.
    
    Returns:
        Global TTS engine instance
    """
    global tts_engine
    if tts_engine is None:
        tts_engine = create_tts_engine(
            model_type=CONFIG.tts_model,
            inactivity_timeout=CONFIG.offload_timeout,
            keep_warm=CONFIG.keep_warm
        )
    return tts_engine


def reset_tts_engine():
    """Reset the global TTS engine instance.
    
    This can be used to force re-creation of the engine with different
    configuration or model type.
    """
    global tts_engine
    tts_engine = None
    logger.info("Global TTS engine reset")