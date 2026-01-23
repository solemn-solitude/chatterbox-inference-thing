"""Exceptions for TTS Inference Client."""


class TTSClientError(Exception):
    """Base exception for TTS client errors."""
    pass


class ConnectionError(TTSClientError):
    """Error connecting to server."""
    pass


class AuthenticationError(TTSClientError):
    """Authentication failed."""
    pass


class RequestError(TTSClientError):
    """Error in request processing."""
    pass


class StreamingError(TTSClientError):
    """Error during audio streaming."""
    pass
