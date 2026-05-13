"""Data models for TTS Inference."""

from .schemas import (
    BaseVoiceConfig,
    ChatterboxVoiceConfig,
    OmniVoiceVoiceConfig,
    FishSpeechVoiceConfig,
    VoiceConfig,
    TTSRequest,
    VoiceUploadRequest,
    VoiceInfo,
    VoiceListResponse,
    VoiceUploadResponse,
    VoiceDeleteResponse,
    VoiceRenameResponse,
    HealthResponse,
    ReadyResponse,
    ErrorResponse,
    ModelInfoResponse,
)
from .database import VoiceDatabase

__all__ = [
    "BaseVoiceConfig",
    "ChatterboxVoiceConfig",
    "OmniVoiceVoiceConfig",
    "FishSpeechVoiceConfig",
    "VoiceConfig",
    "TTSRequest",
    "VoiceUploadRequest",
    "VoiceInfo",
    "VoiceListResponse",
    "VoiceUploadResponse",
    "VoiceDeleteResponse",
    "VoiceRenameResponse",
    "HealthResponse",
    "ReadyResponse",
    "ErrorResponse",
    "ModelInfoResponse",
    "VoiceDatabase",
]
