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
        "battery_query",  # Asking about battery status/health/issues
        "subscription_query",  # Asking about subscription/plan
        "service_center_query",  # Asking about service center visits
        "swap_attempt_query",  # Asking about swap attempts
        "human_handoff",  # User wants to speak to a human agent
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
- service_request: User requesting a service or help (not a complaint)
- problem_report: User COMPLAINING about something or REPORTING an issue they are experiencing. Examples:
  * "Battery garam ho rahi hai" (battery getting hot) = problem_report
  * "Battery charge nahi ho rahi" (battery not charging) = problem_report  
  * "Bahut jaldi discharge ho jati hai" (drains too fast) = problem_report
  * "Scooter slow chal raha hai" (scooter running slow) = problem_report
  * "Kuch problem hai" (there's some problem) = problem_report
  * Any statement describing something IS wrong/broken/not working = problem_report
- location_query: User asking specifically about their own current location
- station_query: User asking about nearest station, where to swap battery, finding a swap station
- battery_query: User ASKING about their battery (query/question), NOT complaining. Examples:
  * "Meri battery ki health kya hai?" (what is my battery health?) = battery_query
  * "Battery status batao" (tell me battery status) = battery_query
- subscription_query: User asking about their subscription, plan, validity, or pricing. Examples:
  * "Mera plan kya hai?" (what is my plan?) = subscription_query
  * "Subscription kab tak valid hai?" (how long is subscription valid?) = subscription_query
  * "Plan ki price kya hai?" (what is plan price?) = subscription_query
  * "Mera plan expire kab hoga?" (when will my plan expire?) = subscription_query
  * "What is my subscription status?" = subscription_query
- service_center_query: User asking about service center visits or history
- swap_attempt_query: User asking about their swap attempts or swap history
- human_handoff: User wants to speak to a human agent, customer service rep, or real person. Examples:
  * "Mujhe kisi insaan se baat karni hai" (I want to talk to a human) = human_handoff
  * "Agent se connect karo" (connect me to agent) = human_handoff
  * "Customer care se baat karao" (let me talk to customer care) = human_handoff
  * "Real person se baat karna hai" (want to talk to real person) = human_handoff
  * "I want to speak to a human" = human_handoff
  * "Transfer me to an agent" = human_handoff
  * "Can I talk to someone real?" = human_handoff
- general: Greetings, thanks, or conversation not fitting other categories

CRITICAL RULES:
1. If user describes something IS wrong/broken/hot/slow/not working → problem_report (even without words like "complaint" or "report")
2. If user ASKS a question about battery status → battery_query
3. "Battery garam hoti hai" (battery gets hot) = problem_report, NOT battery_query
4. "Battery ki health kya hai?" (what is battery health) = battery_query, NOT problem_report
5. When in doubt between problem_report and general, prefer problem_report if user mentions any issue
6. If user explicitly asks for human/agent/customer care/real person → human_handoff

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
