"""API route handlers for the response pipeline."""

import logging
from fastapi import APIRouter, HTTPException, Depends

from modules.response.response import ResponsePipeline
from .dependencies import get_pipeline_dependency
from .schemas import (
    TextRequest,
    ProcessTextResponse,
    TestPromptsResponse,
    ProcessTestPromptsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["response"])


@router.post("/process-text", response_model=ProcessTextResponse)
async def process_text(
    request: TextRequest,
    pipeline: ResponsePipeline = Depends(get_pipeline_dependency)
):
    """
    Process text through the complete pipeline:
    1. Intent Detection
    2. LLM Processing (with tool definitions)
    3. Tool Execution (if needed)
    4. LLM Response Generation
    5. Text Output
    """
    try:
        # Process text using injected pipeline
        result = await pipeline.process_text(request.text)
        
        return ProcessTextResponse(
            response=result.get("response", ""),
            intent=result.get("intent", {}),
            tool_calls=result.get("tool_calls", []),
            tool_results=result.get("tool_results", []),
            metadata=result.get("metadata", {}),
        )
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-prompts", response_model=TestPromptsResponse)
async def get_test_prompts(
    pipeline: ResponsePipeline = Depends(get_pipeline_dependency)
):
    """Get test prompts from test-prompts.json file."""
    try:
        prompts = pipeline.load_test_prompts()
        return TestPromptsResponse(prompts=prompts, count=len(prompts))
    except Exception as e:
        logger.error(f"Error loading test prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-test-prompts", response_model=ProcessTestPromptsResponse)
async def process_test_prompts(
    pipeline: ResponsePipeline = Depends(get_pipeline_dependency)
):
    """Process all test prompts from test-prompts.json."""
    try:
        prompts = pipeline.load_test_prompts()
        
        results = []
        for prompt in prompts:
            result = await pipeline.process_text(prompt)
            results.append({
                "prompt": prompt,
                "response": result.get("response", ""),
                "intent": result.get("intent", {}),
                "tool_calls": result.get("tool_calls", []),
            })
        
        return ProcessTestPromptsResponse(results=results, count=len(results))
        
    except Exception as e:
        logger.error(f"Error processing test prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
