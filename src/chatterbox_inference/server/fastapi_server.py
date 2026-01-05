"""FastAPI server for TTS streaming."""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncIterator

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ..models import (
    TTSRequest, VoiceInfo, VoiceListResponse, VoiceUploadResponse,
    VoiceDeleteResponse, HealthResponse, ReadyResponse, ErrorResponse,
    VoiceDatabase
)
from ..auth import verify_api_key
from ..tts import tts_engine, VoiceManager
from ..utils.config import config
from ..utils.audio_utils import AudioStreamEncoder

logger = logging.getLogger(__name__)

# Global instances
db: VoiceDatabase = None
voice_manager: VoiceManager = None
app = FastAPI(
    title="Chatterbox Inference Server",
    description="TTS inference server with streaming support",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize server components on startup."""
    global db, voice_manager
    
    logger.info("Starting Chatterbox Inference FastAPI server...")
    
    # Validate API key is configured
    try:
        config.validate_api_key()
    except ValueError as e:
        logger.error(str(e))
        raise
    
    # Ensure directories exist
    config.ensure_directories()
    
    # Initialize database
    db = VoiceDatabase(config.database_path)
    await db.initialize()
    
    # Initialize voice manager
    voice_manager = VoiceManager(db)
    
    # Initialize TTS engine
    await tts_engine.initialize()
    
    logger.info("FastAPI server initialization complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown."""
    logger.info("Shutting down FastAPI server...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/ready", response_model=ReadyResponse)
async def readiness_check():
    """Readiness check endpoint."""
    model_loaded = tts_engine.is_loaded()
    voice_dir_accessible = config.voice_audio_dir.exists()
    database_accessible = config.database_path.exists()
    
    ready = model_loaded and voice_dir_accessible and database_accessible
    
    return ReadyResponse(
        ready=ready,
        model_loaded=model_loaded,
        voice_dir_accessible=voice_dir_accessible,
        database_accessible=database_accessible
    )


@app.post("/tts/synthesize")
async def synthesize_tts(
    request: TTSRequest,
    api_key: str = Depends(verify_api_key)
) -> StreamingResponse:
    """Synthesize TTS with streaming response.
    
    Args:
        request: TTS synthesis request
        api_key: Verified API key
        
    Returns:
        Streaming audio response
    """
    logger.info(f"TTS request: mode={request.voice_mode}, format={request.audio_format}")
    
    # Load voice reference if in clone mode
    voice_reference = None
    if request.voice_mode == "clone":
        voice_reference = await voice_manager.load_voice_reference(request.voice_config.voice_id)
        if voice_reference is None:
            raise HTTPException(status_code=404, detail=f"Voice not found: {request.voice_config.voice_id}")
    
    # Create audio encoder
    output_sr = request.sample_rate or tts_engine.sample_rate
    encoder = AudioStreamEncoder(request.audio_format, output_sr)
    
    async def generate_audio() -> AsyncIterator[bytes]:
        """Generate audio stream."""
        try:
            if request.audio_format == "pcm":
                # PCM can be truly streamed chunk by chunk
                async for audio_chunk, sample_rate in tts_engine.synthesize_streaming(
                    text=request.text,
                    voice_mode=request.voice_mode,
                    voice_reference=voice_reference,
                    voice_name=request.voice_config.voice_name,
                    speed=request.voice_config.speed,
                    sample_rate=request.sample_rate,
                    use_turbo=request.use_turbo,
                ):
                    encoded_chunk = encoder.encode_chunk(audio_chunk)
                    yield encoded_chunk
            else:
                # WAV and Vorbis need complete audio - collect all chunks first
                import numpy as np
                async for audio_chunk, sample_rate in tts_engine.synthesize_streaming(
                    text=request.text,
                    voice_mode=request.voice_mode,
                    voice_reference=voice_reference,
                    voice_name=request.voice_config.voice_name,
                    speed=request.voice_config.speed,
                    sample_rate=request.sample_rate,
                    use_turbo=request.use_turbo,
                ):
                    # Accumulate chunks in the encoder
                    encoder.encode_chunk(audio_chunk)
                
                # Finalize encoding (this will concatenate and encode properly)
                encoded_data = encoder.finalize()
                if encoded_data:
                    yield encoded_data
                
        except Exception as e:
            logger.error(f"Error during TTS synthesis: {e}")
            # In streaming context, errors mid-stream are handled by discarding
            # The connection will close and client should retry
            raise
    
    # Determine media type
    if request.audio_format == "pcm":
        media_type = "audio/pcm"
    elif request.audio_format == "wav":
        media_type = "audio/wav"
    elif request.audio_format == "vorbis":
        media_type = "audio/ogg"
    else:
        media_type = "application/octet-stream"
    
    return StreamingResponse(
        generate_audio(),
        media_type=media_type,
        headers={
            "X-Sample-Rate": str(output_sr),
            "X-Audio-Format": request.audio_format,
        }
    )


@app.websocket("/tts/stream")
async def websocket_tts(websocket: WebSocket):
    """WebSocket endpoint for bidirectional TTS streaming.
    
    Protocol:
    - Client sends JSON with TTSRequest + api_key
    - Server streams audio chunks as binary messages
    - Server sends JSON status messages
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Receive request
        data = await websocket.receive_json()
        
        # Verify API key
        api_key = data.get("api_key")
        if api_key != config.api_key:
            await websocket.send_json({"error": "Invalid API key"})
            await websocket.close(code=1008)  # Policy violation
            return
        
        # Parse request
        try:
            request = TTSRequest(**data)
        except Exception as e:
            await websocket.send_json({"error": f"Invalid request: {str(e)}"})
            await websocket.close(code=1003)  # Unsupported data
            return
        
        # Load voice reference if needed
        voice_reference = None
        if request.voice_mode == "clone":
            voice_reference = await voice_manager.load_voice_reference(request.voice_config.voice_id)
            if voice_reference is None:
                await websocket.send_json({"error": f"Voice not found: {request.voice_config.voice_id}"})
                await websocket.close(code=1003)
                return
        
        # Send start message
        await websocket.send_json({
            "status": "streaming",
            "sample_rate": request.sample_rate or tts_engine.sample_rate,
            "audio_format": request.audio_format
        })
        
        # Create encoder
        output_sr = request.sample_rate or tts_engine.sample_rate
        encoder = AudioStreamEncoder(request.audio_format, output_sr)
        
        # Stream audio
        try:
            async for audio_chunk, sample_rate in tts_engine.synthesize_streaming(
                text=request.text,
                voice_mode=request.voice_mode,
                voice_reference=voice_reference,
                voice_name=request.voice_config.voice_name,
                speed=request.voice_config.speed,
                sample_rate=request.sample_rate,
                use_turbo=request.use_turbo,
            ):
                encoded_chunk = encoder.encode_chunk(audio_chunk)
                await websocket.send_bytes(encoded_chunk)
            
            # Send completion message
            await websocket.send_json({"status": "complete"})
            
        except Exception as e:
            logger.error(f"Error during WebSocket TTS: {e}")
            await websocket.send_json({"error": str(e)})
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@app.post("/voices/upload", response_model=VoiceUploadResponse)
async def upload_voice(
    voice_id: str = Form(...),
    sample_rate: int = Form(...),
    audio_file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key)
):
    """Upload a voice reference file.
    
    Args:
        voice_id: Unique identifier for the voice
        sample_rate: Sample rate of the audio file
        audio_file: WAV audio file
        api_key: Verified API key
        
    Returns:
        Upload response
    """
    logger.info(f"Voice upload request: {voice_id}, sample_rate={sample_rate}")
    
    # Validate file type
    if not audio_file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only WAV files are supported")
    
    try:
        # Upload voice
        success = await voice_manager.upload_voice(
            voice_id=voice_id,
            audio_file=audio_file.file,
            sample_rate=sample_rate
        )
        
        if success:
            return VoiceUploadResponse(
                success=True,
                voice_id=voice_id,
                message=f"Voice '{voice_id}' uploaded successfully"
            )
        else:
            raise HTTPException(
                status_code=409,
                detail=f"Voice ID '{voice_id}' already exists"
            )
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading voice: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/voices/list", response_model=VoiceListResponse)
async def list_voices(api_key: str = Depends(verify_api_key)):
    """List all uploaded voices.
    
    Args:
        api_key: Verified API key
        
    Returns:
        List of voices
    """
    voices_data = await db.list_voices()
    voices = [VoiceInfo(**voice) for voice in voices_data]
    
    return VoiceListResponse(
        voices=voices,
        total=len(voices)
    )


@app.delete("/voices/{voice_id}", response_model=VoiceDeleteResponse)
async def delete_voice(
    voice_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete a voice reference.
    
    Args:
        voice_id: Voice identifier
        api_key: Verified API key
        
    Returns:
        Deletion response
    """
    logger.info(f"Voice deletion request: {voice_id}")
    
    success = await voice_manager.delete_voice(voice_id)
    
    if success:
        return VoiceDeleteResponse(
            success=True,
            voice_id=voice_id,
            message=f"Voice '{voice_id}' deleted successfully"
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Voice '{voice_id}' not found"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


def create_app() -> FastAPI:
    """Create and return FastAPI app instance."""
    return app
