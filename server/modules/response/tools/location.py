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
    description: str = "Retrieves the current geographical location (latitude, longitude, address) of a user based on their user ID. Use this when the user asks about their location, where they are, or their current position."
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
                        "message": "No location on file for this user",
                    },
                }
            
            # Extract coordinates from GeoJSON format
            coords = location.get("coordinates", [])
            longitude = coords[0] if len(coords) > 0 else None
            latitude = coords[1] if len(coords) > 1 else None
            address = location.get("address")
            
            # Build user-friendly location data
            location_data = {
                "latitude": latitude,
                "longitude": longitude,
                "accuracy_meters": location.get("accuracy"),
                "address": address,
                "updated_at": location.get("updated_at").isoformat() if location.get("updated_at") else None,
            }
            
            # Build descriptive message for the AI to use in response
            if address:
                message = f"The user is currently located at: {address}"
            elif latitude and longitude:
                message = f"The user's coordinates are: latitude {latitude}, longitude {longitude} (no address available)"
            else:
                message = "Location coordinates are incomplete"
            
            return {
                "status": "ok",
                "data": {
                    "userId": userId,
                    "location": location_data,
                    "message": message,
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "data": {"userId": userId, "error": str(e)},
            }
