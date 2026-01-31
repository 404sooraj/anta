"""Intent detection module for classifying user intents."""

import os
import json
import logging
from typing import Dict, Any, Optional

from langchain_aws import ChatBedrockConverse

logger = logging.getLogger(__name__)


class IntentDetector:
    """Detects user intent from text input using LLM."""
    
    INTENT_CATEGORIES = [
        "user_query",  # General user information query
        "service_request",  # Request for service
        "problem_report",  # Reporting a problem
        "location_query",  # Asking about location
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
        self.model_name = os.getenv("BEDROCK_MODEL_ID")
        if not self.model_name:
            raise ValueError("BEDROCK_MODEL_ID must be set in environment variables")
        self.region_name = region_name or os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION")
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
            response_text = (response.content or "").strip()
            
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
