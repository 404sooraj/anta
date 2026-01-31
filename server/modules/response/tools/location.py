"""Tool for retrieving current user location."""

from typing import Dict, Any

from pydantic import BaseModel, Field

from db.connection import get_db
from .base import BaseTool


class LocationInput(BaseModel):
    """Input schema for getCurrentLocation tool."""
    userId: str = Field(..., description="The unique identifier of the user")


class GetCurrentLocationTool(BaseTool):
    """Get the current location of a user by user ID."""

    name: str = "getCurrentLocation"
    description: str = "Retrieves the current geographical location (latitude, longitude, address) of a user based on their user ID. Use this when the user asks about their location or where they are."
    args_schema = LocationInput

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute getCurrentLocation tool.

        Args:
            userId: The unique identifier of the user.

        Returns:
            Dictionary containing location information.
        """
        userId = kwargs.get("userId")
        if not userId:
            return {
                "status": "error",
                "data": {"message": "userId is required"},
            }
        try:
            db = get_db()
            user = await db.users.find_one(
                {"user_id": userId},
                {"user_id": 1, "location": 1},
            )
            if not user:
                return {
                    "status": "not_found",
                    "data": {
                        "userId": userId,
                        "location": None,
                        "message": "User not found",
                    },
                }
            location = user.get("location")
            if not location:
                return {
                    "status": "ok",
                    "data": {
                        "userId": userId,
                        "location": None,
                        "message": "No location on file",
                    },
                }
            return {
                "status": "ok",
                "data": {"userId": userId, "location": location},
            }
        except Exception as e:
            return {
                "status": "error",
                "data": {"userId": userId, "error": str(e)},
            }
