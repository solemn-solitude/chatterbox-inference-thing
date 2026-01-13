"""REST API route modules."""

from .generation import router as generation_router
from .voices import router as voices_router
from .utilities import router as utilities_router

__all__ = ["generation_router", "voices_router", "utilities_router"]
