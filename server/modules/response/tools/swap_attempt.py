"""Tool for retrieving last swap attempt information."""

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
    return out


class SwapAttemptInput(BaseModel):
    """Input schema for getLastSwapAttempt tool."""
    userId: str = Field(..., description="The unique identifier of the user")


class GetLastSwapAttemptTool(BaseTool):
    """Get information about the last swap attempt for a user."""

    name: str = "getLastSwapAttempt"
    description: str = "Retrieves details about the user's last battery swap attempt, including timestamp, status, location, and any errors or issues encountered. Use this when the user asks about their swap history or a recent swap."
    args_schema = SwapAttemptInput

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute getLastSwapAttempt tool.

        Args:
            userId: The unique identifier of the user.

        Returns:
            Dictionary containing last swap attempt information.
        """
        userId = kwargs.get("userId")
        if not userId:
            return {
                "status": "error",
                "data": {"message": "userId is required"},
            }
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
            # Use embedded station_snapshot when present (single-doc read); else fall back to stations lookup
            if swap.get("station_snapshot") is not None:
                data["station"] = _serialize_doc(swap["station_snapshot"])
            else:
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
