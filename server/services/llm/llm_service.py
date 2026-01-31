"""
LLM Service - Language Model Processing
Handles LLM interactions for processing transcripts using the response pipeline
"""
import os
import logging
from dotenv import load_dotenv
from modules.response.response import ResponsePipeline

load_dotenv()
logger = logging.getLogger(__name__)


# =========================
# LLM Service
# =========================
class LLMService:
    """Process transcripts with LLM using the response pipeline"""
    
    def __init__(self):
        """Initialize LLM service with response pipeline"""
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables")
        
        # Initialize the response pipeline (model name from GEMINI_MODEL_NAME in .env)
        self.pipeline = ResponsePipeline(
            api_key=self.api_key,
            model_name=os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash-lite"),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
        )
        logger.info("✓ LLM Service initialized with response pipeline")
    
    async def process(self, transcript: str, conversation_history: list = None) -> dict:
        """
        Process transcript through the complete pipeline.
        
        Pipeline flow:
        1. Intent Detection
        2. LLM Processing (with tool definitions and conversation context)
        3. Tool Execution (if needed)
        4. LLM Response Generation
        
        Args:
            transcript: The transcribed text to process
            conversation_history: Previous conversation turns for context
            
        Returns:
            Dictionary containing:
            - response: Final text response
            - intent: Detected intent information
            - tool_calls: List of tools that were called
            - tool_results: Results from tool execution
        """
        logger.info(f"Processing transcript: {transcript[:100]}...")
        
        try:
            result = await self.pipeline.process_text(transcript, conversation_history)
            
            logger.info(f"LLM processing complete. Response: {result.get('response', '')[:100]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM processing: {e}")
            return {
                "response": f"I encountered an error processing your request: {str(e)}",
                "intent": {},
                "tool_calls": [],
                "tool_results": [],
                "error": str(e)
            }
