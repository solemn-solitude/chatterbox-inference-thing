"""Configuration management for TTS Inference."""

import os
from pathlib import Path


class Config:
    """Global configuration for TTS Inference."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Voice storage directory
        self.voice_dir = Path(
            os.getenv(
                "CHATTERBOX_VOICE_DIR",
                os.path.expanduser("~/.local/share/tts-inference")
            )
        )
        self.voice_audio_dir = self.voice_dir / "voices"
        self.database_path = self.voice_dir / "voices.db"
        
        # API Key
        self.api_key = os.getenv("CHATTERBOX_API_KEY", "")

        # Default voice used when no voice_id is provided in a request
        self.default_voice_id = os.getenv("CHATTERBOX_DEFAULT_VOICE_ID", "")
        
        # Server settings
        self.fastapi_host = os.getenv("CHATTERBOX_FASTAPI_HOST", "0.0.0.0")
        self.fastapi_port = int(os.getenv("CHATTERBOX_FASTAPI_PORT", "20480"))
        
        # ZMQ settings
        self.zmq_input_address = os.getenv("TTS_INPUT_ADDRESS", "tcp://*:20501")
        self.zmq_pub_address = os.getenv("TTS_PUB_ADDRESS", "")
        
        # Logging
        self.log_level = os.getenv("CHATTERBOX_LOG_LEVEL", "INFO")
        
        # Model offloading settings
        self.offload_timeout = int(os.getenv("CHATTERBOX_OFFLOAD_TIMEOUT", "600"))  # 10 minutes default
        self.keep_warm = os.getenv("CHATTERBOX_KEEP_WARM", "false").lower() in ("true", "1", "yes")
        
    def ensure_directories(self):
        """Ensure required directories exist."""
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.voice_audio_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_api_key(self) -> bool:
        """Validate that API key is configured."""
        if not self.api_key:
            raise ValueError(
                "CHATTERBOX_API_KEY environment variable must be set. "
                "Please set it before starting the server."
            )
        return True


# Global config instance
CONFIG = Config()
