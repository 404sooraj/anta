"""
Text Processing Router - REST API endpoints
Handles text processing through the response pipeline
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from services.llm import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/text", tags=["text"])


# =========================
# Schemas
# =========================
class TextRequest(BaseModel):
    """Request model for text processing endpoint."""
    text: str
    session_id: Optional[str] = None  # when set, conversation and intent_log are persisted
    user_id: Optional[str] = None  # optional; used for conversation.user_id when persisting


class ProcessTextResponse(BaseModel):
    """Response model for text processing endpoint."""
    response: str
    intent: Dict[str, Any]
    tool_calls: List[str]
    tool_results: List[Dict[str, Any]]


# =========================
# Initialize LLM Service
# =========================
llm_service = LLMService()


# =========================
# Endpoints
# =========================
@router.post("/process", response_model=ProcessTextResponse)
async def process_text(request: TextRequest):
    """
    Process text through the complete pipeline:
    1. Intent Detection
    2. LLM Processing (with tool definitions)
    3. Tool Execution (if needed)
    4. Response Generation
    
    This is the REST API equivalent of the WebSocket STT endpoint.
    """
    try:
        logger.info(f"Processing text: {request.text[:100]}...")
        
        # Process through LLM pipeline (optional session_id/user_id for persistence)
        result = await llm_service.process(
            request.text,
            session_id=request.session_id,
            user_id=request.user_id,
        )
        
        # Extract tool names (handle both string lists and dict lists)
        tool_calls_raw = result.get('tool_calls', [])
        tool_names = []
        for tc in tool_calls_raw:
            if isinstance(tc, dict):
                tool_names.append(tc.get('name', tc.get('tool_name', 'unknown')))
            elif isinstance(tc, str):
                tool_names.append(tc)
        
        return ProcessTextResponse(
            response=result.get("response", ""),
            intent=result.get("intent", {}),
            tool_calls=tool_names,
            tool_results=result.get("tool_results", []),
        )
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for text processing"""
    return {"status": "ok", "service": "text_processing"}
