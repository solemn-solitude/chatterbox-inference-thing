"""ZMQ DEALER client for Chatterbox Inference."""

import json
import zmq
from typing import Iterator, Dict, Any, Optional

from .base import TTSClient
from .exceptions import ConnectionError, AuthenticationError, RequestError, StreamingError
from .schemas import (
    TTSRequest, VoiceConfig, VoiceListResponse, 
    VoiceUploadResponse, VoiceDeleteResponse,
    HealthResponse, ReadyResponse
)


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
        voice_config: Optional[VoiceConfig] = None,
        audio_format: str = "pcm",
        sample_rate: Optional[int] = None,
        use_turbo: bool = False,
    ) -> Iterator[bytes]:
        """Synthesize speech from text with streaming.
        
        Args:
            text: Text to synthesize
            voice_mode: "default" or "clone"
            voice_config: Voice configuration object (contains voice_name, voice_id, speed, exaggeration, cfg_weight, etc.)
            audio_format: "pcm" or "vorbis"
            sample_rate: Output sample rate
            use_turbo: Use ChatterboxTurboTTS instead of ChatterboxTTS
            
        Yields:
            Audio data chunks
        """
        # Use default voice_config if none provided
        if voice_config is None:
            voice_config = VoiceConfig()
        
        # Build request
        request = {
            "type": "synthesize",
            "api_key": self.api_key,
            "text": text,
            "voice_mode": voice_mode,
            "voice_config": voice_config.to_dict(),
            "audio_format": audio_format,
            "use_turbo": use_turbo,
        }
        
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
    
    def list_voices(self) -> VoiceListResponse:
        """List available voices.
        
        Returns:
            VoiceListResponse with typed voice information
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
                    return VoiceListResponse.from_dict(json.loads(data.decode('utf-8')))
            
            raise RequestError("Invalid response format")
            
        except zmq.ZMQError as e:
            raise ConnectionError(f"Failed to list voices: {e}")
    
    def health_check(self) -> HealthResponse:
        """Check server health.
        
        Returns:
            HealthResponse with typed health status
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
                    return HealthResponse.from_dict(json.loads(data.decode('utf-8')))
            
            raise RequestError("Invalid response format")
            
        except zmq.ZMQError as e:
            raise ConnectionError(f"Health check failed: {e}")
    
    def ready_check(self) -> ReadyResponse:
        """Check server readiness.
        
        Returns:
            ReadyResponse with typed readiness status
        """
        request = {
            "type": "ready",
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
                    return ReadyResponse.from_dict(json.loads(data.decode('utf-8')))
            
            raise RequestError("Invalid response format")
            
        except zmq.ZMQError as e:
            raise ConnectionError(f"Readiness check failed: {e}")
    
    def upload_voice(
        self,
        voice_id: str,
        audio_file_path: str,
        sample_rate: int
    ) -> VoiceUploadResponse:
        """Upload a voice reference file.
        
        Args:
            voice_id: Unique identifier for the voice
            audio_file_path: Path to WAV audio file
            sample_rate: Sample rate of the audio
            
        Returns:
            VoiceUploadResponse with typed upload result
        """
        import base64
        
        # Read audio file and encode to base64
        try:
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        except FileNotFoundError:
            raise RequestError(f"Audio file not found: {audio_file_path}")
        except Exception as e:
            raise RequestError(f"Failed to read audio file: {e}")
        
        request = {
            "type": "upload_voice",
            "api_key": self.api_key,
            "voice_id": voice_id,
            "sample_rate": sample_rate,
            "audio_data": audio_b64
        }
        
        try:
            self.socket.send_multipart([b"", json.dumps(request).encode('utf-8')])
            message = self.socket.recv_multipart()
            
            if len(message) >= 3:
                msg_type = message[1]
                data = message[2]
                
                if msg_type == b"error":
                    error_data = json.loads(data.decode('utf-8'))
                    error_msg = error_data.get("error", "Unknown error")
                    
                    if "already exists" in error_msg:
                        raise RequestError(f"Voice ID '{voice_id}' already exists")
                    raise RequestError(error_msg)
                elif msg_type == b"response":
                    return VoiceUploadResponse.from_dict(json.loads(data.decode('utf-8')))
            
            raise RequestError("Invalid response format")
            
        except zmq.ZMQError as e:
            raise ConnectionError(f"Failed to upload voice: {e}")
    
    def delete_voice(self, voice_id: str) -> VoiceDeleteResponse:
        """Delete a voice reference.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            VoiceDeleteResponse with typed deletion result
        """
        request = {
            "type": "delete_voice",
            "api_key": self.api_key,
            "voice_id": voice_id
        }
        
        try:
            self.socket.send_multipart([b"", json.dumps(request).encode('utf-8')])
            message = self.socket.recv_multipart()
            
            if len(message) >= 3:
                msg_type = message[1]
                data = message[2]
                
                if msg_type == b"error":
                    error_data = json.loads(data.decode('utf-8'))
                    error_msg = error_data.get("error", "Unknown error")
                    
                    if "not found" in error_msg:
                        raise RequestError(f"Voice '{voice_id}' not found")
                    raise RequestError(error_msg)
                elif msg_type == b"response":
                    return VoiceDeleteResponse.from_dict(json.loads(data.decode('utf-8')))
            
            raise RequestError("Invalid response format")
            
        except zmq.ZMQError as e:
            raise ConnectionError(f"Failed to delete voice: {e}")
    
    def unload_model(self) -> Dict[str, Any]:
        """Manually unload TTS model from memory.
        
        Returns:
            Unload response dictionary
        """
        request = {
            "type": "model_unload",
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
            raise ConnectionError(f"Failed to unload model: {e}")
    
    def close(self):
        """Close ZMQ connection."""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
