"""Audio encoding utilities for streaming."""

import io
import struct
import numpy as np
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator, Tuple, List
import logging

logger = logging.getLogger(__name__)


def encode_pcm_s16le(audio_array: np.ndarray, sample_rate: int) -> bytes:
    """Encode audio as PCM s16le (signed 16-bit little-endian).
    
    Args:
        audio_array: Audio data as float32 in range [-1, 1]
        sample_rate: Sample rate of the audio
        
    Returns:
        PCM encoded bytes
    """
    # Clip to [-1, 1]
    audio_array = np.clip(audio_array, -1.0, 1.0)
    
    # Convert to int16
    audio_int16 = (audio_array * 32767).astype(np.int16)
    
    # Convert to bytes
    return audio_int16.tobytes()


def encode_wav_header(sample_rate: int, num_channels: int, num_samples: int) -> bytes:
    """Create WAV file header.
    
    Args:
        sample_rate: Sample rate
        num_channels: Number of channels
        num_samples: Total number of samples
        
    Returns:
        WAV header bytes
    """
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * num_channels * bits_per_sample // 8
    
    header = io.BytesIO()
    
    # RIFF header
    header.write(b'RIFF')
    header.write(struct.pack('<I', 36 + data_size))  # File size - 8
    header.write(b'WAVE')
    
    # fmt chunk
    header.write(b'fmt ')
    header.write(struct.pack('<I', 16))  # fmt chunk size
    header.write(struct.pack('<H', 1))   # PCM format
    header.write(struct.pack('<H', num_channels))
    header.write(struct.pack('<I', sample_rate))
    header.write(struct.pack('<I', byte_rate))
    header.write(struct.pack('<H', block_align))
    header.write(struct.pack('<H', bits_per_sample))
    
    # data chunk header
    header.write(b'data')
    header.write(struct.pack('<I', data_size))
    
    return header.getvalue()


def encode_wav_complete(audio_array: np.ndarray, sample_rate: int) -> bytes:
    """Encode complete audio as WAV.
    
    Args:
        audio_array: Audio data as float32 in range [-1, 1]
        sample_rate: Sample rate
        
    Returns:
        Complete WAV file bytes
    """
    num_samples = len(audio_array)
    header = encode_wav_header(sample_rate, 1, num_samples)
    pcm_data = encode_pcm_s16le(audio_array, sample_rate)
    return header + pcm_data


def encode_vorbis_complete(audio_array: np.ndarray, sample_rate: int, quality: float = 0.4) -> bytes:
    """Encode complete audio as Ogg Vorbis using ffmpeg.
    
    Args:
        audio_array: Audio data as float32 in range [-1, 1]
        sample_rate: Sample rate
        quality: Encoding quality (0.0 to 1.0)
        
    Returns:
        Vorbis encoded bytes
    """
    try:
        # Create complete WAV data
        wav_data = encode_wav_complete(audio_array, sample_rate)
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
            wav_path = tmp_wav.name
            tmp_wav.write(wav_data)
        
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_ogg:
            ogg_path = tmp_ogg.name
        
        try:
            # Use ffmpeg to convert WAV to Ogg Vorbis
            vorbis_quality = int(quality * 10)  # 0-10 scale
            
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite
                '-i', wav_path,
                '-c:a', 'libvorbis',
                '-q:a', str(vorbis_quality),
                '-f', 'ogg',
                ogg_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                timeout=30
            )
            
            # Read output
            with open(ogg_path, 'rb') as f:
                vorbis_data = f.read()
            
            logger.info(f"Encoded {len(audio_array)} samples to {len(vorbis_data)} bytes vorbis")
            return vorbis_data
            
        finally:
            # Cleanup
            Path(wav_path).unlink(missing_ok=True)
            Path(ogg_path).unlink(missing_ok=True)
            
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"ffmpeg error: {stderr}")
        raise RuntimeError(f"Vorbis encoding failed: {stderr}")
    except FileNotFoundError:
        logger.error("ffmpeg not found")
        raise RuntimeError("ffmpeg not installed. Please install ffmpeg for Vorbis support.")
    except Exception as e:
        logger.error(f"Error encoding vorbis: {e}")
        raise


class AudioStreamEncoder:
    """Helper class for streaming audio encoding."""
    
    def __init__(self, audio_format: str, sample_rate: int):
        """Initialize audio stream encoder.
        
        Args:
            audio_format: "pcm", "wav", or "vorbis"
            sample_rate: Sample rate
        """
        self.audio_format = audio_format
        self.sample_rate = sample_rate
        self._accumulated_chunks: List[np.ndarray] = []
        
    def encode_chunk(self, audio_array: np.ndarray) -> bytes:
        """Encode a single audio chunk for streaming.
        
        For PCM: Returns encoded chunk immediately
        For WAV/Vorbis: Accumulates chunks (returns empty bytes)
        
        Args:
            audio_array: Audio chunk as float32
            
        Returns:
            Encoded audio bytes (or empty for wav/vorbis during accumulation)
        """
        if self.audio_format == "pcm":
            # PCM can be streamed directly
            return encode_pcm_s16le(audio_array, self.sample_rate)
            
        else:
            # WAV and Vorbis need complete audio, so accumulate
            self._accumulated_chunks.append(audio_array.copy())
            return b""  # Return empty, will encode at the end
    
    def finalize(self) -> bytes:
        """Finalize encoding and return any remaining data.
        
        For WAV/Vorbis: Encodes all accumulated chunks
        For PCM: Returns empty bytes
        
        Returns:
            Final encoded bytes
        """
        if self._accumulated_chunks:
            # Concatenate all chunks
            full_audio = np.concatenate(self._accumulated_chunks)
            logger.info(f"Finalizing {self.audio_format} encoding with {len(full_audio)} total samples")
            
            if self.audio_format == "wav":
                return encode_wav_complete(full_audio, self.sample_rate)
            elif self.audio_format == "vorbis":
                return encode_vorbis_complete(full_audio, self.sample_rate)
        
        return b""
    
    def encode_complete(self, audio_array: np.ndarray) -> bytes:
        """Encode complete audio (non-streaming).
        
        Args:
            audio_array: Complete audio as float32
            
        Returns:
            Encoded audio bytes
        """
        if self.audio_format == "pcm":
            return encode_pcm_s16le(audio_array, self.sample_rate)
        elif self.audio_format == "wav":
            return encode_wav_complete(audio_array, self.sample_rate)
        elif self.audio_format == "vorbis":
            return encode_vorbis_complete(audio_array, self.sample_rate)
        else:
            raise ValueError(f"Unsupported audio format: {self.audio_format}")
