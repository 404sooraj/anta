"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel
from typing import Dict, List, Any


class TextRequest(BaseModel):
    """Request model for text processing endpoint."""
    text: str


class ProcessTextResponse(BaseModel):
    """Response model for text processing endpoint."""
    response: str
    intent: Dict[str, Any]
    tool_calls: List[str]
    tool_results: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class TestPromptsResponse(BaseModel):
    """Response model for test prompts endpoint."""
    prompts: List[str]
    count: int


class ProcessTestPromptsResponse(BaseModel):
    """Response model for processing test prompts endpoint."""
    results: List[Dict[str, Any]]
    count: int
