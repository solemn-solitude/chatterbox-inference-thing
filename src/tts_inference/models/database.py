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
    
    async def rename_voice(self, old_voice_id: str, new_voice_id: str) -> bool:
        """Rename a voice in the database.
        
        Args:
            old_voice_id: Current voice identifier
            new_voice_id: New voice identifier
            
        Returns:
            True if renamed successfully, False if old_voice_id not found or new_voice_id already exists
        """
        # Check if old voice exists
        if not await self.voice_exists(old_voice_id):
            logger.warning(f"Cannot rename: voice '{old_voice_id}' not found")
            return False
        
        # Check if new voice ID already exists
        if await self.voice_exists(new_voice_id):
            logger.warning(f"Cannot rename: voice '{new_voice_id}' already exists")
            return False
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Update voice_id in voices table
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
    
    # ========================================================================
    # Prompt Template Methods
    # ========================================================================
    
    async def add_prompt_template(
        self,
        template_id: str,
        prompt_text: str,
        emotion_label: Optional[str] = None,
        description: Optional[str] = None,
        exaggeration: float = 0.15,
        cfg_weight: float = 0.8,
        temperature: float = 0.8,
        repetition_penalty: float = 1.2,
        target_valence: Optional[float] = None,
        target_arousal: Optional[float] = None,
        target_tension: Optional[float] = None,
        target_stability: Optional[float] = None
    ) -> bool:
        """Add a new prompt template to the database.
        
        Args:
            template_id: Unique identifier for the template
            prompt_text: The prompt text
            emotion_label: Human-readable emotion label
            description: Description of emotional intent
            exaggeration: Exaggeration parameter
            cfg_weight: CFG weight parameter
            temperature: Temperature parameter
            repetition_penalty: Repetition penalty parameter
            target_valence: Target valence coordinate
            target_arousal: Target arousal coordinate
            target_tension: Target tension coordinate
            target_stability: Target stability coordinate
            
        Returns:
            True if added successfully, False if template_id already exists
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO prompt_templates (
                        template_id, prompt_text, emotion_label, description,
                        exaggeration, cfg_weight, temperature, repetition_penalty,
                        target_valence, target_arousal, target_tension, target_stability
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        template_id, prompt_text, emotion_label, description,
                        exaggeration, cfg_weight, temperature, repetition_penalty,
                        target_valence, target_arousal, target_tension, target_stability
                    )
                )
                await db.commit()
                logger.info(f"Added prompt template: {template_id}")
                return True
        except aiosqlite.IntegrityError:
            logger.warning(f"Template ID already exists: {template_id}")
            return False
    
    async def get_prompt_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve prompt template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Dictionary with template data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM prompt_templates WHERE template_id = ?",
                (template_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def list_prompt_templates(self) -> List[Dict[str, Any]]:
        """List all prompt templates in the database.
        
        Returns:
            List of prompt template dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM prompt_templates ORDER BY emotion_label, template_id"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    # ========================================================================
    # Emotional Anchor Methods
    # ========================================================================
    
    async def add_emotional_anchor(
        self,
        anchor_id: str,
        base_voice_id: str,
        template_id: str,
        audio_file_path: str,
        sample_rate: int,
        valence: float,
        arousal: float,
        tension: float,
        stability: float,
        duration_seconds: Optional[float] = None,
        mean_pitch: Optional[float] = None,
        pitch_variance: Optional[float] = None,
        pitch_range: Optional[float] = None,
        mean_energy: Optional[float] = None,
        energy_variance: Optional[float] = None,
        speaking_rate: Optional[float] = None,
        spectral_centroid: Optional[float] = None
    ) -> bool:
        """Add a new emotional anchor to the database.
        
        Args:
            anchor_id: Unique identifier for the anchor
            base_voice_id: ID of the base voice used
            template_id: ID of the prompt template used
            audio_file_path: Path to the audio file
            sample_rate: Sample rate of the audio
            valence: Valence coordinate (-1.0 to 1.0)
            arousal: Arousal coordinate (0.0 to 1.0)
            tension: Tension coordinate (0.0 to 1.0)
            stability: Stability coordinate (0.0 to 1.0)
            duration_seconds: Duration of audio in seconds
            mean_pitch: Mean pitch feature
            pitch_variance: Pitch variance feature
            pitch_range: Pitch range feature
            mean_energy: Mean energy feature
            energy_variance: Energy variance feature
            speaking_rate: Speaking rate feature
            spectral_centroid: Spectral centroid feature
            
        Returns:
            True if added successfully, False if anchor_id already exists
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO emotional_anchors (
                        anchor_id, base_voice_id, template_id,
                        audio_file_path, sample_rate, duration_seconds,
                        valence, arousal, tension, stability,
                        mean_pitch, pitch_variance, pitch_range,
                        mean_energy, energy_variance, speaking_rate, spectral_centroid
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        anchor_id, base_voice_id, template_id,
                        audio_file_path, sample_rate, duration_seconds,
                        valence, arousal, tension, stability,
                        mean_pitch, pitch_variance, pitch_range,
                        mean_energy, energy_variance, speaking_rate, spectral_centroid
                    )
                )
                await db.commit()
                logger.info(f"Added emotional anchor: {anchor_id}")
                return True
        except aiosqlite.IntegrityError:
            logger.warning(f"Anchor ID already exists: {anchor_id}")
            return False
    
    async def get_emotional_anchor(self, anchor_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve emotional anchor by ID.
        
        Args:
            anchor_id: Anchor identifier
            
        Returns:
            Dictionary with anchor data or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM emotional_anchors WHERE anchor_id = ?",
                (anchor_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
    
    async def list_emotional_anchors(
        self,
        base_voice_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List emotional anchors, optionally filtered by base voice.
        
        Args:
            base_voice_id: Optional filter by base voice ID
            
        Returns:
            List of emotional anchor dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if base_voice_id:
                query = """
                    SELECT * FROM emotional_anchors 
                    WHERE base_voice_id = ? 
                    ORDER BY valence, arousal
                """
                params = (base_voice_id,)
            else:
                query = "SELECT * FROM emotional_anchors ORDER BY base_voice_id, valence, arousal"
                params = ()
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def find_nearest_anchor(
        self,
        base_voice_id: str,
        valence: float,
        arousal: float,
        tension: float,
        stability: float,
        k: int = 1
    ) -> List[Dict[str, Any]]:
        """Find k nearest emotional anchors to target coordinates.
        
        Args:
            base_voice_id: Base voice ID to search within
            valence: Target valence coordinate
            arousal: Target arousal coordinate
            tension: Target tension coordinate
            stability: Target stability coordinate
            k: Number of nearest neighbors to return
            
        Returns:
            List of k nearest anchor dictionaries with distances
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Calculate Euclidean distance in SQLite
            query = """
                SELECT *,
                    SQRT(
                        (valence - ?) * (valence - ?) +
                        (arousal - ?) * (arousal - ?) +
                        (tension - ?) * (tension - ?) +
                        (stability - ?) * (stability - ?)
                    ) as distance
                FROM emotional_anchors
                WHERE base_voice_id = ?
                ORDER BY distance
                LIMIT ?
            """
            
            async with db.execute(
                query,
                (
                    valence, valence,
                    arousal, arousal,
                    tension, tension,
                    stability, stability,
                    base_voice_id,
                    k
                )
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def update_emotional_anchor_features(
        self,
        anchor_id: str,
        mean_pitch: Optional[float] = None,
        pitch_variance: Optional[float] = None,
        pitch_range: Optional[float] = None,
        mean_energy: Optional[float] = None,
        energy_variance: Optional[float] = None,
        speaking_rate: Optional[float] = None,
        spectral_centroid: Optional[float] = None
    ) -> bool:
        """Update acoustic features for an emotional anchor.
        
        Args:
            anchor_id: Anchor identifier
            mean_pitch: Mean pitch feature
            pitch_variance: Pitch variance feature
            pitch_range: Pitch range feature
            mean_energy: Mean energy feature
            energy_variance: Energy variance feature
            speaking_rate: Speaking rate feature
            spectral_centroid: Spectral centroid feature
            
        Returns:
            True if updated, False if not found
        """
        # Build update query dynamically based on provided features
        updates = []
        params = []
        
        if mean_pitch is not None:
            updates.append("mean_pitch = ?")
            params.append(mean_pitch)
        if pitch_variance is not None:
            updates.append("pitch_variance = ?")
            params.append(pitch_variance)
        if pitch_range is not None:
            updates.append("pitch_range = ?")
            params.append(pitch_range)
        if mean_energy is not None:
            updates.append("mean_energy = ?")
            params.append(mean_energy)
        if energy_variance is not None:
            updates.append("energy_variance = ?")
            params.append(energy_variance)
        if speaking_rate is not None:
            updates.append("speaking_rate = ?")
            params.append(speaking_rate)
        if spectral_centroid is not None:
            updates.append("spectral_centroid = ?")
            params.append(spectral_centroid)
        
        if not updates:
            logger.warning(f"No features provided to update for anchor: {anchor_id}")
            return False
        
        params.append(anchor_id)
        query = f"UPDATE emotional_anchors SET {', '.join(updates)} WHERE anchor_id = ?"
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            updated = cursor.rowcount > 0
            if updated:
                logger.info(f"Updated features for emotional anchor: {anchor_id}")
            return updated
    
    async def delete_emotional_anchor(self, anchor_id: str) -> bool:
        """Delete an emotional anchor from the database.
        
        Args:
            anchor_id: Anchor identifier
            
        Returns:
            True if deleted, False if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM emotional_anchors WHERE anchor_id = ?",
                (anchor_id,)
            )
            await db.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted emotional anchor: {anchor_id}")
            return deleted
