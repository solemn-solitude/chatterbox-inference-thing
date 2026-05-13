"""API key authentication for TTS Inference."""

import hmac
import logging

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..utils.config import CONFIG

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    if not credentials:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not hmac.compare_digest(credentials.credentials, CONFIG.api_key):
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


def verify_api_key_zmq(api_key: str | None) -> bool:
    if not api_key:
        logger.warning("Missing API key in ZMQ request")
        return False

    if not hmac.compare_digest(api_key, CONFIG.api_key):
        logger.warning("Invalid API key in ZMQ request")
        return False

    return True
