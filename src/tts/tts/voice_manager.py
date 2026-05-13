"""Voice management for TTS cloning."""

import io
import logging
import wave
import numpy as np
from pathlib import Path

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
        
    async def _voice_exists(self, voice_id: str) -> bool:
        return await self.db.voice_exists(voice_id)

    def _generate_voice_path(self, voice_id: str) -> Path:
        filename = f"{voice_id}.wav"
        return self.voice_dir / filename

    def _read_audio_content(self, audio_file) -> bytes:
        return audio_file.read()

    async def _save_voice_to_db(
        self,
        voice_id: str,
        filepath: Path,
        sample_rate: int,
        voice_transcript: str,
        duration: float,
    ) -> bool:
        filename = filepath.name
        return await self.db.add_voice(
            voice_id=voice_id,
            filename=filename,
            sample_rate=sample_rate,
            voice_transcript=voice_transcript,
            duration_seconds=duration
        )

    def _cleanup_voice_file(self, filepath: Path):
        filepath.unlink(missing_ok=True)

    async def upload_voice(
        self,
        voice_id: str,
        audio_file,
        sample_rate: int,
        voice_transcript: str,
    ) -> bool:
        if await self._voice_exists(voice_id):
            logger.warning(f"Voice ID already exists: {voice_id}")
            return False

        filepath = self._generate_voice_path(voice_id)

        try:
            audio_content = self._read_audio_content(audio_file)
            duration = self._validate_and_get_duration(audio_content)

            with open(filepath, 'wb') as f:
                f.write(audio_content)

            success = await self._save_voice_to_db(
                voice_id, filepath, sample_rate, voice_transcript, duration
            )

            if success:
                logger.info(f"Voice uploaded: {voice_id} ({duration:.2f}s)")
            else:
                self._cleanup_voice_file(filepath)

            return success

        except Exception as e:
            logger.error(f"Error uploading voice {voice_id}: {e}")
            self._cleanup_voice_file(filepath)
            raise
    
    async def _get_voice_info(self, voice_id: str):
        return await self.db.get_voice(voice_id)

    async def _delete_voice_file(self, voice_info):
        filepath = self.voice_dir / voice_info.filename
        filepath.unlink(missing_ok=True)

    async def delete_voice(self, voice_id: str) -> bool:
        voice_info = await self._get_voice_info(voice_id)
        if not voice_info:
            logger.warning(f"Voice not found: {voice_id}")
            return False

        await self._delete_voice_file(voice_info)
        success = await self.db.delete_voice(voice_id)

        if success:
            logger.info(f"Voice deleted: {voice_id}")

        return success
    
    def _generate_new_voice_path(self, new_voice_id: str) -> Path:
        return self.voice_dir / f"{new_voice_id}.wav"

    async def _rollback_file_rename(self, new_filepath: Path, old_filepath: Path):
        if new_filepath.exists() and not old_filepath.exists():
            new_filepath.rename(old_filepath)

    async def rename_voice(self, old_voice_id: str, new_voice_id: str) -> bool:
        voice_info = await self._get_voice_info(old_voice_id)
        if not voice_info:
            logger.warning(f"Voice not found: {old_voice_id}")
            return False

        if await self._voice_exists(new_voice_id):
            logger.warning(f"Cannot rename: voice '{new_voice_id}' already exists")
            return False

        old_filepath = self.voice_dir / voice_info.filename
        new_filepath = self._generate_new_voice_path(new_voice_id)

        try:
            if old_filepath.exists():
                old_filepath.rename(new_filepath)
                logger.info(f"Renamed file: {voice_info.filename} -> {new_voice_id}.wav")

            success = await self.db.rename_voice(old_voice_id, new_voice_id)

            if not success:
                new_filepath.rename(old_filepath)
                logger.error("Rolled back file rename due to DB error")

            if success:
                logger.info(f"Voice renamed: {old_voice_id} -> {new_voice_id}")

            return success

        except Exception as e:
            logger.error(f"Error renaming voice {old_voice_id}: {e}")
            await self._rollback_file_rename(new_filepath, old_filepath)
            return False
    
    async def _get_voice_filepath(self, voice_id: str):
        voice_info = await self._get_voice_info(voice_id)
        if not voice_info:
            logger.warning(f"Voice not found: {voice_id}")
            return None
        filepath = self.voice_dir / voice_info.filename
        if not filepath.exists():
            logger.error(f"Voice file missing: {filepath}")
            return None
        return filepath

    def _get_wav_params(self, filepath: str):
        with wave.open(filepath, 'rb') as wav_file:
            return (
                wav_file.getframerate(),
                wav_file.getnchannels(),
                wav_file.getsampwidth(),
                wav_file.getnframes()
            )

    def _read_wav_audio(self, filepath: str, n_frames: int):
        with wave.open(filepath, 'rb') as wav_file:
            wav_file.setpos(0)
            return wav_file.readframes(n_frames)

    def _get_dtype(self, sample_width: int):
        if sample_width == 1:
            return np.uint8
        if sample_width == 2:
            return np.int16
        if sample_width == 4:
            return np.int32
        raise ValueError(f"Unsupported sample width: {sample_width}")

    def _bytes_to_float32(self, audio_bytes: bytes, dtype):
        audio_array = np.frombuffer(audio_bytes, dtype=dtype)
        if dtype == np.uint8:
            return (audio_array.astype(np.float32) - 128) / 128.0
        return audio_array.astype(np.float32) / np.iinfo(dtype).max

    def _to_mono(self, audio_array: np.ndarray, n_channels: int):
        if n_channels > 1:
            return audio_array.reshape(-1, n_channels).mean(axis=1)
        return audio_array

    async def load_voice_reference(self, voice_id: str) -> np.ndarray | None:
        filepath = await self._get_voice_filepath(voice_id)
        if not filepath:
            return None

        try:
            sample_rate, n_channels, sample_width, n_frames = self._get_wav_params(str(filepath))
            audio_bytes = self._read_wav_audio(str(filepath), n_frames)

            dtype = self._get_dtype(sample_width)
            audio_array = self._bytes_to_float32(audio_bytes, dtype)
            audio_array = self._to_mono(audio_array, n_channels)

            logger.info(f"Loaded voice reference: {voice_id} ({len(audio_array)} samples)")
            return audio_array

        except Exception as e:
            logger.error(f"Error loading voice reference {voice_id}: {e}")
            return None
    
    def _validate_and_get_duration(self, audio_content: bytes) -> float:
        if len(audio_content) < 12 or audio_content[:4] != b'RIFF' or audio_content[8:12] != b'WAVE':
            raise ValueError("Invalid WAV file: missing RIFF/WAVE header")
        with wave.open(io.BytesIO(audio_content), 'rb') as wav_file:
            sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            return n_frames / sample_rate
