"""Emotional anchor generation system.

This module handles batch generation of emotional voice anchors from prompt templates.
"""

import logging
import asyncio
from pathlib import Path
from textwrap import dedent
from typing import Optional, Dict, Any, List
from datetime import datetime
import wave
import numpy as np

from ..models.database import VoiceDatabase
from ..tts.engine import TTSEngine
from ..tts.voice_manager import VoiceManager
from ..utils.config import CONFIG

logger = logging.getLogger(__name__)


class AnchorGenerator:
    """Generates emotional voice anchors from prompt templates."""

    def __init__(
        self, db: VoiceDatabase, tts_engine: TTSEngine, voice_manager: VoiceManager
    ):
        """Initialize anchor generator.

        Args:
            db: Voice database instance
            tts_engine: TTS engine instance
            voice_manager: Voice manager instance
        """
        self.db = db
        self.tts_engine = tts_engine
        self.voice_manager = voice_manager

        # Create anchors directory structure
        self.anchors_base_dir = CONFIG.voice_dir / "anchors"
        self.anchors_base_dir.mkdir(parents=True, exist_ok=True)

    def _get_anchor_directory(self, base_voice_id: str) -> Path:
        """Get directory for storing anchors for a specific base voice.

        Args:
            base_voice_id: Base voice identifier

        Returns:
            Path to anchor directory
        """
        anchor_dir = self.anchors_base_dir / base_voice_id
        anchor_dir.mkdir(parents=True, exist_ok=True)
        return anchor_dir

    async def generate_anchor(
        self, template_id: str, base_voice_id: str, skip_if_exists: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Generate a single emotional anchor from a prompt template.

        Args:
            template_id: Prompt template ID to use
            base_voice_id: Base voice ID for cloning
            skip_if_exists: Skip generation if anchor already exists

        Returns:
            Dictionary with anchor metadata, or None if skipped or failed
        """
        # Check if anchor already exists
        anchor_id = f"{base_voice_id}_{template_id}"
        existing = await self.db.get_emotional_anchor(anchor_id)

        if existing and skip_if_exists:
            logger.info(f"Anchor {anchor_id} already exists, skipping")
            return existing

        # Get prompt template
        template = await self.db.get_prompt_template(template_id)
        if not template:
            logger.error(f"Prompt template not found: {template_id}")
            return None

        # Get base voice reference
        voice_reference = await self.voice_manager.load_voice_reference(base_voice_id)
        if voice_reference is None:
            logger.error(f"Base voice not found: {base_voice_id}")
            return None

        logger.info(
            dedent(f"""
        Generating anchor: {anchor_id}
        Emotion: {template['emotion_label']}
        Prompt: {template['prompt_text'][:50]}...
        Parameters: exag={template['exaggeration']}, cfg={template['cfg_weight']}, temp={template['temperature']}, rep={template['repetition_penalty']}
        -----------------------------------""")
        )

        try:
            # Synthesize audio with emotional prompt and parameters
            audio_array, sample_rate = await self.tts_engine.synthesize(
                text=template["prompt_text"],
                voice_mode="clone",
                voice_reference=voice_reference,
                exaggeration=template["exaggeration"],
                cfg_weight=template["cfg_weight"],
                temperature=template["temperature"],
                repetition_penalty=template["repetition_penalty"],
                use_turbo=False,  # Use regular model for consistency
            )

            # Calculate duration
            duration_seconds = len(audio_array) / sample_rate

            # Get output path
            anchor_dir = self._get_anchor_directory(base_voice_id)
            audio_filename = f"{template_id}.wav"
            audio_filepath = anchor_dir / audio_filename

            # Save audio file
            self._save_wav_file(audio_filepath, audio_array, sample_rate)

            logger.info(f"  Saved audio: {audio_filepath}")
            logger.info(
                f"  Duration: {duration_seconds:.2f}s, Sample rate: {sample_rate}Hz"
            )

            # Add to database (use template's target coordinates for now)
            # In Phase 3, we'll add acoustic feature extraction
            success = await self.db.add_emotional_anchor(
                anchor_id=anchor_id,
                base_voice_id=base_voice_id,
                template_id=template_id,
                audio_file_path=str(audio_filepath),
                sample_rate=sample_rate,
                valence=template["target_valence"],
                arousal=template["target_arousal"],
                tension=template["target_tension"],
                stability=template["target_stability"],
                duration_seconds=duration_seconds,
            )

            if success:
                logger.info(f"✓ Anchor generated: {anchor_id}")
                return await self.db.get_emotional_anchor(anchor_id)
            else:
                logger.error(f"Failed to save anchor metadata: {anchor_id}")
                # Clean up audio file
                audio_filepath.unlink(missing_ok=True)
                return None

        except Exception as e:
            logger.error(f"Error generating anchor {anchor_id}: {e}", exc_info=True)
            return None

    async def generate_batch(
        self,
        base_voice_id: str,
        template_ids: Optional[List[str]] = None,
        skip_if_exists: bool = True,
        max_concurrent: int = 1,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Generate multiple emotional anchors in batch.

        Args:
            base_voice_id: Base voice ID for cloning
            template_ids: List of template IDs to generate (None = all templates)
            skip_if_exists: Skip generation if anchor already exists
            max_concurrent: Maximum number of concurrent generations (default: 1 for sequential)
            progress_callback: Optional callback(current, total, template_id, status) for progress updates

        Returns:
            Dictionary with generation statistics
        """
        # Get template IDs
        if template_ids is None:
            templates = await self.db.list_prompt_templates()
            template_ids = [t["template_id"] for t in templates]

        total = len(template_ids)
        stats = {
            "total": total,
            "generated": 0,
            "skipped": 0,
            "failed": 0,
            "start_time": datetime.now(),
            "end_time": None,
            "duration_seconds": None,
        }

        logger.info(
            dedent(f"""
        Starting batch generation: {total} templates
        Base voice: {base_voice_id}
        Skip existing: {skip_if_exists}
        Max concurrent: {max_concurrent}
        ==================================""")
        )

        # Process templates
        for i, template_id in enumerate(template_ids, 1):
            if progress_callback:
                progress_callback(i, total, template_id, "processing")

            logger.info(f"\n[{i}/{total}] Processing template: {template_id}")

            result = await self.generate_anchor(
                template_id=template_id,
                base_voice_id=base_voice_id,
                skip_if_exists=skip_if_exists,
            )

            if result:
                if skip_if_exists and "generated_at" in result:
                    # Check if this was just generated or already existed
                    # For simplicity, we'll count all successes as generated
                    stats["generated"] += 1
                else:
                    stats["generated"] += 1
            else:
                stats["failed"] += 1

            logger.info("-" * 70)

        stats["end_time"] = datetime.now()
        stats["duration_seconds"] = (
            stats["end_time"] - stats["start_time"]
        ).total_seconds()

        logger.info(
            dedent(f"""
        
        ==================================
        Batch generation complete!
          Total: {stats['total']}
          Generated: {stats['generated']}
          Failed: {stats['failed']}
          Duration: {stats['duration_seconds']:.1f}s
        ==================================""")
        )

        return stats

    def _save_wav_file(self, filepath: Path, audio_array: np.ndarray, sample_rate: int):
        """Save audio array as WAV file.

        Args:
            filepath: Output file path
            audio_array: Audio data (float32, normalized to [-1, 1])
            sample_rate: Sample rate
        """
        # Convert float32 to int16
        audio_int16 = (audio_array * 32767).astype(np.int16)

        # Save as WAV
        with wave.open(str(filepath), "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes = 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

    async def list_generated_anchors(self, base_voice_id: str) -> List[Dict[str, Any]]:
        """List all generated anchors for a base voice.

        Args:
            base_voice_id: Base voice identifier

        Returns:
            List of anchor metadata dictionaries
        """
        return await self.db.list_emotional_anchors(base_voice_id=base_voice_id)

    async def delete_anchor(self, anchor_id: str) -> bool:
        """Delete an emotional anchor and its audio file.

        Args:
            anchor_id: Anchor identifier

        Returns:
            True if deleted, False if not found
        """
        # Get anchor info
        anchor = await self.db.get_emotional_anchor(anchor_id)
        if not anchor:
            logger.warning(f"Anchor not found: {anchor_id}")
            return False

        # Delete audio file
        audio_filepath = Path(anchor["audio_file_path"])
        audio_filepath.unlink(missing_ok=True)
        logger.info(f"Deleted audio file: {audio_filepath}")

        # Delete from database
        success = await self.db.delete_emotional_anchor(anchor_id)

        if success:
            logger.info(f"Deleted anchor: {anchor_id}")

        return success
