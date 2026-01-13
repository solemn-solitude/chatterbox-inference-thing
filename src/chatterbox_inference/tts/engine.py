"""TTS Engine wrapper for Chatterbox TTS."""

import torch
import numpy as np
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, AsyncIterator, Tuple
from datetime import datetime, timedelta
import logging

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
        from scipy import signal
        
        # Calculate new length
        new_length = int(len(audio) / speed)
        
        if new_length < 1:
            logger.warning(f"Speed {speed} results in audio too short, using speed 1.0")
            return audio
        
        # Resample using polyphase filtering (high quality)
        resampled = signal.resample(audio, new_length)
        
        # Ensure float32 and proper range
        resampled = np.clip(resampled, -1.0, 1.0).astype(np.float32)
        
        logger.debug(f"Resampled audio from {len(audio)} to {len(resampled)} samples (speed={speed})")
        return resampled
        
    except ImportError:
        logger.warning("scipy not available, falling back to numpy-based resampling")
        # Fallback: simple linear interpolation
        indices = np.linspace(0, len(audio) - 1, int(len(audio) / speed))
        resampled = np.interp(indices, np.arange(len(audio)), audio)
        return resampled.astype(np.float32)


class TTSEngine:
    """Wrapper for ChatterboxTTS engine with voice cloning and turbo support."""
    
    def __init__(self, inactivity_timeout: int = 600, keep_warm: bool = False):
        """Initialize TTS engine.
        
        Args:
            inactivity_timeout: Seconds of inactivity before offloading model (default: 600 = 10 minutes)
            keep_warm: If True, keep model loaded in memory (disable auto-offloading)
        """
        self.model_regular: Optional[object] = None
        self.model_turbo: Optional[object] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._default_sr: int = 24000  # ChatterboxTTS default sample rate
        
        # Inactivity tracking
        self.inactivity_timeout = inactivity_timeout
        self.keep_warm = keep_warm
        self.last_activity_time: Optional[datetime] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_offloaded = False
        
    async def initialize(self):
        """Initialize and load the TTS model (regular by default)."""
        logger.info("Loading ChatterboxTTS model on {}...".format(self.device))
        try:
            from chatterbox.tts import ChatterboxTTS
            self.model_regular = ChatterboxTTS.from_pretrained(device=self.device)
            
            # Get sample rate from model
            self._default_sr = getattr(self.model_regular, 'sr', 24000)
            
            logger.info("ChatterboxTTS model loaded successfully. Sample rate: {}".format(self._default_sr))
            
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
                from chatterbox.tts_turbo import ChatterboxTurboTTS
                self.model_turbo = ChatterboxTurboTTS.from_pretrained(device=self.device)
                logger.info("ChatterboxTurboTTS model loaded successfully")
            except Exception as e:
                logger.error("Failed to load ChatterboxTurboTTS model: {}".format(e))
                raise
    
    @property
    def sample_rate(self) -> int:
        """Get the model's default sample rate."""
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
        """Ensure model is loaded, reload if offloaded."""
        if self._is_offloaded or self.model_regular is None:
            logger.info("Model was offloaded, reloading...")
            await self.initialize()
        
        # Update last activity time
        self.last_activity_time = datetime.now()
    
    async def synthesize_streaming(
        self,
        text: str,
        voice_mode: str = "default",
        voice_reference: Optional[np.ndarray] = None,
        voice_name: Optional[str] = None,
        speed: float = 1.0,
        sample_rate: Optional[int] = None,
        use_turbo: bool = False,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.8,
        repetition_penalty: float = 1.2,
    ) -> AsyncIterator[Tuple[np.ndarray, int]]:
        """Generate speech audio with streaming support.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_reference: Reference audio for voice cloning (numpy array)
            voice_name: Name of default voice to use
            speed: Speech speed multiplier
            sample_rate: Output sample rate (defaults to model.sr)
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            exaggeration: Exaggeration level for expressiveness (0.0-1.0)
            cfg_weight: Classifier-free guidance weight (0.0-1.0)
            temperature: Sampling temperature for variability (0.1-2.0)
            repetition_penalty: Penalty for repetitive tokens (1.0-2.0)
            
        Yields:
            Tuple of (audio_chunk, sample_rate)
        """
        # Ensure model is loaded (will reload if offloaded)
        await self._ensure_loaded()
        
        # Select model based on turbo flag
        if use_turbo:
            await self._ensure_turbo_loaded()
            model = self.model_turbo
            model_name = "ChatterboxTurboTTS"
        else:
            model = self.model_regular
            model_name = "ChatterboxTTS"
        
        try:
            output_sr = sample_rate or self.sample_rate
            
            # Prepare audio prompt path if voice cloning is requested
            audio_prompt_path = None
            temp_file = None
            
            if voice_mode == "clone" and voice_reference is not None:
                try:
                    # Create temporary WAV file from voice reference
                    logger.info("Voice cloning mode: creating temporary reference audio file")
                    
                    # Encode the numpy array as WAV
                    wav_data = encode_wav_complete(voice_reference, self.sample_rate)
                    
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
    
    async def synthesize(
        self,
        text: str,
        voice_mode: str = "default",
        voice_reference: Optional[np.ndarray] = None,
        voice_name: Optional[str] = None,
        speed: float = 1.0,
        sample_rate: Optional[int] = None,
        use_turbo: bool = False,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.8,
        repetition_penalty: float = 1.2,
    ) -> Tuple[np.ndarray, int]:
        """Generate complete speech audio (non-streaming).
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_reference: Reference audio for voice cloning
            voice_name: Name of default voice to use
            speed: Speech speed multiplier
            sample_rate: Output sample rate
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            exaggeration: Exaggeration level for expressiveness (0.0-1.0)
            cfg_weight: Classifier-free guidance weight (0.0-1.0)
            temperature: Sampling temperature for variability (0.1-2.0)
            repetition_penalty: Penalty for repetitive tokens (1.0-2.0)
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        chunks = []
        output_sr = sample_rate or self.sample_rate
        
        async for chunk, sr in self.synthesize_streaming(
            text=text,
            voice_mode=voice_mode,
            voice_reference=voice_reference,
            voice_name=voice_name,
            speed=speed,
            sample_rate=sample_rate,
            use_turbo=use_turbo,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
        ):
            chunks.append(chunk)
            output_sr = sr
        
        if chunks:
            full_audio = np.concatenate(chunks)
            return full_audio, output_sr
        else:
            return np.array([]), output_sr


# Global TTS engine instance (will be initialized with config settings on startup)
tts_engine: Optional[TTSEngine] = None


def get_tts_engine() -> TTSEngine:
    """Get or create the global TTS engine instance.
    
    Returns:
        Global TTS engine instance
    """
    global tts_engine
    if tts_engine is None:
        from ..utils.config import config
        tts_engine = TTSEngine(
            inactivity_timeout=config.offload_timeout,
            keep_warm=config.keep_warm
        )
    return tts_engine
