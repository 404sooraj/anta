"""
Call Analytics Service - Generate summaries and satisfaction scores for call transcripts
"""
import logging
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_aws import ChatBedrockConverse
from modules.config import ConfigEnv

logger = logging.getLogger(__name__)


class CallAnalyticsService:
    """Service for analyzing call transcripts and generating insights."""
    
    def __init__(self):
        """Initialize the analytics service with LLM."""
        self.model = ChatBedrockConverse(
            model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=1024,
            region_name=ConfigEnv.AWS_REGION or "us-east-1",
        )
    
    async def analyze_call(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze a call transcript and generate summary and satisfaction score.
        
        Args:
            messages: List of conversation messages with 'role' and 'text'
        
        Returns:
            Dict with 'summary', 'satisfaction_score', and 'satisfaction_reasoning'
        """
        if not messages:
            return {
                "summary": "No conversation recorded.",
                "satisfaction_score": 3,
                "satisfaction_reasoning": "Empty conversation"
            }
        
        # Build transcript for analysis
        transcript_lines = []
        for msg in messages:
            role_label = "Customer" if msg["role"] == "user" else "Agent"
            transcript_lines.append(f"{role_label}: {msg['text']}")
        
        transcript_text = "\n".join(transcript_lines)
        
        # Create analysis prompt
        system_prompt = """You are an expert call center analyst. Analyze customer service call transcripts and provide:
1. A concise summary (2-3 sentences) covering the main topic and outcome
2. A satisfaction score (1-5) where:
   - 5: Excellent - Issue fully resolved, customer very satisfied
   - 4: Good - Issue resolved, customer satisfied
   - 3: Neutral - Partial resolution or information provided
   - 2: Poor - Issue not resolved, customer frustrated
   - 1: Very Poor - Multiple issues, customer very dissatisfied
3. Brief reasoning for the satisfaction score

Respond in JSON format:
{
  "summary": "Brief summary here",
  "satisfaction_score": 4,
  "satisfaction_reasoning": "Brief reasoning here"
}"""

        user_prompt = f"""Analyze this call transcript:

{transcript_text}

Provide your analysis in JSON format."""

        try:
            # Call LLM for analysis
            response = await self.model.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            # Parse response
            content = response.content.strip()
            
            # Extract JSON from response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Validate and normalize
                return {
                    "summary": result.get("summary", "Call completed."),
                    "satisfaction_score": max(1, min(5, int(result.get("satisfaction_score", 3)))),
                    "satisfaction_reasoning": result.get("satisfaction_reasoning", "Standard interaction")
                }
            else:
                # Fallback if JSON not found
                logger.warning("Could not parse JSON from LLM response, using fallback")
                return {
                    "summary": content[:200] if content else "Call completed.",
                    "satisfaction_score": 3,
                    "satisfaction_reasoning": "Unable to parse detailed analysis"
                }
        
        except Exception as e:
            logger.error(f"Error analyzing call: {e}")
            return {
                "summary": "Call completed. Analysis failed.",
                "satisfaction_score": 3,
                "satisfaction_reasoning": f"Error during analysis: {str(e)[:50]}"
            }
