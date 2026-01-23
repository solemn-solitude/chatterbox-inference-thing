"""HTTP/WebSocket client for TTS Inference."""

import requests
from typing import Iterator, Dict, Any, Optional
from urllib.parse import urljoin

from .base import TTSClient
from .exceptions import ConnectionError, AuthenticationError, RequestError, StreamingError
from .schemas import (
    TTSRequest, VoiceConfig, VoiceListResponse, 
    VoiceUploadResponse, VoiceDeleteResponse,
    HealthResponse, ReadyResponse
)


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
        
        request = TTSRequest(
            text=text,
            voice_mode=voice_mode,
            voice_config=voice_config,
            audio_format=audio_format,
            sample_rate=sample_rate,
            use_turbo=use_turbo
        )
        
        # Make streaming request
        url = urljoin(self.server_url, "/tts/synthesize")
        
        try:
            response = self.session.post(url, json=request.to_dict(), stream=True)
            
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
    
    def list_voices(self) -> VoiceListResponse:
        """List available voices.
        
        Returns:
            VoiceListResponse with typed voice information
        """
        url = urljoin(self.server_url, "/voices/list")
        
        try:
            response = self.session.get(url)
            
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("Invalid API key")
            elif response.status_code != 200:
                raise RequestError(f"HTTP {response.status_code}: {response.text}")
            
            return VoiceListResponse.from_dict(response.json())
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to list voices: {e}")
    
    def health_check(self) -> HealthResponse:
        """Check server health.
        
        Returns:
            HealthResponse with typed health status
        """
        url = urljoin(self.server_url, "/health")
        
        try:
            # Health endpoint doesn't require auth
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                raise RequestError(f"HTTP {response.status_code}")
            
            return HealthResponse.from_dict(response.json())
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Health check failed: {e}")
    
    def ready_check(self) -> ReadyResponse:
        """Check server readiness.
        
        Returns:
            ReadyResponse with typed readiness status
        """
        url = urljoin(self.server_url, "/ready")
        
        try:
            response = self.session.get(url, timeout=5)
            
            if response.status_code != 200:
                raise RequestError(f"HTTP {response.status_code}")
            
            return ReadyResponse.from_dict(response.json())
            
        except requests.exceptions.RequestException as e:
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
            
            return VoiceUploadResponse.from_dict(response.json())
            
        except FileNotFoundError:
            raise RequestError(f"Audio file not found: {audio_file_path}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to upload voice: {e}")
    
    def delete_voice(self, voice_id: str) -> VoiceDeleteResponse:
        """Delete a voice reference.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            VoiceDeleteResponse with typed deletion result
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
            
            return VoiceDeleteResponse.from_dict(response.json())
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to delete voice: {e}")
    
    def unload_model(self) -> Dict[str, Any]:
        """Manually unload TTS model from memory.
        
        Returns:
            Unload response dictionary
        """
        url = urljoin(self.server_url, "/model/unload")
        
        try:
            response = self.session.post(url)
            
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError("Invalid API key")
            elif response.status_code != 200:
                try:
                    error_data = response.json()
                    raise RequestError(error_data.get("detail", f"HTTP {response.status_code}"))
                except ValueError:
                    raise RequestError(f"HTTP {response.status_code}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to unload model: {e}")
    
    def close(self):
        """Close HTTP session."""
        if self.session:
            self.session.close()
