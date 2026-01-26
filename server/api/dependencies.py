"""Dependency injection for FastAPI routes."""

from fastapi import Request, HTTPException
from modules.response.response import ResponsePipeline


def get_pipeline_dependency(request: Request) -> ResponsePipeline:
    """
    Dependency to inject pipeline into routes.
    
    Args:
        request: FastAPI request object containing app state.
        
    Returns:
        ResponsePipeline instance from app state.
        
    Raises:
        HTTPException: If pipeline is not initialized in app state.
    """
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=500,
            detail="Pipeline not initialized. Server may be starting up."
        )
    return pipeline
