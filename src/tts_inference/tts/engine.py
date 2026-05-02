"""TTS Engine singleton."""

import logging
from .base_tts import BaseTTSEngine
from ..utils.config import CONFIG

try:
    from .chatterbox_tts import ChatterboxTTSEngine
    CHATTERBOX_AVAILABLE = True
except ImportError:
    CHATTERBOX_AVAILABLE = False
    ChatterboxTTSEngine = None

logger = logging.getLogger(__name__)


def _build_engine() -> BaseTTSEngine:
    if not CHATTERBOX_AVAILABLE:
        raise ImportError(
            "chatterbox-tts is not installed. "
            "Install with: uv sync --extra chatterbox"
        )
    return ChatterboxTTSEngine(
        inactivity_timeout=CONFIG.offload_timeout,
        keep_warm=CONFIG.keep_warm
    )


class _EngineHolder:
    _engine: BaseTTSEngine | None = None

    @classmethod
    def get(cls) -> BaseTTSEngine:
        if cls._engine is None:
            cls._engine = _build_engine()
        return cls._engine

    @classmethod
    def reset(cls):
        cls._engine = None
        logger.info("TTS engine reset")


def get_tts_engine() -> BaseTTSEngine:
    return _EngineHolder.get()


def reset_tts_engine():
    _EngineHolder.reset()
