"""Tool for retrieving battery information."""

from typing import Dict, Any

from pydantic import BaseModel, Field

from db.connection import get_db
from .base import BaseTool


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Make MongoDB doc JSON-serializable."""
    if doc is None:
        return {}
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    for key, val in list(out.items()):
        if hasattr(val, "isoformat"):
            out[key] = val.isoformat()
        elif isinstance(val, list):
            out[key] = [_serialize_doc(item) if isinstance(item, dict) else item for item in val]
    return out


class BatteryInfoInput(BaseModel):
    """Input schema for getBatteryInfo tool."""
    userId: str = Field(..., description="The unique identifier of the user")


class GetBatteryInfoTool(BaseTool):
    """Get information about the user's current battery."""

    name: str = "getBatteryInfo"
    description: str = """Retrieves detailed information about the user's currently assigned battery, 
including battery health, capacity, type, and any reported issues.
Use this when the user asks about:
- Their battery status or health
- Battery issues or problems
- Battery capacity or type
- Whether their battery needs service"""
    args_schema = BatteryInfoInput

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute getBatteryInfo tool.

        Args:
            userId: The unique identifier of the user.

        Returns:
            Dictionary containing battery information.
        """
        userId = kwargs.get("userId")
        if not userId:
            return {
                "status": "error",
                "data": {"message": "userId is required"},
            }
        
        try:
            db = get_db()
            
            # First get user to find their battery_id
            user = await db.users.find_one(
                {"user_id": userId},
                {"battery_id": 1, "user_id": 1}
            )
            
            if not user:
                return {
                    "status": "not_found",
                    "data": {"userId": userId, "message": "User not found"},
                }
            
            battery_id = user.get("battery_id")
            if not battery_id:
                return {
                    "status": "ok",
                    "data": {
                        "userId": userId,
                        "battery": None,
                        "message": "No battery currently assigned to this user. They may need to swap for a new battery.",
                    },
                }
            
            # Fetch battery details
            battery = await db.batteries.find_one({"battery_id": battery_id})
            if not battery:
                return {
                    "status": "ok",
                    "data": {
                        "userId": userId,
                        "battery_id": battery_id,
                        "message": f"Battery {battery_id} not found in system.",
                    },
                }
            
            battery_data = _serialize_doc(battery)
            
            # Calculate health percentage
            health = battery.get("battery_health", 0)
            health_percent = int(health * 100)
            battery_data["health_percent"] = health_percent
            
            # Analyze health status
            if health >= 0.9:
                health_status = "excellent"
            elif health >= 0.75:
                health_status = "good"
            elif health >= 0.5:
                health_status = "fair"
            else:
                health_status = "poor"
            battery_data["health_status"] = health_status
            
            # Check for pending issues
            issues = battery.get("issues", [])
            pending_issues = [
                _serialize_doc(i) for i in issues 
                if isinstance(i, dict) and i.get("status") == "pending"
            ]
            battery_data["pending_issues"] = pending_issues
            battery_data["has_pending_issues"] = len(pending_issues) > 0
            
            # Build user-friendly message
            message_parts = [f"Your battery ({battery_id}) has {health_percent}% health ({health_status})."]
            
            if battery.get("status") == "offline":
                message_parts.append("⚠️ This battery is currently marked as offline and may need service.")
            
            if pending_issues:
                issue_details = [i.get("classification", "unknown issue") for i in pending_issues]
                message_parts.append(f"There are pending issues: {', '.join(issue_details)}.")
            
            if health < 0.75:
                message_parts.append("Consider swapping for a healthier battery soon.")
            
            battery_data["message"] = " ".join(message_parts)
            
            return {
                "status": "ok",
                "data": {
                    "userId": userId,
                    "battery": battery_data,
                    "message": battery_data["message"],
                },
            }
            
        except Exception as e:
            return {
                "status": "error",
                "data": {"userId": userId, "error": str(e)},
            }
