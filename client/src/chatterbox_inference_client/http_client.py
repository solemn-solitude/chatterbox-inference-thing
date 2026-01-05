"""HTTP/WebSocket client for Chatterbox Inference."""

import json
import requests
from typing import Iterator, Dict, Any, Optional
from urllib.parse import urljoin

from .base import TTSClient
from .exceptions import ConnectionError, AuthenticationError, RequestError, StreamingError


class HTTPClient(TTSClient):
    """HTTP/REST client for TTS streaming."""
    
    def __init__(self, server_url: str, api_key: str):
        """Initialize HTTP client.
        
        Args:
            server_url: HTTP server URL (e.g., "http://localhost:20480")
            api_key: API key for authentication
        """
        super().__init__(server_url, api_key)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
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
        request_data = {
            "text": text,
            "voice_mode": voice_mode,
            "voice_config": {
                "speed": speed
            },
            "audio_format": audio_format,
            "use_turbo": use_turbo,
        }
        
        if voice_name:
            request_data["voice_config"]["voice_name"] = voice_name
        if voice_id:
            request_data["voice_config"]["voice_id"] = voice_id
        if sample_rate:
            request_data["sample_rate"] = sample_rate
        
        # Make streaming request
        url = urljoin(self.server_url, "/tts/synthesize")
        
        try:
            response = self.session.post(url, json=request_data, stream=True)
            
            # Check for errors
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 404:
                raise RequestError(f"Voice not found")
            elif response.status_code != 200:
                try:
                    error_data = response.json()
                    raise RequestError(error_data.get("detail", f"HTTP {response.status_code}"))
                except ValueError:
                    raise RequestError(f"HTTP {response.status_code}: {response.text}")
            
            # Stream chunks
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk
                    
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to server: {e}")
        except requests.exceptions.Timeout as e:
            raise StreamingError(f"Request timeout: {e}")
        except requests.exceptions.RequestException as e:
            raise RequestError(f"Request failed: {e}")
    
    def list_voices(self) -> Dict[str, Any]:
        """List available voices.
        
        Returns:
            Dictionary with voices information
        """
        url = urljoin(self.server_url, "/voices/list")
        
        try:
            response = self.session.get(url)
            
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("Invalid API key")
            elif response.status_code != 200:
                raise RequestError(f"HTTP {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to list voices: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check server health.
        
        Returns:
            Health status dictionary
        """
        url = urljoin(self.server_url, "/health")
        
        try:
            # Health endpoint doesn't require auth
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                raise RequestError(f"HTTP {response.status_code}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Health check failed: {e}")
    
    def upload_voice(
        self,
        voice_id: str,
        audio_file_path: str,
        sample_rate: int
    ) -> Dict[str, Any]:
        """Upload a voice reference file.
        
        Args:
            voice_id: Unique identifier for the voice
            audio_file_path: Path to WAV audio file
            sample_rate: Sample rate of the audio
            
        Returns:
            Upload response dictionary
        """
        url = urljoin(self.server_url, "/voices/upload")
        
        try:
            with open(audio_file_path, 'rb') as f:
                files = {'audio_file': (f"{voice_id}.wav", f, 'audio/wav')}
                data = {
                    'voice_id': voice_id,
                    'sample_rate': sample_rate
                }
                
                # Remove Content-Type header for multipart/form-data
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(url, files=files, data=data, headers=headers)
            
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 409:
                raise RequestError(f"Voice ID '{voice_id}' already exists")
            elif response.status_code != 200:
                try:
                    error_data = response.json()
                    raise RequestError(error_data.get("detail", f"HTTP {response.status_code}"))
                except ValueError:
                    raise RequestError(f"HTTP {response.status_code}")
            
            return response.json()
            
        except FileNotFoundError:
            raise RequestError(f"Audio file not found: {audio_file_path}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to upload voice: {e}")
    
    def delete_voice(self, voice_id: str) -> Dict[str, Any]:
        """Delete a voice reference.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            Deletion response dictionary
        """
        url = urljoin(self.server_url, f"/voices/{voice_id}")
        
        try:
            response = self.session.delete(url)
            
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 404:
                raise RequestError(f"Voice '{voice_id}' not found")
            elif response.status_code != 200:
                raise RequestError(f"HTTP {response.status_code}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to delete voice: {e}")
    
    def close(self):
        """Close HTTP session."""
        if self.session:
            self.session.close()
