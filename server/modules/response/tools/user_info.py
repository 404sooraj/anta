"""Tool for retrieving user information."""

from typing import Dict, Any

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
    description: str = "Retrieves user information including profile details, preferences, and account status for a given user ID."

    async def execute(self, userId: str) -> Dict[str, Any]:
        """
        Execute getUserInfo tool.

        Args:
            userId: The unique identifier of the user.

        Returns:
            Dictionary containing user information.
        """
        try:
            db = get_db()
            user = await db.users.find_one({"user_id": userId})
            if not user:
                return {
                    "status": "not_found",
                    "data": {"userId": userId, "message": "User not found"},
                }
            subscriptions = []
            async for sub in db.subscriptions.find({"user_id": userId}):
                subscriptions.append(_serialize_doc(sub))
            data = _serialize_doc(user)
            data["subscriptions"] = subscriptions
            return {"status": "ok", "data": data}
        except Exception as e:
            return {
                "status": "error",
                "data": {"userId": userId, "error": str(e)},
            }
