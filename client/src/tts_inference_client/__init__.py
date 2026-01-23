"""TTS Inference Client Library."""

from .base import TTSClient
from .zmq_client import ZMQClient
from .http_client import HTTPClient
from .exceptions import TTSClientError, ConnectionError, AuthenticationError

__version__ = "0.1.0"

__all__ = [
    "TTSClient",
    "ZMQClient",
    "HTTPClient",
    "TTSClientError",
    "ConnectionError",
    "AuthenticationError",
]


class Client:
    """Factory class for creating TTS clients."""
    
    @staticmethod
    def zmq(server_url: str, api_key: str) -> "ZMQClient":
        """Create a ZMQ client.
        
        Args:
            server_url: ZMQ server URL (e.g., "tcp://localhost:5555")
            api_key: API key for authentication
            
        Returns:
            ZMQ client instance
        """
        return ZMQClient(server_url, api_key)
    
    @staticmethod
    def http(server_url: str, api_key: str) -> "HTTPClient":
        """Create an HTTP client.
        
        Args:
            server_url: HTTP server URL (e.g., "http://localhost:20480")
            api_key: API key for authentication
            
        Returns:
            HTTP client instance
        """
        return HTTPClient(server_url, api_key)
