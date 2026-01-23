"""Data models for TTS Inference."""

from .schemas import (
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
)
from .database import VoiceDatabase

__all__ = [
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
    "VoiceDatabase",
]
