"""FastAPI server for TTS streaming."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..utils.config import CONFIG
from . import dependencies
from .common import initialize_server_components
from .rest_routes import generation_router, voices_router, utilities_router
from ..services import get_synthesis_queue, stop_synthesis_queue

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TTS Inference FastAPI server...")

    db, voice_manager, voice_service = await initialize_server_components()

    dependencies.db = db
    dependencies.voice_manager = voice_manager
    dependencies.voice_service = voice_service

    get_synthesis_queue()

    logger.info("FastAPI server initialization complete")

    yield

    logger.info("Shutting down FastAPI server...")
    await stop_synthesis_queue()


app = FastAPI(
    title="TTS Inference Server",
    description="TTS inference server with streaming support",
    version="0.1.0",
    lifespan=lifespan,
    redoc_url=None,
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}},
)

app.include_router(utilities_router)
app.include_router(generation_router)
app.include_router(voices_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
