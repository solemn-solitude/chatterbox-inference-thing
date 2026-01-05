"""ZMQ ROUTER server for TTS streaming."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
import zmq
import zmq.asyncio

from ..models import TTSRequest, VoiceDatabase
from ..auth import verify_api_key_zmq
from ..tts import tts_engine, VoiceManager
from ..utils.config import config
from ..utils.audio_utils import AudioStreamEncoder

logger = logging.getLogger(__name__)


class ZMQServer:
    """ZMQ ROUTER server for TTS streaming."""
    
    def __init__(self, host: str = "*", port: int = 5555):
        """Initialize ZMQ server.
        
        Args:
            host: Host to bind to ("*" for all interfaces)
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None
        self.running = False
        
        # Server components
        self.db: Optional[VoiceDatabase] = None
        self.voice_manager: Optional[VoiceManager] = None
    
    async def initialize(self):
        """Initialize server components."""
        logger.info("Initializing ZMQ server components...")
        
        # Validate API key
        try:
            config.validate_api_key()
        except ValueError as e:
            logger.error(str(e))
            raise
        
        # Ensure directories exist
        config.ensure_directories()
        
        # Initialize database
        self.db = VoiceDatabase(config.database_path)
        await self.db.initialize()
        
        # Initialize voice manager
        self.voice_manager = VoiceManager(self.db)
        
        # Initialize TTS engine
        await tts_engine.initialize()
        
        logger.info("ZMQ server components initialized")
    
    async def start(self):
        """Start the ZMQ ROUTER server."""
        await self.initialize()
        
        # Create ZMQ context and socket
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        
        # Bind socket
        bind_address = f"tcp://{self.host}:{self.port}"
        self.socket.bind(bind_address)
        logger.info(f"ZMQ ROUTER server listening on {bind_address}")
        
        self.running = True
        
        # Main server loop
        try:
            while self.running:
                try:
                    # Receive multi-part message
                    # Format: [client_identity, b"", request_json]
                    message = await self.socket.recv_multipart()
                    
                    if len(message) < 3:
                        logger.warning(f"Invalid message format: expected at least 3 parts, got {len(message)}")
                        continue
                    
                    client_id = message[0]
                    delimiter = message[1]
                    request_data = message[2]
                    
                    # Process request in background
                    asyncio.create_task(self._handle_request(client_id, request_data))
                    
                except zmq.ZMQError as e:
                    if self.running:
                        logger.error(f"ZMQ error: {e}")
                    else:
                        break
                except Exception as e:
                    logger.error(f"Error in server loop: {e}", exc_info=True)
                    
        finally:
            await self.stop()
    
    async def _handle_request(self, client_id: bytes, request_data: bytes):
        """Handle a single client request.
        
        Args:
            client_id: Client identity
            request_data: JSON request data
        """
        try:
            # Parse request
            request_dict = json.loads(request_data.decode('utf-8'))
            
            # Verify API key
            api_key = request_dict.get("api_key")
            if not verify_api_key_zmq(api_key):
                await self._send_error(client_id, "Invalid or missing API key")
                return
            
            # Determine request type
            request_type = request_dict.get("type", "synthesize")
            
            if request_type == "synthesize":
                await self._handle_synthesize(client_id, request_dict)
            elif request_type == "list_voices":
                await self._handle_list_voices(client_id)
            elif request_type == "health":
                await self._handle_health(client_id)
            else:
                await self._send_error(client_id, f"Unknown request type: {request_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            await self._send_error(client_id, "Invalid JSON")
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            await self._send_error(client_id, str(e))
    
    async def _handle_synthesize(self, client_id: bytes, request_dict: Dict[str, Any]):
        """Handle TTS synthesis request.
        
        Args:
            client_id: Client identity
            request_dict: Request dictionary
        """
        try:
            # Remove api_key and type from request
            request_dict.pop("api_key", None)
            request_dict.pop("type", None)
            
            # Parse TTS request
            request = TTSRequest(**request_dict)
            
            logger.info(f"TTS synthesis request from client {client_id.hex()[:8]}: mode={request.voice_mode}")
            
            # Load voice reference if needed
            voice_reference = None
            if request.voice_mode == "clone":
                voice_reference = await self.voice_manager.load_voice_reference(request.voice_config.voice_id)
                if voice_reference is None:
                    await self._send_error(client_id, f"Voice not found: {request.voice_config.voice_id}")
                    return
            
            # Create encoder
            output_sr = request.sample_rate or tts_engine.sample_rate
            encoder = AudioStreamEncoder(request.audio_format, output_sr)
            
            # Send metadata first
            metadata = {
                "status": "streaming",
                "sample_rate": output_sr,
                "audio_format": request.audio_format
            }
            await self._send_message(client_id, b"metadata", json.dumps(metadata).encode('utf-8'))
            
            # Stream audio chunks
            chunk_count = 0
            try:
                async for audio_chunk, sample_rate in tts_engine.synthesize_streaming(
                    text=request.text,
                    voice_mode=request.voice_mode,
                    voice_reference=voice_reference,
                    voice_name=request.voice_config.voice_name,
                    speed=request.voice_config.speed,
                    sample_rate=request.sample_rate,
                ):
                    # Encode chunk
                    encoded_chunk = encoder.encode_chunk(audio_chunk)
                    
                    # Send audio chunk
                    await self._send_message(client_id, b"audio", encoded_chunk)
                    chunk_count += 1
                
                # Send completion message
                completion = {"status": "complete", "chunks": chunk_count}
                await self._send_message(client_id, b"complete", json.dumps(completion).encode('utf-8'))
                
                logger.info(f"TTS synthesis complete for client {client_id.hex()[:8]}: {chunk_count} chunks sent")
                
            except Exception as e:
                logger.error(f"Error during TTS synthesis: {e}")
                await self._send_error(client_id, f"TTS synthesis failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in synthesize handler: {e}")
            await self._send_error(client_id, str(e))
    
    async def _handle_list_voices(self, client_id: bytes):
        """Handle list voices request.
        
        Args:
            client_id: Client identity
        """
        try:
            voices_data = await self.db.list_voices()
            response = {
                "status": "success",
                "voices": voices_data,
                "total": len(voices_data)
            }
            await self._send_message(client_id, b"response", json.dumps(response).encode('utf-8'))
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            await self._send_error(client_id, str(e))
    
    async def _handle_health(self, client_id: bytes):
        """Handle health check request.
        
        Args:
            client_id: Client identity
        """
        response = {
            "status": "healthy",
            "model_loaded": tts_engine.is_loaded(),
            "version": "0.1.0"
        }
        await self._send_message(client_id, b"response", json.dumps(response).encode('utf-8'))
    
    async def _send_message(self, client_id: bytes, msg_type: bytes, data: bytes):
        """Send a message to a client.
        
        Args:
            client_id: Client identity
            msg_type: Message type (metadata, audio, complete, response, error)
            data: Message data
        """
        # ZMQ ROUTER format: [client_id, b"", msg_type, data]
        await self.socket.send_multipart([client_id, b"", msg_type, data])
    
    async def _send_error(self, client_id: bytes, error_msg: str):
        """Send an error message to a client.
        
        Args:
            client_id: Client identity
            error_msg: Error message
        """
        error_data = {"error": error_msg}
        await self._send_message(client_id, b"error", json.dumps(error_data).encode('utf-8'))
    
    async def stop(self):
        """Stop the ZMQ server."""
        logger.info("Stopping ZMQ server...")
        self.running = False
        
        if self.socket:
            self.socket.close()
        
        if self.context:
            self.context.term()
        
        logger.info("ZMQ server stopped")


async def run_zmq_server(host: str = "*", port: int = 5555):
    """Run the ZMQ server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
    """
    server = ZMQServer(host, port)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        await server.stop()
