"""Qwen3-TTS engine implementation with voice caching."""

import torch
import numpy as np
from typing import Optional, AsyncIterator, Tuple, Dict
import logging
from textwrap import dedent

from .base_tts import BaseTTSEngine
from .qwen_voice_cache import QwenVoiceCache

logger = logging.getLogger(__name__)


# Predefined voice descriptions for common voices
PREDEFINED_VOICES: Dict[str, str] = {
    "solar": "Young male voice, energetic and enthusiastic with bright timbre, confident and engaging",
    "default": "Natural speaking voice with clear pronunciation and moderate energy",
    # Add more voices as needed
}


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
        voice_description: Optional[str] = None,
        reference_audio: Optional[np.ndarray] = None,
        ref_text: Optional[str] = None
    ) -> any:
        """Get or create cached voice prompt.
        
        Args:
            voice_id: Unique identifier for this voice
            voice_description: Natural language description (for VoiceDesign)
            reference_audio: Reference audio array (for direct cloning)
            ref_text: Reference text for cloning
            
        Returns:
            Cached voice clone prompt
        """
        # Check cache first
        cached_prompt = self.voice_cache.get(voice_id)
        if cached_prompt is not None:
            return cached_prompt
        
        # Not cached - create new prompt
        logger.info(f"Creating voice prompt for: {voice_id}")
        
        if reference_audio is not None:
            # Direct cloning from reference audio (x-vector only mode)
            voice_prompt = self.clone_model.create_voice_clone_prompt(
                ref_audio=(reference_audio, self._default_sr),
                ref_text=ref_text or "",
                x_vector_only_mode=True
            )
            logger.info(f"Created prompt from reference audio for: {voice_id}")
            
        elif voice_description:
            # Create reference using VoiceDesign, then clone
            ref_text = ref_text or "This is a voice reference for cloning."
            
            logger.info(f"Designing voice for: {voice_id}")
            ref_wavs, sr = self.design_model.generate_voice_design(
                text=ref_text,
                language="English",  # Reference text in English
                instruct=voice_description
            )
            
            # Build clone prompt from designed voice
            voice_prompt = self.clone_model.create_voice_clone_prompt(
                ref_audio=(ref_wavs[0], sr),
                ref_text=ref_text,
                x_vector_only_mode=False
            )
            logger.info(f"Created prompt from voice design for: {voice_id}")
        else:
            raise ValueError("Must provide voice_description or reference_audio")
        
        # Cache the prompt
        self.voice_cache.set(voice_id, voice_prompt)
        logger.info(f"Cached voice prompt for: {voice_id}")
        
        return voice_prompt
    
    async def synthesize_streaming(
        self,
        text: str,
        voice_mode: str,
        voice_reference: Optional[np.ndarray] = None,
        voice_name: Optional[str] = None,
        speed: float = 1.0,
        sample_rate: Optional[int] = None,
        voice_id: Optional[str] = None,
        voice_description: Optional[str] = None,
        language: str = "Auto",
        instruct: Optional[str] = None,
        ref_text: Optional[str] = None,
        max_new_tokens: int = 2048,
        top_p: float = 1.0,
        top_k: int = 50,
        temperature: float = 0.9,
        repetition_penalty: float = 1.05,
        **model_params
    ) -> AsyncIterator[Tuple[np.ndarray, int]]:
        """Generate speech with streaming support.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_reference: Reference audio for voice cloning (numpy array)
            voice_name: Name of voice/speaker to use
            speed: Speech speed multiplier (Qwen doesn't support this, will warn)
            sample_rate: Output sample rate
            voice_id: Unique voice ID for caching
            voice_description: Natural language voice description
            language: Language or "Auto"
            instruct: Voice instruction override
            ref_text: Reference text for cloning
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
        
        # Determine voice prompt strategy
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
            
            # Voice selection logic
            if voice_id and voice_description:
                # Use cached VoiceDesign + Clone workflow
                voice_prompt = await self._ensure_voice_prompt(
                    voice_id=voice_id,
                    voice_description=voice_description,
                    ref_text=ref_text
                )
                
                wavs, sr = self.clone_model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=voice_prompt,
                    **gen_kwargs
                )
                
            elif voice_id and voice_reference is not None:
                # Direct cloning with caching
                voice_prompt = await self._ensure_voice_prompt(
                    voice_id=voice_id,
                    reference_audio=voice_reference,
                    ref_text=ref_text
                )
                
                wavs, sr = self.clone_model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=voice_prompt,
                    **gen_kwargs
                )
                
            elif voice_name and voice_name.lower() in PREDEFINED_VOICES:
                # Use predefined voice with VoiceDesign + Clone
                voice_prompt = await self._ensure_voice_prompt(
                    voice_id=voice_name,
                    voice_description=PREDEFINED_VOICES[voice_name.lower()],
                    ref_text=ref_text or f"This is {voice_name} speaking."
                )
                
                wavs, sr = self.clone_model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=voice_prompt,
                    **gen_kwargs
                )
                
            elif voice_description:
                # VoiceDesign without explicit voice_id (generate with voice_name as ID)
                if not voice_id:
                    voice_id = f"voice_design_{hash(voice_description) % 10000}"
                
                voice_prompt = await self._ensure_voice_prompt(
                    voice_id=voice_id,
                    voice_description=voice_description,
                    ref_text=ref_text or "Voice reference."
                )
                
                wavs, sr = self.clone_model.generate_voice_clone(
                    text=text,
                    language=language,
                    voice_clone_prompt=voice_prompt,
                    **gen_kwargs
                )
                
            else:
                raise ValueError(
                    "Must provide one of: voice_id+description, voice_id+reference_audio, "
                    "voice_name (predefined), or voice_description"
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
    
    def get_cache_stats(self) -> Dict[str, any]:
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