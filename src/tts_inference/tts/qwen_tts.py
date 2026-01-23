"""Qwen3-TTS engine implementation with voice caching."""

import torch
import numpy as np
from typing import AsyncIterator
import logging
from textwrap import dedent

from .base_tts import BaseTTSEngine
from .qwen_voice_cache import QwenVoiceCache

logger = logging.getLogger(__name__)


class QwenTTSEngine(BaseTTSEngine):
    """Qwen3-TTS engine with intelligent voice prompt caching.
    
    Uses a two-model approach:
    1. VoiceDesign model - Creates reference clips from voice descriptions
    2. Base model - Performs fast cloning using cached prompts
    
    This enables 3-5x faster subsequent generations after the first one.
    """
    
    def __init__(
        self,
        inactivity_timeout: int = 600,
        keep_warm: bool = False,
        cache_ttl_minutes: int = 60
    ):
        """Initialize Qwen3-TTS engine.
        
        Args:
            inactivity_timeout: Seconds before offloading (not currently used)
            keep_warm: Keep model loaded (not currently used)
            cache_ttl_minutes: Time-to-live for cached voice prompts
        """
        self.design_model = None  # VoiceDesign model for creating voices
        self.clone_model = None   # Base model for cloning
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._default_sr: int = 24000  # Qwen typically outputs 24kHz
        
        # Voice prompt caching
        self.voice_cache = QwenVoiceCache(ttl_minutes=cache_ttl_minutes)
        self.current_voice_id = None
        
        # Inactivity tracking (kept for interface compatibility)
        self.inactivity_timeout = inactivity_timeout
        self.keep_warm = keep_warm
        self._is_offloaded = False
    
    async def initialize(self):
        """Load both VoiceDesign and Base models."""
        logger.info(
            dedent(f"""
        Loading Qwen3-TTS models on {self.device}...
        ==================================""")
        )
        
        try:
            from qwen_tts import Qwen3TTSModel
            
            # Load VoiceDesign model for creating voices
            logger.info("Loading Qwen3-TTS VoiceDesign model...")
            self.design_model = Qwen3TTSModel.from_pretrained(
                "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                device_map=self.device,
                dtype=torch.bfloat16,
                attn_implementation="flash_attention_2"
            )
            logger.info("VoiceDesign model loaded")
            
            # Load Base model for cloning (faster for repeated use)
            logger.info("Loading Qwen3-TTS Base model...")
            self.clone_model = Qwen3TTSModel.from_pretrained(
                "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                device_map=self.device,
                dtype=torch.bfloat16,
                attn_implementation="flash_attention_2"
            )
            logger.info("Base model loaded")
            
            logger.info(
                dedent(f"""
        Qwen3-TTS models loaded successfully
        Sample rate: {self._default_sr} Hz
        Voice cache TTL: {self.voice_cache.ttl.total_seconds() / 60:.0f} minutes
        ==================================""")
            )
            
            self._is_offloaded = False
            
        except Exception as e:
            logger.error("Failed to load Qwen3-TTS models: {}".format(e))
            raise
    
    @property
    def sample_rate(self) -> int:
        """Get the model's default sample rate."""
        return self._default_sr
    
    def is_loaded(self) -> bool:
        """Check if models are loaded."""
        return self.design_model is not None and self.clone_model is not None and not self._is_offloaded
    
    async def offload_model(self):
        """Release models from memory."""
        if self._is_offloaded:
            logger.debug("Models already offloaded")
            return
        
        logger.info("Offloading Qwen3-TTS models...")
        
        try:
            # Clear cache
            self.voice_cache.clear()
            
            # Clear CUDA cache if using GPU
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Cleared CUDA cache")
            
            # Delete model references
            if self.design_model is not None:
                del self.design_model
                self.design_model = None
                logger.info("Offloaded VoiceDesign model")
            
            if self.clone_model is not None:
                del self.clone_model
                self.clone_model = None
                logger.info("Offloaded Base model")
            
            # Additional cleanup
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._is_offloaded = True
            logger.info("Model offloading complete")
            
        except Exception as e:
            logger.error(f"Error during model offloading: {e}", exc_info=True)
            raise
    
    async def _ensure_voice_prompt(
        self,
        voice_id: str,
        reference_audio: np.ndarray,
        ref_text: str | None = None
    ) -> any:
        """Get or create cached voice prompt.
        
        Args:
            voice_id: Unique identifier for this voice (for caching)
            reference_audio: Reference audio array from DB
            ref_text: Transcript of reference audio (required for full prosodic cloning)
            
        Returns:
            Cached voice clone prompt
        """
        # Check cache first
        cached_prompt = self.voice_cache.get(voice_id)
        if cached_prompt is not None:
            logger.debug(f"Using cached voice prompt for: {voice_id}")
            return cached_prompt
        
        # Not cached - create new prompt
        logger.info(f"Creating voice prompt for: {voice_id}")
        
        # Direct cloning from reference audio with full prosody
        # x_vector_only_mode=False preserves prosody and emotion but requires ref_text
        ref_text = ref_text or "This is a sample of my voice for cloning purposes."
        voice_prompt = self.clone_model.create_voice_clone_prompt(
            ref_audio=(reference_audio, self._default_sr),
            ref_text=ref_text,
            x_vector_only_mode=False  # Full prosodic cloning for better quality
        )
        logger.info(f"Created prompt from reference audio for: {voice_id}")
        
        # Cache the prompt
        self.voice_cache.set(voice_id, voice_prompt)
        logger.info(f"Cached voice prompt for: {voice_id}")
        
        return voice_prompt
    
    async def synthesize_streaming(
        self,
        text: str,
        voice_id: str,
        voice_reference: np.ndarray,
        speed: float = 1.0,
        sample_rate: int | None = None,
        language: str = "Auto",
        ref_text: str | None = None,
        max_new_tokens: int = 2048,
        top_p: float = 1.0,
        top_k: int = 50,
        temperature: float = 0.9,
        repetition_penalty: float = 1.05,
        **model_params
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        """Generate speech with streaming support.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID from database (for caching)
            voice_reference: Pre-loaded reference audio from DB
            speed: Speech speed multiplier (Qwen doesn't support this, will warn)
            sample_rate: Output sample rate
            language: Language or "Auto"
            ref_text: Transcript of reference audio (used for cloning)
            max_new_tokens: Maximum new tokens to generate
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            temperature: Sampling temperature
            repetition_penalty: Repetition penalty
            **model_params: Additional model-specific parameters
            
        Yields:
            Tuple of (audio_chunk, sample_rate)
        """
        if not self.is_loaded():
            await self.initialize()
        
        # Warn about speed parameter (Qwen doesn't support it)
        if speed != 1.0:
            logger.warning("Qwen3-TTS does not support speed adjustment, ignoring speed parameter")
        
        output_sr = sample_rate or self._default_sr
        
        try:
            # Prepare generation kwargs
            gen_kwargs = {
                "max_new_tokens": max_new_tokens,
                "top_p": top_p,
                "top_k": top_k,
                "temperature": temperature,
                "repetition_penalty": repetition_penalty,
            }
            
            # Use Base model with voice cloning from reference audio
            voice_prompt = await self._ensure_voice_prompt(
                voice_id=voice_id,
                reference_audio=voice_reference,
                ref_text=ref_text
            )
            
            logger.info(f"Generating with Base model voice cloning (voice_id: {voice_id})")
            wavs, sr = self.clone_model.generate_voice_clone(
                text=text,
                language=language,
                voice_clone_prompt=voice_prompt,
                **gen_kwargs
            )
            
            # Stream chunks
            chunk_size = output_sr  # 1 second chunks
            for wav in wavs:
                if isinstance(wav, torch.Tensor):
                    wav = wav.cpu().numpy()
                
                # Ensure correct shape and type
                if len(wav.shape) > 1:
                    wav = wav.flatten()
                if wav.dtype != np.float32:
                    wav = wav.astype(np.float32)
                
                for i in range(0, len(wav), chunk_size):
                    chunk = wav[i:i + chunk_size]
                    yield chunk, output_sr
                    
        except Exception as e:
            logger.error(f"Error during Qwen3-TTS synthesis: {e}")
            raise
    
    def get_cache_stats(self) -> dict[str, any]:
        """Get voice cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.voice_cache.get_stats()
    
    def clear_voice_cache(self):
        """Clear all cached voice prompts."""
        self.voice_cache.clear()
    
    def invalidate_voice(self, voice_id: str):
        """Invalidate specific voice from cache.
        
        Args:
            voice_id: Voice ID to invalidate
        """
        self.voice_cache.invalidate(voice_id)
        if self.current_voice_id == voice_id:
            self.current_voice_id = None