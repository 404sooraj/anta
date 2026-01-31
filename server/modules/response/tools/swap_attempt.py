"""Tool for retrieving last swap attempt information."""

from typing import Dict, Any

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
    return out


class GetLastSwapAttemptTool(BaseTool):
    """Get information about the last swap attempt for a user."""

    name: str = "getLastSwapAttempt"
    description: str = "Retrieves details about the user's last swap attempt, including timestamp, status, location, and any errors or issues encountered."

    async def execute(self, userId: str) -> Dict[str, Any]:
        """
        Execute getLastSwapAttempt tool.

        Args:
            userId: The unique identifier of the user.

        Returns:
            Dictionary containing last swap attempt information.
        """
        try:
            db = get_db()
            swap = await db.swaps.find_one(
                {"user_id": userId},
                sort=[("date", -1)],
            )
            if not swap:
                return {
                    "status": "not_found",
                    "data": {
                        "userId": userId,
                        "message": "No swap attempts found",
                    },
                }
            data = _serialize_doc(swap)
            station_id = swap.get("station_id")
            if station_id:
                station = await db.stations.find_one({"station_id": station_id})
                if station:
                    data["station"] = _serialize_doc(station)
            return {"status": "ok", "data": data}
        except Exception as e:
            return {
                "status": "error",
                "data": {"userId": userId, "error": str(e)},
            }
