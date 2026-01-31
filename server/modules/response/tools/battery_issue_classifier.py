"""Battery issue classification system."""

import logging
from typing import Dict, Any, Optional
from enum import Enum

from langchain_aws import ChatBedrockConverse

from modules.config import ConfigEnv

logger = logging.getLogger(__name__)


class BatteryIssueCategory(str, Enum):
    """Standard categories for battery issues."""
    
    # Charging issues
    CHARGING_SLOW = "charging_slow"
    CHARGING_FAILED = "charging_failed"
    NOT_CHARGING = "not_charging"
    
    # Capacity/Range issues
    LOW_CAPACITY = "low_capacity"
    RAPID_DISCHARGE = "rapid_discharge"
    RANGE_REDUCED = "range_reduced"
    
    # Physical issues
    OVERHEATING = "overheating"
    SWELLING = "swelling"
    PHYSICAL_DAMAGE = "physical_damage"
    LEAKAGE = "leakage"
    
    # Connection issues
    CONNECTION_ERROR = "connection_error"
    NOT_DETECTED = "not_detected"
    FITMENT_ISSUE = "fitment_issue"
    
    # Performance issues
    PERFORMANCE_DEGRADED = "performance_degraded"
    POWER_FLUCTUATION = "power_fluctuation"
    SUDDEN_SHUTDOWN = "sudden_shutdown"
    
    # Health warnings
    HEALTH_WARNING = "health_warning"
    CELL_IMBALANCE = "cell_imbalance"
    
    # Other
    OTHER = "other"
    UNKNOWN = "unknown"


# Keyword-based classification rules (fast fallback)
KEYWORD_RULES: Dict[BatteryIssueCategory, list[str]] = {
    BatteryIssueCategory.CHARGING_SLOW: [
        "slow charging", "charge slowly", "takes long to charge", "charging time",
        "धीरे चार्ज", "चार्ज होने में समय"
    ],
    BatteryIssueCategory.CHARGING_FAILED: [
        "charge failed", "charging failed", "won't charge", "not charging properly",
        "चार्ज फेल", "चार्ज नहीं हो रहा"
    ],
    BatteryIssueCategory.NOT_CHARGING: [
        "not charging", "doesn't charge", "cannot charge", "चार्ज नहीं"
    ],
    BatteryIssueCategory.LOW_CAPACITY: [
        "low capacity", "less capacity", "battery low", "drains fast", "कम क्षमता"
    ],
    BatteryIssueCategory.RAPID_DISCHARGE: [
        "discharge fast", "draining quickly", "losing charge", "battery dies fast",
        "जल्दी खत्म", "तेजी से डिस्चार्ज"
    ],
    BatteryIssueCategory.RANGE_REDUCED: [
        "less range", "reduced range", "short range", "doesn't last long",
        "कम रेंज", "दूरी कम"
    ],
    BatteryIssueCategory.OVERHEATING: [
        "hot", "heating", "overheating", "warm", "temperature", "गर्म", "heat"
    ],
    BatteryIssueCategory.SWELLING: [
        "swelling", "swollen", "bulging", "expanded", "फूला हुआ"
    ],
    BatteryIssueCategory.PHYSICAL_DAMAGE: [
        "damage", "broken", "crack", "dent", "टूटा", "क्षतिग्रस्त"
    ],
    BatteryIssueCategory.LEAKAGE: [
        "leak", "leaking", "liquid", "spill", "रिसाव"
    ],
    BatteryIssueCategory.CONNECTION_ERROR: [
        "connection", "connect", "disconnect", "कनेक्शन"
    ],
    BatteryIssueCategory.NOT_DETECTED: [
        "not detected", "not recognized", "not showing", "पता नहीं चल रहा"
    ],
    BatteryIssueCategory.FITMENT_ISSUE: [
        "doesn't fit", "fitting", "loose", "tight", "फिट नहीं"
    ],
    BatteryIssueCategory.PERFORMANCE_DEGRADED: [
        "slow", "sluggish", "poor performance", "weak", "कमजोर", "धीमा"
    ],
    BatteryIssueCategory.POWER_FLUCTUATION: [
        "fluctuation", "unstable", "varies", "inconsistent", "उतार-चढ़ाव"
    ],
    BatteryIssueCategory.SUDDEN_SHUTDOWN: [
        "shutdown", "turns off", "dies suddenly", "cuts off", "अचानक बंद"
    ],
    BatteryIssueCategory.HEALTH_WARNING: [
        "health warning", "health issue", "स्वास्थ्य चेतावनी"
    ],
    BatteryIssueCategory.CELL_IMBALANCE: [
        "imbalance", "cell", "uneven", "असंतुलन"
    ],
}


class BatteryIssueClassifier:
    """Classifies battery issues from user descriptions."""
    
    def __init__(self):
        """Initialize the classifier."""
        self.model_name = ConfigEnv.BEDROCK_MODEL_ID or "anthropic.claude-3-haiku-20240307-v1:0"
        self.region_name = ConfigEnv.get_bedrock_region()
        self._llm: Optional[ChatBedrockConverse] = None
    
    @property
    def llm(self) -> ChatBedrockConverse:
        """Lazy load LLM."""
        if self._llm is None:
            self._llm = ChatBedrockConverse(
                model=self.model_name,
                temperature=0,
                max_tokens=512,
                region_name=self.region_name,
            )
        return self._llm
    
    def _keyword_classify(self, text: str) -> Optional[BatteryIssueCategory]:
        """Fast keyword-based classification."""
        text_lower = text.lower()
        
        for category, keywords in KEYWORD_RULES.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    logger.info(f"Keyword match: '{keyword}' -> {category.value}")
                    return category
        
        return None
    
    async def classify(self, user_description: str) -> Dict[str, Any]:
        """
        Classify a battery issue from user description.
        
        Args:
            user_description: The user's description of the battery issue.
            
        Returns:
            Dictionary with classification, confidence, and extracted details.
        """
        # First try keyword-based classification (fast)
        keyword_result = self._keyword_classify(user_description)
        
        if keyword_result and keyword_result != BatteryIssueCategory.OTHER:
            return {
                "classification": keyword_result.value,
                "confidence": 0.8,
                "method": "keyword",
                "details": user_description,
            }
        
        # Fall back to LLM classification for complex cases
        try:
            return await self._llm_classify(user_description)
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Return keyword result if available, else unknown
            return {
                "classification": keyword_result.value if keyword_result else BatteryIssueCategory.UNKNOWN.value,
                "confidence": 0.5,
                "method": "fallback",
                "details": user_description,
            }
    
    async def _llm_classify(self, user_description: str) -> Dict[str, Any]:
        """Use LLM for classification when keywords don't match."""
        categories = [c.value for c in BatteryIssueCategory]
        
        prompt = f"""Classify this battery issue complaint into one of the predefined categories.

User complaint: "{user_description}"

Available categories:
{chr(10).join(f'- {c}' for c in categories)}

Category descriptions:
- charging_slow: Battery takes too long to charge
- charging_failed: Charging process fails or errors
- not_charging: Battery won't charge at all
- low_capacity: Battery capacity is lower than expected
- rapid_discharge: Battery loses charge too quickly
- range_reduced: Vehicle range is less than expected
- overheating: Battery gets hot during use or charging
- swelling: Battery is physically swollen or bulging
- physical_damage: Visible damage to battery casing
- leakage: Battery is leaking fluid
- connection_error: Issues connecting battery to vehicle/charger
- not_detected: Battery not recognized by vehicle/system
- fitment_issue: Battery doesn't fit properly in the slot
- performance_degraded: General performance issues
- power_fluctuation: Unstable power output
- sudden_shutdown: Battery suddenly stops working
- health_warning: System shows health warnings
- cell_imbalance: Battery cells are imbalanced
- other: Doesn't fit any specific category
- unknown: Cannot determine the issue

Respond with ONLY a JSON object in this exact format:
{{
    "classification": "category_name",
    "confidence": 0.0-1.0,
    "summary": "brief one-line summary of the issue"
}}"""

        response = await self.llm.ainvoke(prompt)
        raw = response.content
        
        if isinstance(raw, list):
            response_text = " ".join(
                (c.get("text", c) if isinstance(c, dict) else str(c))
                for c in raw
            ).strip()
        else:
            response_text = (raw or "").strip()
        
        # Parse JSON response
        import json
        
        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        # Validate classification
        classification = result.get("classification", "unknown")
        if classification not in categories:
            classification = "unknown"
        
        return {
            "classification": classification,
            "confidence": result.get("confidence", 0.7),
            "method": "llm",
            "details": result.get("summary", user_description),
        }


# Singleton instance
_classifier_instance: Optional[BatteryIssueClassifier] = None


def get_battery_issue_classifier() -> BatteryIssueClassifier:
    """Get or create the singleton classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = BatteryIssueClassifier()
    return _classifier_instance
