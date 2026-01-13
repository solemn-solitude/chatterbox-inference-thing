"""TTS module for Chatterbox Inference."""

from .engine import TTSEngine, tts_engine, get_tts_engine
from .voice_manager import VoiceManager

__all__ = ["TTSEngine", "tts_engine", "get_tts_engine", "VoiceManager"]
