"""Configuration management for TTS Inference."""

import os
from pathlib import Path


def _env(primary: str, fallback: str | None = None, default: str = "") -> str:
    """Read env var with optional legacy fallback name."""
    value = os.getenv(primary)
    if value is not None:
        return value
    if fallback is not None:
        value = os.getenv(fallback)
        if value is not None:
            return value
    return default


class Config:
    """Global configuration for TTS Inference."""

    def __init__(self):
        self.tts_engine = _env("TTS_ENGINE", default="chatterbox")

        self.voice_dir = Path(
            _env("TTS_VOICE_DIR", "CHATTERBOX_VOICE_DIR",
                 os.path.expanduser("~/.local/share/tts-inference"))
        )
        self.voice_audio_dir = self.voice_dir / "voices"
        self.database_path = self.voice_dir / "voices.db"

        self.api_key = _env("TTS_API_KEY", "CHATTERBOX_API_KEY")
        self.default_voice_id = _env("TTS_DEFAULT_VOICE_ID", "CHATTERBOX_DEFAULT_VOICE_ID")

        self.fastapi_host = _env("TTS_FASTAPI_HOST", "CHATTERBOX_FASTAPI_HOST", "0.0.0.0")
        self.fastapi_port = int(_env("TTS_FASTAPI_PORT", "CHATTERBOX_FASTAPI_PORT", "20480"))

        self.zmq_input_address = _env("TTS_INPUT_ADDRESS", default="tcp://*:20501")
        self.zmq_pub_address = _env("TTS_PUB_ADDRESS", default="tcp://*:20502")

        self.log_level = _env("TTS_LOG_LEVEL", "CHATTERBOX_LOG_LEVEL", "INFO")

        self.offload_timeout = int(_env("TTS_OFFLOAD_TIMEOUT", "CHATTERBOX_OFFLOAD_TIMEOUT", "600"))
        self.keep_warm = _env("TTS_KEEP_WARM", "CHATTERBOX_KEEP_WARM", "false").lower() in ("true", "1", "yes")

    def ensure_directories(self):
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.voice_audio_dir.mkdir(parents=True, exist_ok=True)

    def validate_api_key(self) -> bool:
        if not self.api_key:
            raise ValueError(
                "TTS_API_KEY environment variable must be set. "
                "Please set it before starting the server."
            )
        return True


CONFIG = Config()
