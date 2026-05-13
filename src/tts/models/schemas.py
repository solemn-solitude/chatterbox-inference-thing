"""Pydantic models for request and response schemas."""

from typing import Annotated, Literal
from datetime import datetime

import msgpack
from pydantic import BaseModel, Field, field_validator, model_validator


class BaseVoiceConfig(BaseModel):
    voice_id: str | None = Field(None, description="ID of uploaded voice; omit to use server default")
    speed: float = Field(1.0, ge=0.1, le=3.0, description="Speech speed multiplier")

    @field_validator("voice_id")
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
    type: Literal["chatterbox"] = "chatterbox"
    use_turbo: bool = Field(False, description="Use ChatterboxTurboTTS")
    exaggeration: float = Field(0.5, ge=0.0, le=1.0, description="Exaggeration level for expressiveness")
    cfg_weight: float = Field(0.5, ge=0.0, le=1.0, description="Classifier-free guidance weight")
    temperature: float = Field(0.8, ge=0.1, le=2.0, description="Sampling temperature for variability")
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0, description="Penalty for repetitive tokens")


class OmniVoiceVoiceConfig(BaseVoiceConfig):
    type: Literal["omnivoice"] = "omnivoice"
    voice_description: str | None = Field(None, description="Describe the desired voice (e.g. 'female, British accent')")
    language: str | None = Field(None, description="BCP-47 language code hint")
    num_step: int = Field(50, ge=1, le=200, description="Diffusion steps")
    guidance_scale: float = Field(1.0, ge=0.0, le=20.0, description="Classifier-free guidance scale")


class FishSpeechVoiceConfig(BaseVoiceConfig):
    type: Literal["fish-speech"] = "fish-speech"
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(0.7, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0, description="Penalty for repetitive tokens")
    chunk_length: int = Field(200, ge=100, le=1000, description="Text chunk length for generation")
    seed: int | None = Field(None, description="Random seed for reproducibility")
    normalize: bool = Field(True, description="Normalize text before synthesis")


VoiceConfig = Annotated[
    ChatterboxVoiceConfig | OmniVoiceVoiceConfig | FishSpeechVoiceConfig,
    Field(discriminator="type"),
]


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Text to synthesize")
    voice_config: VoiceConfig = Field(default_factory=ChatterboxVoiceConfig)
    voice_id: str | None = Field(None, description="Shorthand voice ID; merged into voice_config if voice_config.voice_id is not set")
    audio_format: Literal["pcm", "wav", "vorbis"] = Field("pcm", description="Output audio format")
    sample_rate: int | None = Field(None, ge=20480, le=420480, description="Output sample rate (defaults to model.sr)")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v

    @model_validator(mode="after")
    def merge_voice_id(self) -> "TTSRequest":
        if self.voice_id and not self.voice_config.voice_id:
            self.voice_config.voice_id = self.voice_id
        return self

    def to_msgpack(self) -> bytes:
        return msgpack.packb(self.model_dump(), use_bin_type=True)

    @classmethod
    def from_msgpack(cls, data: bytes):
        return cls(**msgpack.unpackb(data, raw=False))


class VoiceUploadRequest(BaseModel):
    voice_id: str = Field(..., min_length=1, max_length=100, description="Unique identifier for the voice")
    sample_rate: int = Field(..., ge=20480, le=420480, description="Sample rate of the audio file")
    voice_transcript: str = Field(..., min_length=1, max_length=1000, description="Transcript of what is spoken in the audio file")

    @field_validator("voice_id")
    @classmethod
    def validate_voice_id(cls, v):
        if not v.strip():
            raise ValueError("voice_id cannot be empty")
        invalid_chars = set('/\\:*?"<>|')
        if any(char in v for char in invalid_chars):
            raise ValueError(f"voice_id cannot contain: {' '.join(invalid_chars)}")
        return v.strip()

    @field_validator("voice_transcript")
    @classmethod
    def validate_transcript(cls, v):
        if not v.strip():
            raise ValueError("voice_transcript cannot be empty")
        return v.strip()


class VoiceInfo(BaseModel):
    voice_id: str
    filename: str
    sample_rate: int
    voice_transcript: str | None = None
    duration_seconds: float | None = None
    uploaded_at: str


class VoiceListResponse(BaseModel):
    voices: list[VoiceInfo]
    total: int


class VoiceUploadResponse(BaseModel):
    success: bool
    voice_id: str
    message: str


class VoiceDeleteResponse(BaseModel):
    success: bool
    voice_id: str
    message: str


class VoiceRenameResponse(BaseModel):
    success: bool
    old_voice_id: str
    new_voice_id: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class ReadyResponse(BaseModel):
    ready: bool
    model_loaded: bool
    voice_dir_accessible: bool
    database_accessible: bool


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    code: str | None = None


class ModelInfoResponse(BaseModel):
    model: str
    sample_rate: int | None = None
