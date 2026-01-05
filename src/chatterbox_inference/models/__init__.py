"""Data models for Chatterbox Inference."""

from .schemas import (
    VoiceConfig,
    TTSRequest,
    VoiceUploadRequest,
    VoiceInfo,
    VoiceListResponse,
    VoiceUploadResponse,
    VoiceDeleteResponse,
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
    "HealthResponse",
    "ReadyResponse",
    "ErrorResponse",
    "VoiceDatabase",
]
