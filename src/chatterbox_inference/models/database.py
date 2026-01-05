"""SQLite database management for voice metadata."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class VoiceDatabase:
    """Manages voice metadata in SQLite database."""
    
    def __init__(self, db_path: Path):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
    
    async def initialize(self):
        """Create database schema if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS voices (
                    voice_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    sample_rate INTEGER NOT NULL,
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
        duration_seconds: Optional[float] = None
    ) -> bool:
        """Add a new voice to the database.
        
        Args:
            voice_id: Unique identifier for the voice
            filename: Name of the audio file
            sample_rate: Sample rate of the audio
            duration_seconds: Duration of the audio in seconds
            
        Returns:
            True if added successfully, False if voice_id already exists
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO voices (voice_id, filename, sample_rate, duration_seconds, uploaded_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (voice_id, filename, sample_rate, duration_seconds, datetime.utcnow().isoformat())
                )
                await db.commit()
                logger.info(f"Added voice: {voice_id}")
                return True
        except aiosqlite.IntegrityError:
            logger.warning(f"Voice ID already exists: {voice_id}")
            return False
    
    async def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve voice metadata by ID.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            Dictionary with voice metadata or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM voices WHERE voice_id = ?",
                (voice_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """List all voices in the database.
        
        Returns:
            List of voice metadata dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM voices ORDER BY uploaded_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a voice from the database.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if deleted, False if not found
        """
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
        """Check if a voice ID exists in the database.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if exists, False otherwise
        """
        voice = await self.get_voice(voice_id)
        return voice is not None
