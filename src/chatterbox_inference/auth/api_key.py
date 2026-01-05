"""API key authentication for Chatterbox Inference."""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from ..utils.config import config

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """Verify API key from Authorization header.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        The API key if valid
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not credentials:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != config.api_key:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return credentials.credentials


def verify_api_key_zmq(api_key: Optional[str]) -> bool:
    """Verify API key for ZMQ requests.
    
    Args:
        api_key: API key from request
        
    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        logger.warning("Missing API key in ZMQ request")
        return False
    
    if api_key != config.api_key:
        logger.warning(f"Invalid API key in ZMQ request")
        return False
    
    return True
