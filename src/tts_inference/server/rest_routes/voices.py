"""Voice management endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from ...models import VoiceInfo, VoiceListResponse, VoiceUploadResponse, VoiceDeleteResponse, VoiceRenameResponse
from ...auth import verify_api_key
from ...services import VoiceService
from ..dependencies import get_voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voices", tags=["voices"])


@router.post("/upload", response_model=VoiceUploadResponse)
async def upload_voice(
    voice_id: str = Form(...),
    sample_rate: int = Form(...),
    audio_file: UploadFile = File(...),
    voice_service: VoiceService = Depends(get_voice_service),
    api_key: str = Depends(verify_api_key)
):
    """Upload a voice reference file."""
    logger.info(f"Voice upload request: {voice_id}, sample_rate={sample_rate}")
    
    # Validate file type
    if not audio_file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only WAV files are supported")
    
    # Check if voice ID already exists
    if await voice_service.voice_exists(voice_id):
        logger.warning(f"Voice upload failed: Voice ID '{voice_id}' already exists")
        raise HTTPException(
            status_code=400,
            detail=f"Voice ID '{voice_id}' already exists. Please use a different identifier or delete the existing voice first."
        )
    
    try:
        # Upload voice
        success = await voice_service.upload_voice(
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
            logger.error(f"Voice upload returned False unexpectedly for {voice_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to upload voice '{voice_id}'. Please try again."
            )
            
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error uploading voice: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading voice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list", response_model=VoiceListResponse)
async def list_voices(
    voice_service: VoiceService = Depends(get_voice_service),
    api_key: str = Depends(verify_api_key)
):
    """List all uploaded voices."""
    voices_data = await voice_service.list_voices()
    voices = [VoiceInfo(**voice) for voice in voices_data]
    
    return VoiceListResponse(
        voices=voices,
        total=len(voices)
    )


@router.delete("/{voice_id}", response_model=VoiceDeleteResponse)
async def delete_voice(
    voice_id: str,
    voice_service: VoiceService = Depends(get_voice_service),
    api_key: str = Depends(verify_api_key)
):
    """Delete a voice reference."""
    logger.info(f"Voice deletion request: {voice_id}")
    
    success = await voice_service.delete_voice(voice_id)
    
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


@router.put("/{voice_id}/rename", response_model=VoiceRenameResponse)
async def rename_voice(
    voice_id: str,
    new_voice_id: str = Form(...),
    voice_service: VoiceService = Depends(get_voice_service),
    api_key: str = Depends(verify_api_key)
):
    """Rename a voice reference."""
    logger.info(f"Voice rename request: {voice_id} -> {new_voice_id}")
    
    # Validate new_voice_id
    if not new_voice_id or not new_voice_id.strip():
        raise HTTPException(
            status_code=400,
            detail="New voice ID cannot be empty"
        )
    
    # Check for invalid characters in new_voice_id
    invalid_chars = set('/\\:*?"<>|')
    if any(char in new_voice_id for char in invalid_chars):
        raise HTTPException(
            status_code=400,
            detail=f"New voice ID cannot contain: {' '.join(invalid_chars)}"
        )
    
    # Check if old voice exists
    if not await voice_service.voice_exists(voice_id):
        raise HTTPException(
            status_code=404,
            detail=f"Voice '{voice_id}' not found"
        )
    
    # Check if new voice ID already exists
    if await voice_service.voice_exists(new_voice_id):
        raise HTTPException(
            status_code=400,
            detail=f"Voice ID '{new_voice_id}' already exists. Please choose a different name."
        )
    
    try:
        success = await voice_service.rename_voice(voice_id, new_voice_id)
        
        if success:
            return VoiceRenameResponse(
                success=True,
                old_voice_id=voice_id,
                new_voice_id=new_voice_id,
                message=f"Voice renamed from '{voice_id}' to '{new_voice_id}' successfully"
            )
        else:
            logger.error(f"Voice rename returned False unexpectedly for {voice_id}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to rename voice '{voice_id}'. Please try again."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming voice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
