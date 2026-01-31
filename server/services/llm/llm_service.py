"""
LLM Service - Language Model Processing
Handles LLM interactions for processing transcripts using the response pipeline
"""
import logging

from modules.config import ConfigEnv
from modules.response.response import ResponsePipeline

logger = logging.getLogger(__name__)


# =========================
# LLM Service
# =========================
class LLMService:
    """Process transcripts with LLM using the response pipeline"""

    def __init__(self):
        """Initialize LLM service with response pipeline"""
        self.api_key = ConfigEnv.BEDROCK_API_KEY
        # Bedrock uses AWS credentials; keep api_key for backward compatibility only

        self.pipeline = ResponsePipeline(
            api_key=self.api_key,
            model_name=ConfigEnv.BEDROCK_MODEL_ID,
            temperature=ConfigEnv.BEDROCK_TEMPERATURE,
        )
        logger.info("✓ LLM Service initialized with response pipeline")
    
    async def process(
        self,
        transcript: str,
        conversation_history: list = None,
        session_id: str = None,
        user_id: str = None,
        is_twilio_call: bool = False,
    ) -> dict:
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
            session_id: Optional; when set, conversation and intent_log are persisted
            user_id: Optional; used for conversation.user_id when persisting
            is_twilio_call: Whether this is a Twilio phone call (no GPS available)

        Returns:
            Dictionary containing:
            - response: Final text response
            - intent: Detected intent information
            - tool_calls: List of tools that were called
            - tool_results: Results from tool execution
        """
        logger.info(f"Processing transcript: {transcript[:100]}...")
        logger.info(f"[LLMService] user_id: {user_id}, is_twilio_call: {is_twilio_call}")

        try:
            result = await self.pipeline.process_text(
                transcript,
                conversation_history=conversation_history,
                session_id=session_id,
                user_id=user_id,
                is_twilio_call=is_twilio_call,
            )
            
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

    async def process_stream(
        self,
        transcript: str,
        conversation_history: list = None,
        user_id: str | None = None,
        is_twilio_call: bool = False,
    ) -> dict:
        """
        Process transcript and stream the LLM response.

        Args:
            transcript: The transcribed text to process
            conversation_history: Previous conversation turns for context
            user_id: Optional; used for tool calls requiring user identification
            is_twilio_call: Whether this is a Twilio phone call (no GPS available)

        Returns:
            Dictionary containing metadata and an async generator under "stream".
        """
        logger.info(f"Processing transcript (streaming): {transcript[:100]}...")
        logger.info(f"[LLMService] user_id received: {user_id}, is_twilio_call: {is_twilio_call}")

        try:
            result = await self.pipeline.process_text_streaming(
                transcript,
                conversation_history,
                user_id=user_id,
                is_twilio_call=is_twilio_call,
            )
            return result
        except Exception as e:
            logger.error(f"Error in LLM streaming: {e}")
            return {
                "stream": None,
                "response": f"I encountered an error processing your request: {str(e)}",
                "intent": {},
                "tool_calls": [],
                "tool_results": [],
                "error": str(e)
            }
