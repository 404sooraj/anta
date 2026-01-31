"""Tools for retrieving service center/station information."""

import math
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

from db.connection import get_db
from .base import BaseTool


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees)
        lat2, lon2: Latitude and longitude of point 2 (in degrees)
    
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


class ServiceCenterInput(BaseModel):
    """Input schema for getLastServiceCenterVisit tool."""
    userId: str = Field(..., description="The unique identifier of the user")


class NearestStationInput(BaseModel):
    """Input schema for getNearestStation tool."""
    userId: str = Field(..., description="The unique identifier of the user")
    requireAvailableBatteries: bool = Field(
        default=False, 
        description="If true, only return stations that have batteries available for swap"
    )
    latitude: Optional[float] = Field(
        default=None,
        description="Optional explicit latitude. Use this when user provides their location verbally (e.g., phone calls). Takes precedence over user's stored location."
    )
    longitude: Optional[float] = Field(
        default=None,
        description="Optional explicit longitude. Use this when user provides their location verbally (e.g., phone calls). Takes precedence over user's stored location."
    )


class GetLastServiceCenterVisitTool(BaseTool):
    """Get details about the last service center visit for a user."""
    
    name: str = "getLastServiceCenterVisit"
    description: str = "Retrieves information about the user's last visit to a service center, including date, location, services performed, and any issues reported. Use this when the user asks about their service center visit history."
    args_schema = ServiceCenterInput
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute getLastServiceCenterVisit tool.
        
        Args:
            userId: The unique identifier of the user.
            
        Returns:
            Dictionary containing last service center visit information.
        """
        userId = kwargs.get("userId")
        if not userId:
            return {
                "status": "error",
                "data": {"message": "userId is required"},
            }
        # Placeholder implementation
        return {
            "status": "not_implemented",
            "data": {
                "userId": userId,
                "message": "getLastServiceCenterVisit tool is not yet implemented"
            }
        }


class GetNearestStationTool(BaseTool):
    """Find the nearest battery swap station to the user's current location."""
    
    name: str = "getNearestStation"
    description: str = """Finds the nearest battery swap station. This tool automatically fetches the user's stored location - you do NOT need to call getCurrentLocation first.

Use this tool DIRECTLY when user asks about:
- Nearest/closest swap station ("Nearest station kahan hai?")
- Where to swap battery ("Battery kahan swap karun?")
- Finding a station nearby
- Stations with available batteries

For web/app users: Just pass userId - location is fetched automatically.
For phone callers (Twilio): Pass latitude and longitude explicitly after using geocodeAddress."""
    args_schema = NearestStationInput
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute getNearestStation tool.
        
        Args:
            userId: The unique identifier of the user.
            requireAvailableBatteries: If true, filter to stations with available batteries.
            latitude: Optional explicit latitude (for phone calls where GPS unavailable).
            longitude: Optional explicit longitude (for phone calls where GPS unavailable).
            
        Returns:
            Dictionary containing nearest station information.
        """
        userId = kwargs.get("userId")
        require_available = kwargs.get("requireAvailableBatteries", False)
        explicit_lat = kwargs.get("latitude")
        explicit_lon = kwargs.get("longitude")
        
        if not userId:
            return {
                "status": "error",
                "data": {"message": "userId is required"},
            }
        
        try:
            db = get_db()
            
            # Use explicit coordinates if provided (for Twilio calls)
            if explicit_lat is not None and explicit_lon is not None:
                user_lat = explicit_lat
                user_lon = explicit_lon
                user_address = "User-provided location"
            else:
                # Get user's stored location
                user = await db.users.find_one(
                    {"user_id": userId},
                    {"location": 1}
                )
                
                if not user:
                    return {
                        "status": "error",
                        "data": {"message": f"User {userId} not found"},
                    }
                
                user_location = user.get("location")
                if not user_location or not user_location.get("coordinates"):
                    return {
                        "status": "error",
                        "data": {
                            "message": "User's location is not available. Please ask the user for their location and use geocodeAddress tool to get coordinates.",
                        },
                    }
                
                # User coordinates (GeoJSON format: [longitude, latitude])
                user_coords = user_location.get("coordinates", [])
                user_lon = user_coords[0] if len(user_coords) > 0 else None
                user_lat = user_coords[1] if len(user_coords) > 1 else None
                user_address = user_location.get("address")
                
                if user_lat is None or user_lon is None:
                    return {
                        "status": "error",
                        "data": {"message": "Invalid user location coordinates"},
                    }
            
            # Get all stations (exclude offline stations by default)
            query = {"status": {"$ne": "offline"}}  # Only show available stations
            if require_available:
                query["available_batteries"] = {"$gt": 0}
            
            stations_cursor = db.stations.find(query)
            stations = await stations_cursor.to_list(length=None)
            
            if not stations:
                if require_available:
                    return {
                        "status": "ok",
                        "data": {
                            "message": "No stations with available batteries found in our network.",
                            "nearest_station": None,
                        },
                    }
                return {
                    "status": "ok",
                    "data": {
                        "message": "No stations found in our network.",
                        "nearest_station": None,
                    },
                }
            
            # Calculate distance to each station and find nearest
            stations_with_distance: List[Dict[str, Any]] = []
            
            for station in stations:
                station_location = station.get("location", {})
                station_coords = station_location.get("coordinates", [])
                
                if len(station_coords) >= 2:
                    station_lon = station_coords[0]
                    station_lat = station_coords[1]
                    
                    distance_km = haversine_distance(
                        user_lat, user_lon, station_lat, station_lon
                    )
                    
                    stations_with_distance.append({
                        "station_id": station.get("station_id"),
                        "name": station.get("name"),
                        "available_batteries": station.get("available_batteries", 0),
                        "total_capacity": station.get("total_capacity", 0),
                        "status": station.get("status", "unknown"),
                        "distance_km": round(distance_km, 2),
                        "latitude": station_lat,
                        "longitude": station_lon,
                    })
            
            if not stations_with_distance:
                return {
                    "status": "ok",
                    "data": {
                        "message": "No stations with valid location data found.",
                        "nearest_station": None,
                    },
                }
            
            # Sort by distance
            stations_with_distance.sort(key=lambda x: x["distance_km"])
            
            nearest = stations_with_distance[0]
            
            # Build response message
            if require_available:
                message = (
                    f"The nearest station with available batteries is {nearest['name']}, "
                    f"which is {nearest['distance_km']} km away and has {nearest['available_batteries']} batteries available."
                )
            else:
                message = (
                    f"The nearest station is {nearest['name']}, "
                    f"which is {nearest['distance_km']} km away."
                )
                if nearest['available_batteries'] > 0:
                    message += f" It has {nearest['available_batteries']} batteries available."
                else:
                    message += " However, it currently has no batteries available."
                    # Also find nearest with batteries if different
                    available_stations = [s for s in stations_with_distance if s['available_batteries'] > 0]
                    if available_stations:
                        nearest_available = available_stations[0]
                        if nearest_available['station_id'] != nearest['station_id']:
                            message += (
                                f" The nearest station with available batteries is {nearest_available['name']}, "
                                f"{nearest_available['distance_km']} km away with {nearest_available['available_batteries']} batteries."
                            )
            
            return {
                "status": "ok",
                "data": {
                    "message": message,
                    "nearest_station": nearest,
                    "all_nearby_stations": stations_with_distance[:5],  # Return top 5 nearest
                    "user_location": {
                        "latitude": user_lat,
                        "longitude": user_lon,
                        "address": user_address if 'user_address' in dir() else None,
                    },
                },
            }
            
        except Exception as e:
            return {
                "status": "error",
                "data": {"error": str(e)},
            }
