"""FastAPI server for TTS streaming."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ..models import VoiceDatabase
from ..tts import get_tts_engine, VoiceManager
from ..services import VoiceService
from ..utils.config import CONFIG
from . import dependencies
from .rest_routes import generation_router, voices_router, utilities_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Replaces deprecated on_event("startup") and on_event("shutdown").
    """
    # Startup
    logger.info("Starting TTS Inference FastAPI server...")

    # Validate API key is configured
    try:
        CONFIG.validate_api_key()
    except ValueError as e:
        logger.error(str(e))
        raise

    # Ensure directories exist
    CONFIG.ensure_directories()

    # Initialize database
    dependencies.db = VoiceDatabase(CONFIG.database_path)
    await dependencies.db.initialize()

    # Initialize voice manager
    dependencies.voice_manager = VoiceManager(dependencies.db)

    # Initialize voice service
    dependencies.voice_service = VoiceService(
        dependencies.voice_manager, dependencies.db
    )

    # Initialize TTS engine (with config settings)
    tts_engine = get_tts_engine()
    await tts_engine.initialize()

    logger.info("FastAPI server initialization complete")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI server...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="TTS Inference Server",
    description="TTS inference server with streaming support",
    version="0.1.0",
    lifespan=lifespan,
    redoc_url=None,
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(utilities_router)
app.include_router(generation_router)
app.include_router(voices_router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )

