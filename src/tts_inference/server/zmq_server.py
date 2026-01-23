"""ZMQ ROUTER server for TTS streaming."""

import asyncio
import json
import logging
from typing import Optional
import zmq
import zmq.asyncio

from ..models import VoiceDatabase
from ..auth import verify_api_key_zmq
from ..tts import get_tts_engine, VoiceManager
from ..services import VoiceService
from ..utils.config import CONFIG
from .zmq_routes import (
    handle_synthesize,
    handle_list_voices,
    handle_upload_voice,
    handle_delete_voice,
    handle_health,
    handle_ready,
    handle_model_unload
)

logger = logging.getLogger(__name__)


class ZMQServer:
    """ZMQ ROUTER server for TTS streaming."""
    
    def __init__(self, input_address: str = "tcp://localhost:20501", enable_pub: bool = False, pub_address: str = ""):
        """Initialize ZMQ server.
        
        Args:
            input_address: Address to bind the input ROUTER socket to
            enable_pub: Whether to enable PUB socket for broadcasting
            pub_address: Address to bind the PUB socket to (required if enable_pub is True)
        """
        self.input_address = input_address
        self.enable_pub = enable_pub
        self.pub_address = pub_address
        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None
        self.pub_socket: Optional[zmq.asyncio.Socket] = None
        self.running = False
        
        # Server components
        self.db: Optional[VoiceDatabase] = None
        self.voice_manager: Optional[VoiceManager] = None
        self.voice_service: Optional[VoiceService] = None
    
    async def initialize(self):
        """Initialize server components."""
        logger.info("Initializing ZMQ server components...")
        
        # Validate API key
        try:
            CONFIG.validate_api_key()
        except ValueError as e:
            logger.error(str(e))
            raise
        
        # Ensure directories exist
        CONFIG.ensure_directories()
        
        # Initialize database
        self.db = VoiceDatabase(CONFIG.database_path)
        await self.db.initialize()
        
        # Initialize voice manager
        self.voice_manager = VoiceManager(self.db)
        
        # Initialize voice service
        self.voice_service = VoiceService(self.voice_manager, self.db)
        
        # Initialize TTS engine (with config settings)
        tts_engine = get_tts_engine()
        await tts_engine.initialize()
        
        logger.info("ZMQ server components initialized")
    
    async def start(self):
        """Start the ZMQ ROUTER server."""
        await self.initialize()
        
        # Create ZMQ context and socket
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        
        # Bind input socket
        self.socket.bind(self.input_address)
        logger.info(f"ZMQ ROUTER server listening on {self.input_address}")
        
        # Optionally create and bind PUB socket
        if self.enable_pub:
            if not self.pub_address:
                logger.error("PUB socket enabled but no address provided")
                raise ValueError("TTS_PUB_ADDRESS must be set when using --enable-pub")
            
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(self.pub_address)
            logger.info(f"ZMQ PUB socket broadcasting on {self.pub_address}")
        
        self.running = True
        
        # Main server loop
        try:
            while self.running:
                try:
                    # Receive multi-part message
                    # ROUTER messages come as: [identity_frame(s)..., message_data]
                    frames = await self.socket.recv_multipart()
                    
                    if len(frames) < 2:
                        logger.warning(f"Invalid message format: expected at least 2 parts, got {len(frames)}")
                        continue
                    
                    # Log frame details for debugging
                    logger.debug(f"Received {len(frames)} frames: {[len(f) for f in frames]}")
                    
                    # Extract identity frames (all except last frame) and message data (last frame)
                    identity_frames = frames[:-1]
                    request_data = frames[-1]
                    
                    # Process request in background
                    asyncio.create_task(self._handle_request(identity_frames, request_data))
                    
                except zmq.ZMQError as e:
                    if self.running:
                        logger.error(f"ZMQ error: {e}")
                    else:
                        break
                except Exception as e:
                    logger.error(f"Error in server loop: {e}", exc_info=True)
                    
        finally:
            await self.stop()
    
    async def _handle_request(self, identity_frames: list, request_data: bytes):
        """Handle a single client request.
        
        Args:
            identity_frames: List of identity frames from ROUTER
            request_data: The actual request data (JSON or plain text)
        """
        try:
            # Check if request_data is empty or just whitespace
            if not request_data or not request_data.strip():
                logger.error(f"Empty request data received. Frames: {len(identity_frames) + 1}")
                await self._send_error(identity_frames, "Empty request data")
                return
            
            # Try to parse as JSON first
            try:
                request_dict = json.loads(request_data.decode('utf-8'))
            except json.JSONDecodeError:
                # Not JSON - treat as plain text to synthesize
                logger.info(f"Received plain text message ({len(request_data)} bytes)")
                text = request_data.decode('utf-8')
                
                # Create a synthesize request from the plain text
                # TODO: Make voice settings configurable via environment variables
                # Currently using hardcoded "peaches4" voice as placeholder
                request_dict = {
                    "text": text,
                    "voice_mode": "clone",
                    "audio_format": "pcm",  # Changed from "vorbis" to "pcm" for raw audio streaming
                    "voice_config": {
                        "voice_id": "solar",  # TODO: Make this configurable
                        "speed": 1.0,
                        "exaggeration": 0.15,
                        "cfg_weight": 1
                    },
                    "use_turbo": False
                }
                
                # Handle synthesis without API key check for plain text (internal messages)
                await handle_synthesize(identity_frames, request_dict, self.voice_service, self._send_message)
                return
            
            # Verify API key
            api_key = request_dict.get("api_key")
            if not verify_api_key_zmq(api_key):
                await self._send_error(identity_frames, "Invalid or missing API key")
                return
            
            # Remove api_key from request
            request_dict.pop("api_key", None)
            
            # Determine request type
            request_type = request_dict.pop("type", "synthesize")
            
            # Route to appropriate handler
            if request_type == "synthesize":
                await handle_synthesize(identity_frames, request_dict, self.voice_service, self._send_message)
            elif request_type == "list_voices":
                await handle_list_voices(identity_frames, self.voice_service, self._send_message)
            elif request_type == "upload_voice":
                await handle_upload_voice(identity_frames, request_dict, self.voice_service, self._send_message)
            elif request_type == "delete_voice":
                await handle_delete_voice(identity_frames, request_dict, self.voice_service, self._send_message)
            elif request_type == "health":
                await handle_health(identity_frames, self._send_message)
            elif request_type == "ready":
                await handle_ready(identity_frames, self._send_message)
            elif request_type == "model_unload":
                await handle_model_unload(identity_frames, self._send_message)
            else:
                await self._send_error(identity_frames, f"Unknown request type: {request_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            logger.error(f"Request data (first 200 bytes): {request_data[:200]}")
            logger.error(f"Identity frames count: {len(identity_frames)}, sizes: {[len(f) for f in identity_frames]}")
            await self._send_error(identity_frames, "Invalid JSON")
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            await self._send_error(identity_frames, str(e))
    
    async def _send_message(self, identity_frames: list, msg_type: bytes, data: bytes):
        """Send a message to a client or broadcast via PUB socket.
        
        Args:
            identity_frames: List of identity frames from ROUTER (for routing back to client)
            msg_type: Message type identifier
            data: Message payload
        """
        if self.enable_pub:
            # When PUB is enabled, only broadcast (don't send back via ROUTER)
            await self.pub_socket.send_multipart([msg_type, data])
        else:
            # Normal ROUTER response: identity_frames + [msg_type, data]
            await self.socket.send_multipart(identity_frames + [msg_type, data])
    
    async def _send_error(self, identity_frames: list, error_msg: str):
        """Send an error message to a client.
        
        Args:
            identity_frames: List of identity frames from ROUTER
            error_msg: Error message to send
        """
        error_data = {"error": error_msg}
        await self._send_message(identity_frames, b"error", json.dumps(error_data).encode('utf-8'))
    
    async def stop(self):
        """Stop the ZMQ server."""
        logger.info("Stopping ZMQ server...")
        self.running = False
        
        if self.socket:
            self.socket.close()
        
        if self.pub_socket:
            self.pub_socket.close()
        
        if self.context:
            self.context.term()
        
        logger.info("ZMQ server stopped")


async def run_zmq_server(input_address: str = "tcp://localhost:20501", enable_pub: bool = False, pub_address: str = ""):
    """Run the ZMQ server.
    
    Args:
        input_address: Address to bind the input ROUTER socket to
        enable_pub: Whether to enable PUB socket for broadcasting
        pub_address: Address to bind the PUB socket to
    """
    server = ZMQServer(input_address, enable_pub, pub_address)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        await server.stop()
