"""Intent detection module for classifying user intents."""

import json
import logging
from typing import Dict, Any, Optional

from langchain_aws import ChatBedrockConverse

from modules.config import ConfigEnv

logger = logging.getLogger(__name__)


class IntentDetector:
    """Detects user intent from text input using LLM."""
    
    INTENT_CATEGORIES = [
        "user_query",  # General user information query
        "service_request",  # Request for service
        "problem_report",  # Reporting a problem
        "location_query",  # Asking about location
        "station_query",  # Asking about nearest station or where to swap
        "service_center_query",  # Asking about service center visits
        "swap_attempt_query",  # Asking about swap attempts
        "general",  # General conversation
    ]
    
    def __init__(self, api_key: Optional[str] = None, region_name: Optional[str] = None):
        """
        Initialize the intent detector.
        
        Args:
            api_key: Unused for Bedrock. Present for backward compatibility.
            region_name: AWS region. If not provided, reads from BEDROCK_REGION or AWS_REGION.
        """
        self.api_key = api_key
        # Use same Bedrock model as pipeline; GEMINI_MODEL_NAME kept for override
        self.model_name = ConfigEnv.BEDROCK_MODEL_ID
        if not self.model_name:
            raise ValueError(
                "Set BEDROCK_MODEL_ID or GEMINI_MODEL_NAME in environment variables"
            )
        self.region_name = region_name or ConfigEnv.get_bedrock_region()
        self.model = ChatBedrockConverse(
            model=self.model_name,
            temperature=0,
            max_tokens=512,
            region_name=self.region_name,
        )

    def _get_intent_prompt(self, text: str) -> str:
        """Generate the prompt for intent detection."""
        categories_str = ", ".join(self.INTENT_CATEGORIES)
        return f"""Analyze the following user input and classify the intent. 

User input: "{text}"

Intent categories: {categories_str}

Category definitions:
- user_query: User asking about their personal info, name, profile, account details
- service_request: User requesting a service or help
- problem_report: User reporting an issue or problem
- location_query: User asking specifically about their own current location or where they are
- station_query: User asking about nearest station, where to swap battery, finding a swap station, stations with available batteries
- service_center_query: User asking about service center visits or history
- swap_attempt_query: User asking about their swap attempts or swap history
- general: General conversation not fitting other categories

IMPORTANT: If the user mentions "station", "swap station", "nearest station", or "where to swap", classify as station_query, NOT location_query.

Respond with a JSON object in this exact format:
{{
    "intent": "one_of_the_categories",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Only respond with the JSON object, no additional text."""
    
    async def detect_intent(self, text: str) -> Dict[str, Any]:
        """
        Detect intent from user text.
        
        Args:
            text: The user input text to analyze.
            
        Returns:
            Dictionary containing intent, confidence, and reasoning.
        """
        try:
            prompt = self._get_intent_prompt(text)
            
            response = await self.model.ainvoke(prompt)
            raw = response.content
            if isinstance(raw, list):
                response_text = " ".join(
                    (c.get("text", c) if isinstance(c, dict) else str(c))
                    for c in raw
                ).strip()
            else:
                response_text = (raw or "").strip()

            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            intent_data = json.loads(response_text)
            
            # Validate intent category
            if intent_data.get("intent") not in self.INTENT_CATEGORIES:
                logger.warning(f"Invalid intent category: {intent_data.get('intent')}. Defaulting to 'general'")
                intent_data["intent"] = "general"
            
            logger.info(f"Detected intent: {intent_data.get('intent')} (confidence: {intent_data.get('confidence', 0)})")
            return intent_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent detection response as JSON: {e}")
            return {
                "intent": "general",
                "confidence": 0.0,
                "reasoning": "Failed to parse intent detection response"
            }
        except Exception as e:
            logger.error(f"Error detecting intent: {e}")
            return {
                "intent": "general",
                "confidence": 0.0,
                "reasoning": f"Error during intent detection: {str(e)}"
            }
