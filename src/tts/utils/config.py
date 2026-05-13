"""Configuration management for TTS Inference."""

import os
import sqlite3
from pathlib import Path


def _ai_network_home() -> Path:
    xdg = os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "ai-network"


AI_NETWORK_HOME = _ai_network_home()


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


def _cfg(key: str, default: str = "") -> str:
    """Read a value from the central config.db. Returns default if DB absent or key missing."""
    db_path = AI_NETWORK_HOME / "config.db"
    if not db_path.exists():
        return default
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT value FROM service_config WHERE service='tts' AND key=?", (key,)
        ).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


class Config:
    """Global configuration for TTS Inference.

    Priority: env var > config.db > hardcoded default.
    """

    def __init__(self):
        self.tts_engine = _env("TTS_ENGINE") or _cfg("engine", "chatterbox")

        self.voice_dir = Path(
            _env("TTS_VOICE_DIR", "CHATTERBOX_VOICE_DIR",
                 str(AI_NETWORK_HOME / "tts"))
        )
        self.voice_audio_dir = self.voice_dir / "voices"
        self.database_path = self.voice_dir / "voices.db"

        self.api_key = _env("TTS_API_KEY", "CHATTERBOX_API_KEY")
        self.default_voice_id = _env("TTS_DEFAULT_VOICE_ID", "CHATTERBOX_DEFAULT_VOICE_ID")

        self.fastapi_host = _env("TTS_FASTAPI_HOST", "CHATTERBOX_FASTAPI_HOST", "0.0.0.0")
        self.fastapi_port = int(_env("TTS_FASTAPI_PORT", "CHATTERBOX_FASTAPI_PORT", "20480"))

        self.zmq_input_address = _env("TTS_INPUT_ADDRESS") or _cfg("input_address", "tcp://*:20501")
        self.zmq_pub_address = _env("TTS_PUB_ADDRESS") or _cfg("pub_address", "tcp://*:20502")

        self.log_level = _env("TTS_LOG_LEVEL", "CHATTERBOX_LOG_LEVEL", "INFO")

        self.offload_timeout = int(_env("TTS_OFFLOAD_TIMEOUT", "CHATTERBOX_OFFLOAD_TIMEOUT")
                                   or _cfg("offload_timeout", "600"))
        keep_warm_str = _env("TTS_KEEP_WARM", "CHATTERBOX_KEEP_WARM") or _cfg("keep_warm", "false")
        self.keep_warm = keep_warm_str.lower() in ("true", "1", "yes")

        fish_speech_checkpoint = _env("FISH_SPEECH_CHECKPOINT_PATH", default="checkpoints/openaudio-s1-mini")
        self.fish_speech_checkpoint_path = fish_speech_checkpoint
        self.fish_speech_decoder_path = _env(
            "FISH_SPEECH_DECODER_PATH",
            default=f"{fish_speech_checkpoint}/codec.pth",
        )

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
