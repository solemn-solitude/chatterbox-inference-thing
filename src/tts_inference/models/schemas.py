"""Pydantic models for request and response schemas."""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal
from datetime import datetime
import msgpack


class BaseVoiceConfig(BaseModel):
    """Base voice configuration for TTS synthesis."""

    voice_id: str | None = Field(None, description="ID of uploaded voice; omit to use server default")
    speed: float = Field(1.0, ge=0.1, le=3.0, description="Speech speed multiplier")

    @field_validator('voice_id')
    @classmethod
    def validate_voice_id(cls, v):
        if v is not None and not v.strip():
            raise ValueError("voice_id cannot be empty string")
        return v

    def to_msgpack(self) -> bytes:
        return msgpack.packb(self.model_dump(), use_bin_type=True)

    @classmethod
    def from_msgpack(cls, data: bytes):
        return cls(**msgpack.unpackb(data, raw=False))


class ChatterboxVoiceConfig(BaseVoiceConfig):
    """ChatterboxTTS-specific voice configuration."""

    exaggeration: float = Field(0.5, ge=0.0, le=1.0, description="Exaggeration level for expressiveness")
    cfg_weight: float = Field(0.5, ge=0.0, le=1.0, description="Classifier-free guidance weight")
    temperature: float = Field(0.8, ge=0.1, le=2.0, description="Sampling temperature for variability")
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0, description="Penalty for repetitive tokens")


class TTSRequest(BaseModel):
    """Request model for TTS synthesis."""

    text: str = Field(..., min_length=1, max_length=10000, description="Text to synthesize")
    voice_config: ChatterboxVoiceConfig = Field(default_factory=ChatterboxVoiceConfig, description="Voice configuration")  # type: ignore[call-arg]
    voice_id: str | None = Field(None, description="Shorthand voice ID; merged into voice_config if voice_config.voice_id is not set")
    audio_format: Literal["pcm", "wav", "vorbis"] = Field("pcm", description="Output audio format")
    sample_rate: int | None = Field(None, ge=20480, le=420480, description="Output sample rate (defaults to model.sr)")
    use_turbo: bool = Field(False, description="Use ChatterboxTurboTTS")

    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v

    @model_validator(mode='after')
    def merge_voice_id(self) -> 'TTSRequest':
        if self.voice_id and not self.voice_config.voice_id:
            self.voice_config.voice_id = self.voice_id
        return self

    def to_msgpack(self) -> bytes:
        return msgpack.packb(self.model_dump(), use_bin_type=True)

    @classmethod
    def from_msgpack(cls, data: bytes):
        return cls(**msgpack.unpackb(data, raw=False))


class VoiceUploadRequest(BaseModel):
    """Request model for voice upload (form data)."""

    voice_id: str = Field(..., min_length=1, max_length=100, description="Unique identifier for the voice")
    sample_rate: int = Field(..., ge=20480, le=420480, description="Sample rate of the audio file")
    voice_transcript: str = Field(..., min_length=1, max_length=1000, description="Transcript of what is spoken in the audio file")

    @field_validator('voice_id')
    @classmethod
    def validate_voice_id(cls, v):
        if not v.strip():
            raise ValueError("voice_id cannot be empty")
        invalid_chars = set('/\\:*?"<>|')
        if any(char in v for char in invalid_chars):
            raise ValueError(f"voice_id cannot contain: {' '.join(invalid_chars)}")
        return v.strip()

    @field_validator('voice_transcript')
    @classmethod
    def validate_transcript(cls, v):
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
