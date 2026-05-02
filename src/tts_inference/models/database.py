"""SQLite database management for voice metadata."""

import aiosqlite
from datetime import datetime
from pathlib import Path
import logging

from .service_dataclasses import VoiceRecord

logger = logging.getLogger(__name__)


class VoiceDatabase:
    """Manages voice metadata in SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS voices (
                    voice_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    sample_rate INTEGER NOT NULL,
                    voice_transcript TEXT,
                    duration_seconds REAL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info(f"Database initialized at {self.db_path}")

    async def add_voice(
        self,
        voice_id: str,
        filename: str,
        sample_rate: int,
        voice_transcript: str | None = None,
        duration_seconds: float | None = None
    ) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO voices (voice_id, filename, sample_rate, voice_transcript, duration_seconds, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (voice_id, filename, sample_rate, voice_transcript, duration_seconds, datetime.utcnow().isoformat())
                )
                await db.commit()
                logger.info(f"Added voice: {voice_id}")
                return True
        except aiosqlite.IntegrityError:
            logger.warning(f"Voice ID already exists: {voice_id}")
            return False

    async def get_voice(self, voice_id: str) -> VoiceRecord | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM voices WHERE voice_id = ?",
                (voice_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return VoiceRecord(**dict(row))
                return None

    async def list_voices(self) -> list[VoiceRecord]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM voices ORDER BY uploaded_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [VoiceRecord(**dict(row)) for row in rows]

    async def delete_voice(self, voice_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM voices WHERE voice_id = ?",
                (voice_id,)
            )
            await db.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted voice: {voice_id}")
            return deleted

    async def voice_exists(self, voice_id: str) -> bool:
        return await self.get_voice(voice_id) is not None

    async def rename_voice(self, old_voice_id: str, new_voice_id: str) -> bool:
        if not await self.voice_exists(old_voice_id):
            logger.warning(f"Cannot rename: voice '{old_voice_id}' not found")
            return False

        if await self.voice_exists(new_voice_id):
            logger.warning(f"Cannot rename: voice '{new_voice_id}' already exists")
            return False

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE voices SET voice_id = ? WHERE voice_id = ?",
                    (new_voice_id, old_voice_id)
                )
                await db.commit()
                logger.info(f"Renamed voice: {old_voice_id} -> {new_voice_id}")
                return True
        except Exception as e:
            logger.error(f"Error renaming voice in database: {e}")
            return False
