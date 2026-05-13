"""Voice management service - shared business logic."""

import logging
import numpy as np

from ..tts import VoiceManager
from ..models import VoiceDatabase
from ..models.service_dataclasses import VoiceRecord

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for voice management operations."""

    def __init__(self, voice_manager: VoiceManager, db: VoiceDatabase):
        self.voice_manager = voice_manager
        self.db = db

    async def load_voice_reference(self, voice_id: str) -> np.ndarray | None:
        return await self.voice_manager.load_voice_reference(voice_id)

    async def get_voice_transcript(self, voice_id: str) -> str | None:
        record = await self.db.get_voice(voice_id)
        return record.voice_transcript if record else None

    async def voice_exists(self, voice_id: str) -> bool:
        return await self.db.voice_exists(voice_id)

    async def upload_voice(
        self,
        voice_id: str,
        audio_file,
        sample_rate: int,
        voice_transcript: str
    ) -> bool:
        return await self.voice_manager.upload_voice(
            voice_id=voice_id,
            audio_file=audio_file,
            sample_rate=sample_rate,
            voice_transcript=voice_transcript
        )

    async def list_voices(self) -> list[VoiceRecord]:
        return await self.db.list_voices()

    async def delete_voice(self, voice_id: str) -> bool:
        return await self.voice_manager.delete_voice(voice_id)

    async def rename_voice(self, old_voice_id: str, new_voice_id: str) -> bool:
        return await self.voice_manager.rename_voice(old_voice_id, new_voice_id)
