"""Shared server initialization components and utilities."""
import logging
import numpy as np

from ..models import VoiceDatabase, TTSRequest
from ..tts import get_tts_engine, VoiceManager
from ..services import VoiceService
from ..utils.config import CONFIG

logger = logging.getLogger(__name__)


async def initialize_server_components() -> tuple[VoiceDatabase, VoiceManager, VoiceService]:
    """Initialize shared server components: db, voice_manager, voice_service, tts_engine."""
    logger.info("Initializing shared server components...")

    try:
        CONFIG.validate_api_key()
    except ValueError as e:
        logger.error(str(e))
        raise

    CONFIG.ensure_directories()

    db = VoiceDatabase(CONFIG.database_path)
    await db.initialize()

    voice_manager = VoiceManager(db)
    voice_service = VoiceService(voice_manager, db)

    tts_engine = get_tts_engine()
    await tts_engine.initialize()

    logger.info("Shared server components initialized")

    return db, voice_manager, voice_service


async def load_voice_reference_or_raise(
    voice_service: VoiceService,
    voice_id: str,
    raise_on_not_found: bool = True
) -> np.ndarray | None:
    voice_reference = await voice_service.load_voice_reference(voice_id)
    if voice_reference is None and raise_on_not_found:
        raise ValueError(f"Voice not found: {voice_id}")
    return voice_reference


def get_output_sample_rate(request: TTSRequest) -> int:
    tts_engine = get_tts_engine()
    return request.sample_rate or tts_engine.sample_rate


def get_model_info() -> dict:
    tts_engine = get_tts_engine()
    return {
        "model": "chatterbox",
        "sample_rate": tts_engine.sample_rate if tts_engine.is_loaded() else None
    }
