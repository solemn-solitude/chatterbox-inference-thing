"""Pydantic models for request and response schemas."""

from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime
import msgpack


class BaseVoiceConfig(BaseModel):
    """Base voice configuration for TTS synthesis."""
    
    # Common settings - voice cloning only
    voice_id: str = Field(..., description="ID of uploaded voice for cloning")
    speed: float = Field(1.0, ge=0.1, le=3.0, description="Speech speed multiplier (Chatterbox only)")
    
    @field_validator('voice_id')
    @classmethod
    def validate_voice_id(cls, v):
        """Ensure voice_id is valid."""
        if not v.strip():
            raise ValueError("voice_id cannot be empty")
        return v
    
    def to_msgpack(self) -> bytes:
        """Serialize to msgpack."""
        return msgpack.packb(self.model_dump(), use_bin_type=True)
    
    @classmethod
    def from_msgpack(cls, data: bytes):
        """Deserialize from msgpack."""
        return cls(**msgpack.unpackb(data, raw=False))


class ChatterboxVoiceConfig(BaseVoiceConfig):
    """ChatterboxTTS-specific voice configuration."""
    
    # ChatterboxTTS generation parameters
    exaggeration: float = Field(0.5, ge=0.0, le=1.0, description="Exaggeration level for expressiveness")
    cfg_weight: float = Field(0.5, ge=0.0, le=1.0, description="Classifier-free guidance weight")
    temperature: float = Field(0.8, ge=0.1, le=2.0, description="Sampling temperature for variability")
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0, description="Penalty for repetitive tokens")


class QwenVoiceConfig(BaseVoiceConfig):
    """Qwen3-TTS-specific voice configuration."""
    
    # Generation parameters
    language: str = Field("Auto", description="Language or 'Auto'")
    ref_text: str | None = Field(None, description="Reference text for cloning")
    
    # Model parameters
    max_new_tokens: int = Field(2048, ge=1, le=8192, description="Maximum new tokens to generate")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Top-p sampling parameter")
    top_k: int = Field(50, ge=1, le=100, description="Top-k sampling parameter")
    temperature: float = Field(0.9, ge=0.1, le=2.0, description="Sampling temperature")
    repetition_penalty: float = Field(1.05, ge=1.0, le=2.0, description="Repetition penalty")


class TTSRequest(BaseModel):
    """Request model for TTS synthesis."""
    
    text: str = Field(..., min_length=1, max_length=10000, description="Text to synthesize")
    voice_config: ChatterboxVoiceConfig | QwenVoiceConfig = Field(default_factory=ChatterboxVoiceConfig, description="Voice configuration")  # type: ignore[call-arg]
    audio_format: Literal["pcm", "wav", "vorbis"] = Field("pcm", description="Output audio format")
    sample_rate: int | None = Field(None, ge=20480, le=420480, description="Output sample rate (defaults to model.sr)")
    model_type: Literal["chatterbox", "qwen"] | None = Field(None, description="Override default TTS model")
    use_turbo: bool = Field(False, description="Use ChatterboxTurboTTS (Chatterbox only)")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        """Ensure text is not empty."""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v
    
    def to_msgpack(self) -> bytes:
        """Serialize to msgpack."""
        return msgpack.packb(self.model_dump(), use_bin_type=True)
    
    @classmethod
    def from_msgpack(cls, data: bytes):
        """Deserialize from msgpack."""
        return cls(**msgpack.unpackb(data, raw=False))


class VoiceUploadRequest(BaseModel):
    """Request model for voice upload (form data)."""
    
    voice_id: str = Field(..., min_length=1, max_length=100, description="Unique identifier for the voice")
    sample_rate: int = Field(..., ge=20480, le=420480, description="Sample rate of the audio file")
    voice_transcript: str = Field(..., min_length=1, max_length=1000, description="Transcript of what is spoken in the audio file")
    
    @field_validator('voice_id')
    @classmethod
    def validate_voice_id(cls, v):
        """Ensure voice_id is valid and safe for filesystem."""
        if not v.strip():
            raise ValueError("voice_id cannot be empty")
        # Check for invalid characters
        invalid_chars = set('/\\:*?"<>|')
        if any(char in v for char in invalid_chars):
            raise ValueError(f"voice_id cannot contain: {' '.join(invalid_chars)}")
        return v.strip()
    
    @field_validator('voice_transcript')
    @classmethod
    def validate_transcript(cls, v):
        """Ensure voice_transcript is not empty."""
        if not v.strip():
            raise ValueError("voice_transcript cannot be empty")
        return v.strip()


class VoiceInfo(BaseModel):
    """Response model for voice information."""
    
    voice_id: str
    filename: str
    sample_rate: int
    voice_transcript: str | None = None
    duration_seconds: float | None = None
    uploaded_at: str


class VoiceListResponse(BaseModel):
    """Response model for listing voices."""
    
    voices: list[VoiceInfo]
    total: int


class VoiceUploadResponse(BaseModel):
    """Response model for voice upload."""
    
    success: bool
    voice_id: str
    message: str


class VoiceDeleteResponse(BaseModel):
    """Response model for voice deletion."""
    
    success: bool
    voice_id: str
    message: str


class VoiceRenameResponse(BaseModel):
    """Response model for voice rename."""
    
    success: bool
    old_voice_id: str
    new_voice_id: str
    message: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str
    version: str
    timestamp: str


class ReadyResponse(BaseModel):
    """Response model for readiness check."""
    
    ready: bool
    model_loaded: bool
    voice_dir_accessible: bool
    database_accessible: bool


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    error: str
    detail: str | None = None
    code: str | None = None


class ModelInfoResponse(BaseModel):
    """Response model for model information."""
    
    model: str
    sample_rate: int | None = None


# ============================================================================
# Emotional Prosody Schemas
# ============================================================================


class EmotionalCoordinates(BaseModel):
    """4-dimensional emotional coordinates for prosody control."""
    
    valence: float = Field(..., ge=-1.0, le=1.0, description="Negative (-1.0) to Positive (+1.0)")
    arousal: float = Field(..., ge=0.0, le=1.0, description="Calm (0.0) to Excited (1.0)")
    tension: float = Field(..., ge=0.0, le=1.0, description="Relaxed (0.0) to Tense (1.0)")
    stability: float = Field(..., ge=0.0, le=1.0, description="Irregular (0.0) to Stable (1.0)")
    
    @classmethod
    def neutral(cls) -> "EmotionalCoordinates":
        """Return neutral emotional coordinates."""
        return cls(valence=0.0, arousal=0.5, tension=0.3, stability=0.8)
    
    def distance_to(self, other: "EmotionalCoordinates") -> float:
        """Calculate Euclidean distance to another coordinate.
        
        Args:
            other: Another EmotionalCoordinates instance
            
        Returns:
            Distance in 4D space
        """
        return (
            (self.valence - other.valence) ** 2 +
            (self.arousal - other.arousal) ** 2 +
            (self.tension - other.tension) ** 2 +
            (self.stability - other.stability) ** 2
        ) ** 0.5


class PromptTemplate(BaseModel):
    """Prompt template for generating emotional voice anchors."""
    
    template_id: str
    prompt_text: str
    emotion_label: str | None = None
    description: str | None = None
    
    # Generation parameters
    exaggeration: float = Field(0.15, ge=0.0, le=1.0)
    cfg_weight: float = Field(0.8, ge=0.0, le=1.0)
    temperature: float = Field(0.8, ge=0.1, le=2.0)
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0)
    
    # Target coordinates
    target_valence: float | None = Field(None, ge=-1.0, le=1.0)
    target_arousal: float | None = Field(None, ge=0.0, le=1.0)
    target_tension: float | None = Field(None, ge=0.0, le=1.0)
    target_stability: float | None = Field(None, ge=0.0, le=1.0)
    
    created_at: str | None = None
    
    @property
    def target_coords(self) -> EmotionalCoordinates | None:
        """Get target coordinates as EmotionalCoordinates object."""
        if all(x is not None for x in [
            self.target_valence, self.target_arousal, 
            self.target_tension, self.target_stability
        ]):
            return EmotionalCoordinates(
                valence=self.target_valence,
                arousal=self.target_arousal,
                tension=self.target_tension,
                stability=self.target_stability
            )
        return None


class AcousticFeatures(BaseModel):
    """Extracted acoustic features from voice samples."""
    
    mean_pitch: float | None = None
    pitch_variance: float | None = None
    pitch_range: float | None = None
    mean_energy: float | None = None
    energy_variance: float | None = None
    speaking_rate: float | None = None
    spectral_centroid: float | None = None


class EmotionalAnchor(BaseModel):
    """Emotional voice anchor with associated metadata."""
    
    anchor_id: str
    base_voice_id: str
    template_id: str
    
    # File storage
    audio_file_path: str
    sample_rate: int
    duration_seconds: float | None = None
    
    # Emotional coordinates
    valence: float = Field(..., ge=-1.0, le=1.0)
    arousal: float = Field(..., ge=0.0, le=1.0)
    tension: float = Field(..., ge=0.0, le=1.0)
    stability: float = Field(..., ge=0.0, le=1.0)
    
    # Acoustic features
    mean_pitch: float | None = None
    pitch_variance: float | None = None
    pitch_range: float | None = None
    mean_energy: float | None = None
    energy_variance: float | None = None
    speaking_rate: float | None = None
    spectral_centroid: float | None = None
    
    generated_at: str | None = None
    
    @property
    def coords(self) -> EmotionalCoordinates:
        """Get coordinates as EmotionalCoordinates object."""
        return EmotionalCoordinates(
            valence=self.valence,
            arousal=self.arousal,
            tension=self.tension,
            stability=self.stability
        )
    
    @property
    def features(self) -> AcousticFeatures:
        """Get acoustic features as AcousticFeatures object."""
        return AcousticFeatures(
            mean_pitch=self.mean_pitch,
            pitch_variance=self.pitch_variance,
            pitch_range=self.pitch_range,
            mean_energy=self.mean_energy,
            energy_variance=self.energy_variance,
            speaking_rate=self.speaking_rate,
            spectral_centroid=self.spectral_centroid
        )


class EmotionalTTSRequest(BaseModel):
    """Request model for emotional TTS synthesis."""
    
    text: str = Field(..., min_length=1, max_length=10000, description="Text to synthesize")
    emotional_coords: EmotionalCoordinates = Field(..., description="Target emotional coordinates")
    base_voice_id: str = Field(..., description="Base voice ID to use for anchor selection")
    audio_format: Literal["pcm", "wav", "vorbis"] = Field("pcm", description="Output audio format")
    sample_rate: int | None = Field(None, ge=20480, le=420480, description="Output sample rate")
    use_turbo: bool = Field(False, description="Use ChatterboxTurboTTS")
    
    # Optional smoothing parameters
    smoothing_factor: float = Field(0.5, ge=0.0, le=1.0, description="Temporal smoothing between turns")
    max_delta_per_turn: float = Field(0.3, ge=0.0, le=2.0, description="Maximum coordinate change per turn")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        """Ensure text is not empty."""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v


class AnchorListResponse(BaseModel):
    """Response model for listing emotional anchors."""
    
    anchors: list[EmotionalAnchor]
    total: int


class PromptTemplateListResponse(BaseModel):
    """Response model for listing prompt templates."""
    
    templates: list[PromptTemplate]
    total: int
