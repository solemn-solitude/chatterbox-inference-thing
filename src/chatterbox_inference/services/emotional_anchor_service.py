"""Emotional anchor management service - shared business logic."""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import aiosqlite

from ..models.database import VoiceDatabase
from ..emotion_map.anchor_generator import AnchorGenerator
from ..emotion_map.acoustic_features import AcousticFeatureExtractor
from ..emotion_map import PROMPT_TEMPLATES_SEED

logger = logging.getLogger(__name__)


class EmotionalAnchorService:
    """Service for emotional anchor operations."""
    
    def __init__(
        self,
        db: Optional[VoiceDatabase] = None,
        db_path: Optional[Path] = None,
        generator: Optional[AnchorGenerator] = None,
        extractor: Optional[AcousticFeatureExtractor] = None
    ):
        """Initialize emotional anchor service.
        
        Args:
            db: Database instance (optional, will be created if db_path provided)
            db_path: Path to database (optional, used to create db if not provided)
            generator: Anchor generator instance (optional)
            extractor: Feature extractor instance (optional)
        """
        if db is None and db_path is None:
            raise ValueError("Either db or db_path must be provided")
        
        self.db = db
        self.db_path = db_path
        self.generator = generator
        self.extractor = extractor or AcousticFeatureExtractor()
        self._db_initialized = db is not None
    
    async def _ensure_db(self):
        """Ensure database is initialized."""
        if not self._db_initialized:
            self.db = VoiceDatabase(self.db_path)
            await self.db.initialize()
            self._db_initialized = True
    
    # ========================================================================
    # Prompt Template Operations
    # ========================================================================
    
    async def seed_prompt_templates(self) -> int:
        """Seed prompt templates from SQL file.
        
        Returns:
            Number of templates seeded
            
        Raises:
            FileNotFoundError: If seed file doesn't exist
            Exception: If seeding fails
        """
        await self._ensure_db()
        
        if not PROMPT_TEMPLATES_SEED.exists():
            raise FileNotFoundError(f"Seed file not found: {PROMPT_TEMPLATES_SEED}")
        
        logger.info(f"Seeding prompt templates from {PROMPT_TEMPLATES_SEED}")
        
        # Read SQL file
        with open(PROMPT_TEMPLATES_SEED, 'r') as f:
            sql_script = f.read()
        
        # Execute SQL
        async with aiosqlite.connect(self.db.db_path) as db:
            await db.executescript(sql_script)
            await db.commit()
            
            # Count templates
            async with db.execute("SELECT COUNT(*) FROM prompt_templates") as cursor:
                count = (await cursor.fetchone())[0]
        
        logger.info(f"Seeded {count} prompt templates")
        return count
    
    async def list_prompt_templates(self) -> List[Dict[str, Any]]:
        """List all prompt templates.
        
        Returns:
            List of template dictionaries
        """
        return await self.db.list_prompt_templates()
    
    async def get_prompt_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific prompt template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template dictionary or None
        """
        return await self.db.get_prompt_template(template_id)
    
    # ========================================================================
    # Anchor Generation Operations
    # ========================================================================
    
    async def generate_anchors(
        self,
        base_voice_id: str,
        template_ids: Optional[List[str]] = None,
        skip_if_exists: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Generate emotional anchors from templates.
        
        Args:
            base_voice_id: Base voice ID
            template_ids: Optional list of template IDs (None = all)
            skip_if_exists: Skip existing anchors
            progress_callback: Optional progress callback
            
        Returns:
            Generation statistics
            
        Raises:
            ValueError: If generator not provided or voice not found
        """
        if self.generator is None:
            raise ValueError("AnchorGenerator not provided to service")
        
        # Verify voice exists
        voice = await self.db.get_voice(base_voice_id)
        if not voice:
            raise ValueError(f"Voice not found: {base_voice_id}")
        
        logger.info(f"Starting anchor generation for voice: {base_voice_id}")
        
        return await self.generator.generate_batch(
            base_voice_id=base_voice_id,
            template_ids=template_ids,
            skip_if_exists=skip_if_exists,
            progress_callback=progress_callback
        )
    
    async def list_anchors(
        self,
        base_voice_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List emotional anchors.
        
        Args:
            base_voice_id: Optional filter by base voice
            
        Returns:
            List of anchor dictionaries
        """
        await self._ensure_db()
        return await self.db.list_emotional_anchors(base_voice_id=base_voice_id)
    
    async def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get voice information.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            Voice dictionary or None if not found
        """
        await self._ensure_db()
        return await self.db.get_voice(voice_id)
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """List all voices.
        
        Returns:
            List of voice dictionaries
        """
        await self._ensure_db()
        return await self.db.list_voices()
    
    async def get_anchor(self, anchor_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific anchor.
        
        Args:
            anchor_id: Anchor identifier
            
        Returns:
            Anchor dictionary or None
        """
        return await self.db.get_emotional_anchor(anchor_id)
    
    async def delete_anchor(self, anchor_id: str) -> bool:
        """Delete an anchor.
        
        Args:
            anchor_id: Anchor identifier
            
        Returns:
            True if deleted
        """
        if self.generator is None:
            raise ValueError("AnchorGenerator not provided to service")
        
        return await self.generator.delete_anchor(anchor_id)
    
    # ========================================================================
    # Acoustic Analysis Operations
    # ========================================================================
    
    async def analyze_anchor(
        self,
        anchor_id: str,
        update_db: bool = False
    ) -> Dict[str, Any]:
        """Analyze acoustic features of an anchor.
        
        Args:
            anchor_id: Anchor identifier
            update_db: Whether to update database with features
            
        Returns:
            Dictionary with analysis results
            
        Raises:
            ValueError: If anchor not found or file missing
        """
        # Get anchor
        anchor = await self.db.get_emotional_anchor(anchor_id)
        if not anchor:
            raise ValueError(f"Anchor not found: {anchor_id}")
        
        # Check file exists
        filepath = Path(anchor['audio_file_path'])
        if not filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {filepath}")
        
        logger.info(f"Analyzing anchor: {anchor_id}")
        
        # Extract features
        features = self.extractor.extract_all_features(filepath)
        
        # Update database if requested
        if update_db:
            updated = await self.db.update_emotional_anchor_features(
                anchor_id=anchor_id,
                mean_pitch=features.get('mean_pitch'),
                pitch_variance=features.get('pitch_variance'),
                pitch_range=features.get('pitch_range'),
                mean_energy=features.get('mean_energy'),
                energy_variance=features.get('energy_variance'),
                speaking_rate=features.get('speaking_rate'),
                spectral_centroid=features.get('spectral_centroid')
            )
            features['db_updated'] = updated
        
        return {
            'anchor_id': anchor_id,
            'features': features,
            'success': True
        }
    
    async def analyze_anchors_batch(
        self,
        base_voice_id: str,
        anchor_ids: Optional[List[str]] = None,
        update_db: bool = False
    ) -> Dict[str, Any]:
        """Analyze multiple anchors in batch.
        
        Args:
            base_voice_id: Base voice ID to analyze
            anchor_ids: Optional list of specific anchor IDs
            update_db: Whether to update database
            
        Returns:
            Dictionary with batch analysis results
        """
        # Get anchors to analyze
        if anchor_ids:
            anchors = []
            for aid in anchor_ids:
                anchor = await self.db.get_emotional_anchor(aid)
                if anchor:
                    anchors.append(anchor)
        else:
            anchors = await self.db.list_emotional_anchors(base_voice_id=base_voice_id)
        
        logger.info(f"Analyzing {len(anchors)} anchors...")
        
        results = {
            'total': len(anchors),
            'analyzed': 0,
            'failed': 0,
            'failures': []
        }
        
        for anchor in anchors:
            try:
                await self.analyze_anchor(
                    anchor_id=anchor['anchor_id'],
                    update_db=update_db
                )
                results['analyzed'] += 1
            except Exception as e:
                results['failed'] += 1
                results['failures'].append({
                    'anchor_id': anchor['anchor_id'],
                    'error': str(e)
                })
                logger.error(f"Failed to analyze {anchor['anchor_id']}: {e}")
        
        return results
    
    # ========================================================================
    # Selection Operations (for future use)
    # ========================================================================
    
    async def find_nearest_anchors(
        self,
        base_voice_id: str,
        valence: float,
        arousal: float,
        tension: float,
        stability: float,
        k: int = 1
    ) -> List[Dict[str, Any]]:
        """Find k nearest anchors to target coordinates.
        
        Args:
            base_voice_id: Base voice ID
            valence: Target valence
            arousal: Target arousal
            tension: Target tension
            stability: Target stability
            k: Number of neighbors
            
        Returns:
            List of nearest anchors with distances
        """
        return await self.db.find_nearest_anchor(
            base_voice_id=base_voice_id,
            valence=valence,
            arousal=arousal,
            tension=tension,
            stability=stability,
            k=k
        )
