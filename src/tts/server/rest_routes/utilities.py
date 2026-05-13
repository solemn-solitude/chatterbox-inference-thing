"""Utility endpoints (health, ready, model management)."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ...models import HealthResponse, ReadyResponse
from ...auth import verify_api_key
from ...services import ModelService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["utilities"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check():
    """Readiness check endpoint."""
    status = ModelService.get_model_status()
    
    ready = (
        status["model_loaded"] and 
        status["voice_dir_accessible"] and 
        status["database_accessible"]
    )
    
    return ReadyResponse(
        ready=ready,
        **status
    )


@router.post("/model/unload")
async def unload_model(api_key: str = Depends(verify_api_key)):
    """Manually unload TTS model from memory."""
    logger.info("Manual model unload requested")
    
    try:
        result = await ModelService.unload_model()
        return JSONResponse(status_code=200, content=result)
        
    except Exception as e:
        logger.error(f"Error unloading model: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unload model: {str(e)}"
        )
