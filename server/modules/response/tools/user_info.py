"""Tool for retrieving user information."""

from typing import Dict, Any

from pydantic import BaseModel, Field

from db.connection import get_db
from .base import BaseTool


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Make MongoDB doc JSON-serializable (datetime, ObjectId)."""
    if doc is None:
        return {}
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    for key, val in list(out.items()):
        if hasattr(val, "isoformat"):
            out[key] = val.isoformat()
    return out


class GetUserInfoTool(BaseTool):
    """Retrieve user information by user ID."""

    name: str = "getUserInfo"
    description: str = "Retrieves user information including their name, phone number, profile details, preferences, and account status. Use this when the user asks about their name, account, profile, or personal information."
    
    class UserInfoInput(BaseModel):
        """Input schema for getUserInfo tool."""

        userId: str = Field(..., description="The unique identifier of the user")

    args_schema = UserInfoInput

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute getUserInfo tool.

        Args:
            userId: The unique identifier of the user.

        Returns:
            Dictionary containing user information.
        """
        try:
            user_id = kwargs.get("userId") or kwargs.get("user_id")
            if not user_id:
                return {
                    "status": "error",
                    "data": {"message": "userId is required"},
                }
            db = get_db()
            user = await db.users.find_one({"user_id": user_id})
            if not user:
                return {
                    "status": "not_found",
                    "data": {"userId": user_id, "message": "User not found"},
                }
            data = _serialize_doc(user)
            data.pop("password_hash", None)
            
            # Prefer embedded active_plan (single-doc read); fall back to subscriptions collection
            if data.get("active_plan") is not None:
                data.setdefault("subscriptions", [data["active_plan"]])
            else:
                subscriptions = []
                async for sub in db.subscriptions.find({"user_id": user_id}):
                    subscriptions.append(_serialize_doc(sub))
                data["subscriptions"] = subscriptions
            
            # Fetch vehicle info if user has one
            vehicle_id = user.get("vehicle_id")
            if vehicle_id:
                vehicle = await db.vehicles.find_one({"vehicle_id": vehicle_id})
                if vehicle:
                    data["vehicle"] = _serialize_doc(vehicle)
            
            # Fetch current battery info if user has one assigned
            battery_id = user.get("battery_id")
            if battery_id:
                battery = await db.batteries.find_one({"battery_id": battery_id})
                if battery:
                    battery_data = _serialize_doc(battery)
                    # Include health percentage for easy reading
                    battery_data["health_percent"] = int(battery.get("battery_health", 0) * 100)
                    # Check for any pending issues
                    issues = battery.get("issues", [])
                    battery_data["pending_issues"] = [
                        _serialize_doc(i) for i in issues 
                        if isinstance(i, dict) and i.get("status") == "pending"
                    ]
                    data["current_battery"] = battery_data
            
            return {"status": "ok", "data": data}
        except Exception as e:
            return {
                "status": "error",
                "data": {"userId": kwargs.get("userId"), "error": str(e)},
            }
