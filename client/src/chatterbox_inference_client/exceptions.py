"""Exceptions for Chatterbox Inference Client."""


class ChatterboxClientError(Exception):
    """Base exception for Chatterbox client errors."""
    pass


class ConnectionError(ChatterboxClientError):
    """Error connecting to server."""
    pass


class AuthenticationError(ChatterboxClientError):
    """Authentication failed."""
    pass


class RequestError(ChatterboxClientError):
    """Error in request processing."""
    pass


class StreamingError(ChatterboxClientError):
    """Error during audio streaming."""
    pass
