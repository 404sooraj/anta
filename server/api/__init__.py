"""API module for FastAPI routes and schemas."""

from .routes import router
from .schemas import TextRequest, ProcessTextResponse

__all__ = ["router", "TextRequest", "ProcessTextResponse"]
