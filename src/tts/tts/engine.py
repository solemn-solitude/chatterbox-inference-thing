"""TTS Engine singleton."""

import logging
from tts.tts.base_tts import BaseTTSEngine
from tts.utils.config import CONFIG

try:
    from tts.tts.chatterbox_tts import ChatterboxTTSEngine
    CHATTERBOX_AVAILABLE = True
except ImportError:
    CHATTERBOX_AVAILABLE = False
    ChatterboxTTSEngine = None

try:
    from tts.tts.omnivoice_tts import OmniVoiceTTSEngine
    OMNIVOICE_AVAILABLE = True
except ImportError:
    OMNIVOICE_AVAILABLE = False
    OmniVoiceTTSEngine = None

try:
    from tts.tts.fish_speech_tts import FishSpeechTTSEngine
    FISH_SPEECH_AVAILABLE = True
except ImportError:
    FISH_SPEECH_AVAILABLE = False
    FishSpeechTTSEngine = None

logger = logging.getLogger(__name__)


def _build_engine() -> BaseTTSEngine:
    if CONFIG.tts_engine == "omnivoice":
        if not OMNIVOICE_AVAILABLE:
            raise ImportError(
                "omnivoice is not installed. "
                "Install with: uv sync --extra omnivoice"
            )
        return OmniVoiceTTSEngine(
            inactivity_timeout=CONFIG.offload_timeout,
            keep_warm=CONFIG.keep_warm,
        )

    if CONFIG.tts_engine == "fish-speech":
        if not FISH_SPEECH_AVAILABLE:
            raise ImportError(
                "fish-speech is not installed. "
                "Install with: uv sync --extra fish-speech"
            )
        return FishSpeechTTSEngine(
            inactivity_timeout=CONFIG.offload_timeout,
            keep_warm=CONFIG.keep_warm,
        )

    if not CHATTERBOX_AVAILABLE:
        raise ImportError(
            "chatterbox-tts is not installed. "
            "Install with: uv sync --extra chatterbox"
        )
    return ChatterboxTTSEngine(
        inactivity_timeout=CONFIG.offload_timeout,
        keep_warm=CONFIG.keep_warm,
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
