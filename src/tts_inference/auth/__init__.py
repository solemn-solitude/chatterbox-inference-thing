"""Authentication module for TTS Inference."""

from .api_key import verify_api_key, verify_api_key_zmq

__all__ = ["verify_api_key", "verify_api_key_zmq"]
