"""Client-side data models for chatterbox inference."""

from dataclasses import dataclass, field, asdict
from typing import Optional, Literal


@dataclass
class VoiceConfig:
    """Voice configuration for TTS synthesis."""
    
    # For default mode
    voice_name: Optional[str] = None
    
    # For clone mode
    voice_id: Optional[str] = None
    
    # Common settings
    speed: float = 1.0
    
    # ChatterboxTTS generation parameters
    exaggeration: float = 0.5
    cfg_weight: float = 0.5
    temperature: float = 0.8
    repetition_penalty: float = 1.2
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TTSRequest:
    """Request model for TTS synthesis."""
    
    text: str
    voice_mode: Literal["default", "clone"] = "default"
    voice_config: VoiceConfig = field(default_factory=lambda: VoiceConfig())
    audio_format: Literal["pcm", "wav", "vorbis"] = "pcm"
    sample_rate: Optional[int] = None
    use_turbo: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            'text': self.text,
            'voice_mode': self.voice_mode,
            'voice_config': self.voice_config.to_dict(),
            'audio_format': self.audio_format,
            'use_turbo': self.use_turbo
        }
        if self.sample_rate is not None:
            result['sample_rate'] = self.sample_rate
        return result


@dataclass
class VoiceInfo:
    """Response model for voice information."""
    
    voice_id: str
    filename: str
    sample_rate: int
    duration_seconds: Optional[float] = None
    uploaded_at: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VoiceInfo':
        """Create from dictionary."""
        return cls(
            voice_id=data.get('voice_id', ''),
            filename=data.get('filename', ''),
            sample_rate=data.get('sample_rate', 0),
            duration_seconds=data.get('duration_seconds'),
            uploaded_at=data.get('uploaded_at', '')
        )


@dataclass
class VoiceListResponse:
    """Response model for listing voices."""
    
    voices: list[VoiceInfo] = field(default_factory=list)
    total: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VoiceListResponse':
        """Create from dictionary."""
        voices_data = data.get('voices', [])
        voices = [VoiceInfo.from_dict(v) for v in voices_data]
        return cls(
            voices=voices,
            total=data.get('total', len(voices))
        )


@dataclass
class VoiceUploadResponse:
    """Response model for voice upload."""
    
    success: bool
    voice_id: str
    message: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VoiceUploadResponse':
        """Create from dictionary."""
        return cls(
            success=data.get('success', False),
            voice_id=data.get('voice_id', ''),
            message=data.get('message', '')
        )


@dataclass
class VoiceDeleteResponse:
    """Response model for voice deletion."""
    
    success: bool
    voice_id: str
    message: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VoiceDeleteResponse':
        """Create from dictionary."""
        return cls(
            success=data.get('success', False),
            voice_id=data.get('voice_id', ''),
            message=data.get('message', '')
        )


@dataclass
class HealthResponse:
    """Response model for health check."""
    
    status: str
    version: str
    timestamp: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HealthResponse':
        """Create from dictionary."""
        return cls(
            status=data.get('status', ''),
            version=data.get('version', ''),
            timestamp=data.get('timestamp', '')
        )


@dataclass
class ReadyResponse:
    """Response model for readiness check."""
    
    ready: bool
    model_loaded: bool
    voice_dir_accessible: bool
    database_accessible: bool
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ReadyResponse':
        """Create from dictionary."""
        return cls(
            ready=data.get('ready', False),
            model_loaded=data.get('model_loaded', False),
            voice_dir_accessible=data.get('voice_dir_accessible', False),
            database_accessible=data.get('database_accessible', False)
        )
