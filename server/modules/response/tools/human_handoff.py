"""Tool for requesting human agent handoff."""

from datetime import datetime, timezone
from typing import Dict, Any

from pydantic import BaseModel, Field

from .base import BaseTool


class RequestHumanAgentInput(BaseModel):
    """Input schema for requestHumanAgent tool."""
    userId: str = Field(..., description="The unique identifier of the user")
    reason: str = Field(
        default="User requested to speak with a human agent",
        description="The reason for requesting human assistance"
    )


class RequestHumanAgentTool(BaseTool):
    """Request connection to a human call center agent."""

    name: str = "requestHumanAgent"
    description: str = """Initiates a warm handoff to connect the user with a human call center agent.

Use this tool when the user:
- Explicitly asks to speak to a human/person/agent/representative
- Says things like "मुझे किसी से बात करनी है" (I need to talk to someone)
- Says "real person", "actual person", "human agent", "customer care", "call center"
- Expresses frustration and wants human help
- Says "agent se baat karo", "insaan se baat", "kisi ko bulao"
- The AI cannot resolve their issue and human intervention is needed

This will:
1. Notify the system to connect a human agent
2. Put the user in a queue for the next available agent
3. Maintain the conversation context for warm handoff"""
    args_schema = RequestHumanAgentInput

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute requestHumanAgent tool.

        Args:
            userId: The unique identifier of the user.
            reason: Reason for requesting human agent.

        Returns:
            Dictionary containing handoff request status.
        """
        userId = kwargs.get("userId")
        reason = kwargs.get("reason", "User requested human assistance")
        
        if not userId:
            return {
                "status": "error",
                "data": {"message": "userId is required"},
            }
        
        # The actual WebSocket handoff is handled by the STT router
        # This tool just signals the intent and returns confirmation
        return {
            "status": "ok",
            "action": "handoff_requested",
            "data": {
                "message": "Human agent connection requested. Please wait while we connect you to the next available agent.",
                "userId": userId,
                "reason": reason,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "handoff_type": "warm",
            },
        }
