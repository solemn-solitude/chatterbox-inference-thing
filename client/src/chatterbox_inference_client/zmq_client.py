"""ZMQ DEALER client for Chatterbox Inference."""

import json
import zmq
from typing import Iterator, Dict, Any, Optional

from .base import TTSClient
from .exceptions import ConnectionError, AuthenticationError, RequestError, StreamingError


class ZMQClient(TTSClient):
    """ZMQ DEALER client for TTS streaming."""
    
    def __init__(self, server_url: str, api_key: str):
        """Initialize ZMQ client.
        
        Args:
            server_url: ZMQ server URL (e.g., "tcp://localhost:5555")
            api_key: API key for authentication
        """
        super().__init__(server_url, api_key)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        
        try:
            self.socket.connect(server_url)
            # Set socket timeout
            self.socket.setsockopt(zmq.RCVTIMEO, 30000)  # 30 seconds
            self.socket.setsockopt(zmq.SNDTIMEO, 5000)   # 5 seconds
        except zmq.ZMQError as e:
            raise ConnectionError(f"Failed to connect to {server_url}: {e}")
    
    def synthesize(
        self,
        text: str,
        voice_mode: str = "default",
        voice_name: Optional[str] = None,
        voice_id: Optional[str] = None,
        audio_format: str = "pcm",
        sample_rate: Optional[int] = None,
        speed: float = 1.0,
        use_turbo: bool = False,
    ) -> Iterator[bytes]:
        """Synthesize speech from text with streaming.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_name: Name of default voice (for default mode)
            voice_id: ID of cloned voice (for clone mode)
            audio_format: "pcm" or "vorbis"
            sample_rate: Output sample rate
            speed: Speech speed multiplier
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            
        Yields:
            Audio data chunks
        """
        # Build request
        request = {
            "type": "synthesize",
            "api_key": self.api_key,
            "text": text,
            "voice_mode": voice_mode,
            "voice_config": {
                "speed": speed
            },
            "audio_format": audio_format,
            "use_turbo": use_turbo,
        }
        
        if voice_name:
            request["voice_config"]["voice_name"] = voice_name
        if voice_id:
            request["voice_config"]["voice_id"] = voice_id
        if sample_rate:
            request["sample_rate"] = sample_rate
        
        # Send request
        # DEALER format: [b"", request_json]
        try:
            self.socket.send_multipart([b"", json.dumps(request).encode('utf-8')])
        except zmq.ZMQError as e:
            raise ConnectionError(f"Failed to send request: {e}")
        
        # Receive response
        metadata_received = False
        
        while True:
            try:
                # Receive multi-part message
                # Format: [b"", msg_type, data]
                message = self.socket.recv_multipart()
                
                if len(message) < 3:
                    raise StreamingError(f"Invalid message format: {len(message)} parts")
                
                delimiter = message[0]
                msg_type = message[1]
                data = message[2]
                
                if msg_type == b"error":
                    error_data = json.loads(data.decode('utf-8'))
                    error_msg = error_data.get("error", "Unknown error")
                    
                    if "Invalid" in error_msg and "API key" in error_msg:
                        raise AuthenticationError(error_msg)
                    else:
                        raise RequestError(error_msg)
                
                elif msg_type == b"metadata":
                    # Metadata message
                    metadata = json.loads(data.decode('utf-8'))
                    metadata_received = True
                    # Continue to receive audio chunks
                
                elif msg_type == b"audio":
                    # Audio chunk
                    if not metadata_received:
                        raise StreamingError("Received audio before metadata")
                    yield data
                
                elif msg_type == b"complete":
                    # Completion message
                    completion = json.loads(data.decode('utf-8'))
                    break
                
                else:
                    raise StreamingError(f"Unknown message type: {msg_type}")
                    
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    raise StreamingError("Timeout waiting for response")
                else:
                    raise ConnectionError(f"ZMQ error: {e}")
    
    def list_voices(self) -> Dict[str, Any]:
        """List available voices.
        
        Returns:
            Dictionary with voices information
        """
        request = {
            "type": "list_voices",
            "api_key": self.api_key
        }
        
        try:
            self.socket.send_multipart([b"", json.dumps(request).encode('utf-8')])
            message = self.socket.recv_multipart()
            
            if len(message) >= 3:
                msg_type = message[1]
                data = message[2]
                
                if msg_type == b"error":
                    error_data = json.loads(data.decode('utf-8'))
                    raise RequestError(error_data.get("error", "Unknown error"))
                elif msg_type == b"response":
                    return json.loads(data.decode('utf-8'))
            
            raise RequestError("Invalid response format")
            
        except zmq.ZMQError as e:
            raise ConnectionError(f"Failed to list voices: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check server health.
        
        Returns:
            Health status dictionary
        """
        request = {
            "type": "health",
            "api_key": self.api_key
        }
        
        try:
            self.socket.send_multipart([b"", json.dumps(request).encode('utf-8')])
            message = self.socket.recv_multipart()
            
            if len(message) >= 3:
                msg_type = message[1]
                data = message[2]
                
                if msg_type == b"error":
                    error_data = json.loads(data.decode('utf-8'))
                    raise RequestError(error_data.get("error", "Unknown error"))
                elif msg_type == b"response":
                    return json.loads(data.decode('utf-8'))
            
            raise RequestError("Invalid response format")
            
        except zmq.ZMQError as e:
            raise ConnectionError(f"Health check failed: {e}")
    
    def close(self):
        """Close ZMQ connection."""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
