"""Voice management for TTS cloning."""

import wave
import numpy as np
from pathlib import Path
from typing import BinaryIO
import logging

from ..models.database import VoiceDatabase
from ..utils.config import CONFIG

logger = logging.getLogger(__name__)


class VoiceManager:
    """Manages voice files and metadata for cloning."""
    
    def __init__(self, db: VoiceDatabase):
        """Initialize voice manager.
        
        Args:
            db: Voice database instance
        """
        self.db = db
        self.voice_dir = CONFIG.voice_audio_dir
        
    async def upload_voice(
        self,
        voice_id: str,
        audio_file: BinaryIO,
        sample_rate: int,
        voice_transcript: str,
    ) -> bool:
        """Upload and store a voice reference file.
        
        Args:
            voice_id: Unique identifier for the voice
            audio_file: Audio file content (WAV format)
            sample_rate: Sample rate of the audio
            voice_transcript: Transcript of what is spoken in the audio file
            
        Returns:
            True if successful, False if voice_id already exists
        """
        # Check if voice already exists
        if await self.db.voice_exists(voice_id):
            logger.warning(f"Voice ID already exists: {voice_id}")
            return False
        
        # Generate filename
        filename = f"{voice_id}.wav"
        filepath = self.voice_dir / filename
        
        try:
            # Read audio content
            audio_content = audio_file.read()
            
            # Validate WAV format and get duration
            duration = self._validate_and_get_duration(audio_content)
            
            # Save file
            with open(filepath, 'wb') as f:
                f.write(audio_content)
            
            # Add to database
            success = await self.db.add_voice(
                voice_id=voice_id,
                filename=filename,
                sample_rate=sample_rate,
                voice_transcript=voice_transcript,
                duration_seconds=duration
            )
            
            if success:
                logger.info(f"Voice uploaded successfully: {voice_id} ({duration:.2f}s)")
            else:
                # Clean up file if database insert failed
                filepath.unlink(missing_ok=True)
                
            return success
            
        except Exception as e:
            logger.error(f"Error uploading voice {voice_id}: {e}")
            # Clean up file if it was created
            filepath.unlink(missing_ok=True)
            raise
    
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a voice reference.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            True if deleted, False if not found
        """
        # Get voice info
        voice_info = await self.db.get_voice(voice_id)
        if not voice_info:
            logger.warning(f"Voice not found for deletion: {voice_id}")
            return False
        
        # Delete file
        filepath = self.voice_dir / voice_info['filename']
        filepath.unlink(missing_ok=True)
        
        # Delete from database
        success = await self.db.delete_voice(voice_id)
        
        if success:
            logger.info(f"Voice deleted: {voice_id}")
        
        return success
    
    async def rename_voice(self, old_voice_id: str, new_voice_id: str) -> bool:
        """Rename a voice reference.
        
        Args:
            old_voice_id: Current voice identifier
            new_voice_id: New voice identifier
            
        Returns:
            True if renamed successfully, False if failed
        """
        # Get voice info for old voice
        voice_info = await self.db.get_voice(old_voice_id)
        if not voice_info:
            logger.warning(f"Voice not found for rename: {old_voice_id}")
            return False
        
        # Check if new voice ID already exists
        if await self.db.voice_exists(new_voice_id):
            logger.warning(f"Cannot rename: voice '{new_voice_id}' already exists")
            return False
        
        # Rename file
        old_filename = voice_info['filename']
        old_filepath = self.voice_dir / old_filename
        new_filename = f"{new_voice_id}.wav"
        new_filepath = self.voice_dir / new_filename
        
        try:
            if old_filepath.exists():
                old_filepath.rename(new_filepath)
                logger.info(f"Renamed voice file: {old_filename} -> {new_filename}")
            
            # Update database
            success = await self.db.rename_voice(old_voice_id, new_voice_id)
            
            if success:
                logger.info(f"Voice renamed successfully: {old_voice_id} -> {new_voice_id}")
            else:
                # Rollback file rename if database update failed
                if new_filepath.exists():
                    new_filepath.rename(old_filepath)
                    logger.error(f"Rolled back file rename due to database error")
            
            return success
            
        except Exception as e:
            logger.error(f"Error renaming voice {old_voice_id}: {e}")
            # Try to rollback file rename
            if new_filepath.exists() and not old_filepath.exists():
                new_filepath.rename(old_filepath)
            return False
    
    async def load_voice_reference(self, voice_id: str) -> np.ndarray | None:
        """Load voice reference audio for cloning.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            Audio data as numpy array, or None if not found
        """
        # Get voice info
        voice_info = await self.db.get_voice(voice_id)
        if not voice_info:
            logger.warning(f"Voice not found: {voice_id}")
            return None
        
        # Load audio file
        filepath = self.voice_dir / voice_info['filename']
        if not filepath.exists():
            logger.error(f"Voice file missing: {filepath}")
            return None
        
        try:
            # Read WAV file
            with wave.open(str(filepath), 'rb') as wav_file:
                # Get audio parameters
                sample_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                n_frames = wav_file.getnframes()
                
                # Read audio data
                audio_bytes = wav_file.readframes(n_frames)
                
                # Convert to numpy array
                if sample_width == 1:
                    dtype = np.uint8
                elif sample_width == 2:
                    dtype = np.int16
                elif sample_width == 4:
                    dtype = np.int32
                else:
                    raise ValueError(f"Unsupported sample width: {sample_width}")
                
                audio_array = np.frombuffer(audio_bytes, dtype=dtype)
                
                # Convert to float32 normalized to [-1, 1]
                if dtype == np.uint8:
                    audio_array = (audio_array.astype(np.float32) - 128) / 128.0
                else:
                    audio_array = audio_array.astype(np.float32) / np.iinfo(dtype).max
                
                # Handle stereo - convert to mono if needed
                if n_channels > 1:
                    audio_array = audio_array.reshape(-1, n_channels).mean(axis=1)
                
                logger.info(f"Loaded voice reference: {voice_id} ({len(audio_array)} samples)")
                return audio_array
                
        except Exception as e:
            logger.error(f"Error loading voice reference {voice_id}: {e}")
            return None
    
    def _validate_and_get_duration(self, audio_content: bytes) -> float:
        """Validate WAV format and calculate duration.
        
        Args:
            audio_content: WAV file content
            
        Returns:
            Duration in seconds
            
        Raises:
            ValueError: If not a valid WAV file
        """
        try:
            import io
            with wave.open(io.BytesIO(audio_content), 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                duration = n_frames / sample_rate
                return duration
        except wave.Error as e:
            raise ValueError(f"Invalid WAV file: {e}")
