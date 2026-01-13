"""Pydantic models for request and response schemas."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime


class VoiceConfig(BaseModel):
    """Voice configuration for TTS synthesis."""
    
    # For default mode
    voice_name: Optional[str] = Field(None, description="Name of default voice to use")
    
    # For clone mode
    voice_id: Optional[str] = Field(None, description="ID of uploaded voice for cloning")
    
    # Common settings
    speed: float = Field(1.0, ge=0.1, le=3.0, description="Speech speed multiplier")
    
    # ChatterboxTTS generation parameters
    exaggeration: float = Field(0.5, ge=0.0, le=1.0, description="Exaggeration level for expressiveness")
    cfg_weight: float = Field(0.5, ge=0.0, le=1.0, description="Classifier-free guidance weight")
    temperature: float = Field(0.8, ge=0.1, le=2.0, description="Sampling temperature for variability")
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0, description="Penalty for repetitive tokens")
    
    @field_validator('voice_name', 'voice_id')
    @classmethod
    def validate_voice(cls, v):
        """Ensure voice identifiers are valid."""
        if v is not None and not v.strip():
            raise ValueError("Voice name/ID cannot be empty")
        return v


class TTSRequest(BaseModel):
    """Request model for TTS synthesis."""
    
    text: str = Field(..., min_length=1, max_length=10000, description="Text to synthesize")
    voice_mode: Literal["default", "clone"] = Field("default", description="Voice mode to use")
    voice_config: VoiceConfig = Field(default_factory=VoiceConfig, description="Voice configuration")
    audio_format: Literal["pcm", "wav", "vorbis"] = Field("pcm", description="Output audio format")
    sample_rate: Optional[int] = Field(None, ge=20480, le=420480, description="Output sample rate (defaults to model.sr)")
    use_turbo: bool = Field(False, description="Use ChatterboxTurboTTS instead of ChatterboxTTS")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        """Ensure text is not empty."""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v
    
    def model_post_init(self, __context):
        """Validate mode-specific requirements."""
        if self.voice_mode == "default" and not self.voice_config.voice_name:
            self.voice_config.voice_name = "default"  # Set default voice
        elif self.voice_mode == "clone" and not self.voice_config.voice_id:
            raise ValueError("voice_id is required when voice_mode is 'clone'")


class VoiceUploadRequest(BaseModel):
    """Request model for voice upload (form data)."""
    
    voice_id: str = Field(..., min_length=1, max_length=100, description="Unique identifier for the voice")
    sample_rate: int = Field(..., ge=20480, le=420480, description="Sample rate of the audio file")
    
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


class VoiceInfo(BaseModel):
    """Response model for voice information."""
    
    voice_id: str
    filename: str
    sample_rate: int
    duration_seconds: Optional[float] = None
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
    detail: Optional[str] = None
    code: Optional[str] = None
