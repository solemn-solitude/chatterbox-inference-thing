"""ChatterboxTTS engine implementation."""

import torch
import numpy as np
import tempfile
import asyncio
from pathlib import Path
from typing import AsyncIterator
from datetime import datetime
from textwrap import dedent
import logging
from scipy import signal

from chatterbox.tts import ChatterboxTTS
from chatterbox.tts_turbo import ChatterboxTurboTTS

from .base_tts import BaseTTSEngine
from ..utils.audio_utils import encode_wav_complete

logger = logging.getLogger(__name__)


def resample_audio_for_speed(audio: np.ndarray, speed: float) -> np.ndarray:
    """Resample audio to change playback speed.
    
    Args:
        audio: Audio array (float32, normalized to [-1, 1])
        speed: Speed multiplier (>1.0 = faster, <1.0 = slower)
        
    Returns:
        Resampled audio array
    """
    if speed == 1.0:
        return audio
    
    try:
        # Calculate new length
        new_length = int(len(audio) / speed)
        
        if new_length < 1:
            logger.warning(f"Speed {speed} results in audio too short, using speed 1.0")
            return audio
        
        # Resample using polyphase filtering (high quality)
        resampled = signal.resample(audio, new_length)
        
        # Ensure float32 and proper range
        resampled = np.clip(np.asarray(resampled), -1.0, 1.0).astype(np.float32)
        
        logger.debug(f"Resampled audio from {len(audio)} to {len(resampled)} samples (speed={speed})")
        return resampled
        
    except ImportError:
        logger.warning("scipy not available, falling back to numpy-based resampling")
        # Fallback: simple linear interpolation
        indices = np.linspace(0, len(audio) - 1, int(len(audio) / speed))
        resampled = np.interp(indices, np.arange(len(audio)), audio)
        return resampled.astype(np.float32)


class ChatterboxTTSEngine(BaseTTSEngine):
    """ChatterboxTTS engine with voice cloning and turbo support."""
    
    def __init__(self, inactivity_timeout: int = 600, keep_warm: bool = False):
        """Initialize ChatterboxTTS engine.
        
        Args:
            inactivity_timeout: Seconds of inactivity before offloading model (default: 600 = 10 minutes)
            keep_warm: If True, keep model loaded in memory (disable auto-offloading)
        """
        self.model_regular: ChatterboxTTS | None = None
        self.model_turbo: ChatterboxTurboTTS | None = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._default_sr: int = 24000  # ChatterboxTTS default sample rate
        
        # Inactivity tracking
        self.inactivity_timeout = inactivity_timeout
        self.keep_warm = keep_warm
        self.last_activity_time: datetime | None = None
        self._monitor_task: asyncio.Task | None = None
        self._is_offloaded = False
        
    async def initialize(self):
        """Initialize and load the TTS model (regular by default)."""
        logger.info(
            dedent(f"""
        Loading ChatterboxTTS model on {self.device}...
        ==================================""")
        )
        try:
            self.model_regular = ChatterboxTTS.from_pretrained(device=self.device)
            
            # Get sample rate from model
            self._default_sr = getattr(self.model_regular, 'sr', 24000)
            
            logger.info(
                dedent(f"""
        ChatterboxTTS model loaded successfully
        Sample rate: {self._default_sr} Hz
        ==================================""")
            )
            
            # Update activity time and start monitoring
            self.last_activity_time = datetime.now()
            self._is_offloaded = False
            
            # Only start monitoring if keep_warm is disabled
            if not self.keep_warm:
                self._start_inactivity_monitor()
            else:
                logger.info("Keep-warm mode enabled, model will remain loaded")
            
        except Exception as e:
            logger.error("Failed to load ChatterboxTTS model: {}".format(e))
            raise
    
    async def _ensure_turbo_loaded(self):
        """Load turbo model if not already loaded."""
        if self.model_turbo is None:
            logger.info("Loading ChatterboxTurboTTS model on {}...".format(self.device))
            try:
                self.model_turbo = ChatterboxTurboTTS.from_pretrained(device=self.device)
                
                # Update default sample rate from turbo model if not set from regular model
                turbo_sr = getattr(self.model_turbo, 'sr', 24000)
                if self._default_sr != turbo_sr:
                    logger.info(f"ChatterboxTurboTTS sample rate: {turbo_sr} Hz (regular: {self._default_sr} Hz)")
                
                logger.info("ChatterboxTurboTTS model loaded successfully")
            except Exception as e:
                logger.error("Failed to load ChatterboxTurboTTS model: {}".format(e))
                raise
        
        # Update last activity time
        self.last_activity_time = datetime.now()
        self._is_offloaded = False
    
    @property
    def sample_rate(self) -> int:
        """Get the model's default sample rate."""
        return self._default_sr
    
    def get_model_sample_rate(self, use_turbo: bool = False) -> int:
        """Get the sample rate for a specific model.
        
        Args:
            use_turbo: Whether to get turbo model's sample rate
            
        Returns:
            Sample rate in Hz
        """
        if use_turbo and self.model_turbo is not None:
            return getattr(self.model_turbo, 'sr', self._default_sr)
        elif self.model_regular is not None:
            return getattr(self.model_regular, 'sr', self._default_sr)
        return self._default_sr
    
    def is_loaded(self) -> bool:
        """Check if model is loaded (and not offloaded)."""
        return self.model_regular is not None and not self._is_offloaded
    
    def _start_inactivity_monitor(self):
        """Start background task to monitor inactivity."""
        if self.keep_warm:
            logger.debug("Keep-warm enabled, skipping inactivity monitor")
            return
            
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_inactivity())
            logger.info("Started inactivity monitor (timeout: {}s)".format(self.inactivity_timeout))
    
    async def _monitor_inactivity(self):
        """Monitor for inactivity and offload model if inactive."""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                
                if self.last_activity_time and not self._is_offloaded:
                    inactive_duration = (datetime.now() - self.last_activity_time).total_seconds()
                    
                    if inactive_duration >= self.inactivity_timeout:
                        logger.info(f"Model inactive for {inactive_duration:.0f}s, offloading...")
                        await self.offload_model()
                        
        except asyncio.CancelledError:
            logger.info("Inactivity monitor stopped")
        except Exception as e:
            logger.error(f"Error in inactivity monitor: {e}", exc_info=True)
    
    async def offload_model(self):
        """Offload model from memory to save resources."""
        if self._is_offloaded:
            logger.debug("Model already offloaded")
            return
        
        logger.info("Offloading TTS models from memory...")
        
        try:
            # Clear CUDA cache if using GPU
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Cleared CUDA cache")
            
            # Delete model references
            if self.model_regular is not None:
                del self.model_regular
                self.model_regular = None
                logger.info("Offloaded regular model")
            
            if self.model_turbo is not None:
                del self.model_turbo
                self.model_turbo = None
                logger.info("Offloaded turbo model")
            
            # Additional cleanup
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._is_offloaded = True
            logger.info("Model offloading complete")
            
        except Exception as e:
            logger.error(f"Error during model offloading: {e}", exc_info=True)
            raise
    
    async def _ensure_loaded(self):
        """Ensure regular model is loaded, reload if offloaded."""
        if self._is_offloaded or self.model_regular is None:
            logger.info("Model was offloaded, reloading...")
            await self.initialize()
        
        # Update last activity time
        self.last_activity_time = datetime.now()
        self._is_offloaded = False
    
    async def synthesize_streaming(
        self,
        text: str,
        voice_id: str,
        voice_reference: np.ndarray,
        speed: float = 1.0,
        sample_rate: int | None = None,
        use_turbo: bool = False,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.8,
        repetition_penalty: float = 1.2,
        **model_params
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        """Generate speech audio with streaming support.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID (for compatibility, not used by Chatterbox)
            voice_reference: Reference audio for voice cloning (numpy array)
            speed: Speech speed multiplier
            sample_rate: Output sample rate (defaults to model.sr)
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            exaggeration: Exaggeration level for expressiveness (0.0-1.0)
            cfg_weight: Classifier-free guidance weight (0.0-1.0)
            temperature: Sampling temperature for variability (0.1-2.0)
            repetition_penalty: Penalty for repetitive tokens (1.0-2.0)
            **model_params: Additional parameters (unused in Chatterbox)
            
        Yields:
            Tuple of (audio_chunk, sample_rate)
        """
        # Select and load only the needed model
        if use_turbo:
            await self._ensure_turbo_loaded()
            model = self.model_turbo
            model_name = "ChatterboxTurboTTS"
        else:
            await self._ensure_loaded()
            model = self.model_regular
            model_name = "ChatterboxTTS"
        
        
        try:
            # Use the correct sample rate for the selected model
            model_sr = self.get_model_sample_rate(use_turbo)
            output_sr = sample_rate or model_sr
            
            # Prepare audio prompt path for voice cloning (always done now)
            audio_prompt_path = None
            temp_file = None
            
            try:
                # Create temporary WAV file from voice reference
                logger.info("Voice cloning: creating temporary reference audio file")
                
                # Encode the numpy array as WAV using the model's sample rate
                wav_data = encode_wav_complete(voice_reference, model_sr)
                
                # Save to temporary file
                temp_file = tempfile.NamedTemporaryFile(
                    mode='wb',
                    suffix='.wav',
                    delete=False
                )
                temp_file.write(wav_data)
                temp_file.close()
                
                audio_prompt_path = temp_file.name
                logger.info(f"Voice cloning: saved reference audio to {audio_prompt_path}")
                
            except Exception as e:
                logger.error(f"Error preparing voice reference for cloning: {e}")
                if temp_file and hasattr(temp_file, 'name'):
                    Path(temp_file.name).unlink(missing_ok=True)
                raise
            
            logger.info("Generating speech with {} for text: {}...".format(model_name, text[:50]))
            
            try:
                # ChatterboxTTS.generate returns a single wav tensor/array
                # The signature is: generate(text, repetition_penalty, min_p, top_p, 
                #                            audio_prompt_path, exaggeration, cfg_weight, temperature)

                if not model:
                    logger.error("Model was not set. Could not do generation.")
                    return


                wav = model.generate(
                    text,
                    repetition_penalty=repetition_penalty,
                    audio_prompt_path=audio_prompt_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                    temperature=temperature
                )
                
                # Convert to numpy array if needed
                if isinstance(wav, torch.Tensor):
                    audio_array = wav.cpu().numpy()
                else:
                    audio_array = np.array(wav)
                
                # Ensure correct shape (flatten if needed)
                if len(audio_array.shape) > 1:
                    audio_array = audio_array.flatten()
                
                # Convert to float32 if needed
                if audio_array.dtype != np.float32:
                    audio_array = audio_array.astype(np.float32)
                
                # Apply speed adjustment if needed
                if speed != 1.0:
                    logger.info(f"Applying speed adjustment: {speed}x")
                    audio_array = resample_audio_for_speed(audio_array, speed)
                
                # Chunk the audio for streaming (e.g., 1 second chunks)
                chunk_size = output_sr  # 1 second chunks
                for i in range(0, len(audio_array), chunk_size):
                    chunk = audio_array[i:i + chunk_size]
                    yield chunk, output_sr
                    
            finally:
                # Clean up temporary voice reference file
                if temp_file and hasattr(temp_file, 'name'):
                    try:
                        Path(temp_file.name).unlink(missing_ok=True)
                        logger.debug(f"Cleaned up temporary voice reference file: {temp_file.name}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temporary file: {cleanup_error}")
                    
        except Exception as e:
            logger.error("Error during TTS synthesis with {}: {}".format(model_name, e))
            raise