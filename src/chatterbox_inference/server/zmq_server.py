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
    
    def __init__(self, host: str = "*", port: int = 5555):
        """Initialize ZMQ server."""
        self.host = host
        self.port = port
        self.context: Optional[zmq.asyncio.Context] = None
        self.socket: Optional[zmq.asyncio.Socket] = None
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
                    message = await self.socket.recv_multipart()
                    
                    if len(message) < 3:
                        logger.warning(f"Invalid message format: expected at least 3 parts, got {len(message)}")
                        continue
                    
                    client_id = message[0]
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
        """Handle a single client request."""
        try:
            # Parse request
            request_dict = json.loads(request_data.decode('utf-8'))
            
            # Verify API key
            api_key = request_dict.get("api_key")
            if not verify_api_key_zmq(api_key):
                await self._send_error(client_id, "Invalid or missing API key")
                return
            
            # Remove api_key from request
            request_dict.pop("api_key", None)
            
            # Determine request type
            request_type = request_dict.pop("type", "synthesize")
            
            # Route to appropriate handler
            if request_type == "synthesize":
                await handle_synthesize(client_id, request_dict, self.voice_service, self._send_message)
            elif request_type == "list_voices":
                await handle_list_voices(client_id, self.voice_service, self._send_message)
            elif request_type == "upload_voice":
                await handle_upload_voice(client_id, request_dict, self.voice_service, self._send_message)
            elif request_type == "delete_voice":
                await handle_delete_voice(client_id, request_dict, self.voice_service, self._send_message)
            elif request_type == "health":
                await handle_health(client_id, self._send_message)
            elif request_type == "ready":
                await handle_ready(client_id, self._send_message)
            elif request_type == "model_unload":
                await handle_model_unload(client_id, self._send_message)
            else:
                await self._send_error(client_id, f"Unknown request type: {request_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            await self._send_error(client_id, "Invalid JSON")
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            await self._send_error(client_id, str(e))
    
    async def _send_message(self, client_id: bytes, msg_type: bytes, data: bytes):
        """Send a message to a client."""
        await self.socket.send_multipart([client_id, b"", msg_type, data])
    
    async def _send_error(self, client_id: bytes, error_msg: str):
        """Send an error message to a client."""
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
    """Run the ZMQ server."""
    server = ZMQServer(host, port)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        await server.stop()
