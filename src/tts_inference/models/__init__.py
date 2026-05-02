"""Data models for TTS Inference."""

from .schemas import (
    BaseVoiceConfig,
    ChatterboxVoiceConfig,
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
