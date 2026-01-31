"""Tool for geocoding addresses to coordinates."""

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field

from .base import BaseTool


# Lazy import to avoid circular dependencies
def _get_geocoding_service():
    """Get geocoding service instance."""
    from services.geocoding.geocoding_service import get_geocoding_service
    return get_geocoding_service()


class GeocodeAddressInput(BaseModel):
    """Input schema for geocodeAddress tool."""
    
    address: str = Field(
        ..., 
        description="The address or location name to convert to coordinates (e.g., 'Andheri Station', 'Mumbai Central', 'Connaught Place')"
    )
    city: Optional[str] = Field(
        default=None,
        description="Optional city name for better accuracy (e.g., 'Mumbai', 'Delhi')"
    )
    state: Optional[str] = Field(
        default=None,
        description="Optional state name for better accuracy (e.g., 'Maharashtra', 'Delhi')"
    )


class GeocodeAddressTool(BaseTool):
    """
    Convert a user-provided address/location to geographical coordinates.
    
    Use this tool when:
    - The user is calling via phone (Twilio) and their GPS location is unavailable
    - You need to find coordinates for a location the user mentioned
    - You need coordinates to find the nearest station to a user's specified location
    """
    
    name: str = "geocodeAddress"
    description: str = """Converts a user-provided address or location name to geographical coordinates (latitude, longitude).
Use this tool when:
1. User's GPS location is not available (e.g., phone call via Twilio)
2. User mentions a specific location where they want to find nearest stations
3. You need to convert a spoken location to coordinates

IMPORTANT: For phone callers, first ASK the user for their location, then use this tool to get coordinates.
After getting coordinates, you can use getNearestStation with these coordinates."""
    
    args_schema = GeocodeAddressInput
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute geocodeAddress tool.
        
        Args:
            address: The address/location to geocode
            city: Optional city for context
            state: Optional state for context
            
        Returns:
            Dictionary containing coordinates and address info.
        """
        address = kwargs.get("address")
        city = kwargs.get("city")
        state = kwargs.get("state")
        
        if not address:
            return {
                "status": "error",
                "data": {"message": "address is required"},
            }
        
        try:
            geocoding_service = _get_geocoding_service()
            
            # Use Indian-specific geocoding for better results
            result = await geocoding_service.geocode_indian_location(
                location=address,
                city=city,
                state=state,
            )
            
            if not result:
                return {
                    "status": "not_found",
                    "data": {
                        "address": address,
                        "message": f"Could not find coordinates for '{address}'. Please ask the user to provide a more specific location or nearby landmark.",
                    },
                }
            
            return {
                "status": "ok",
                "data": {
                    "address": address,
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                    "formatted_address": result.get("display_name"),
                    "message": f"Found location: {result.get('display_name', address)} at coordinates ({result['latitude']}, {result['longitude']})",
                },
            }
            
        except Exception as e:
            return {
                "status": "error",
                "data": {
                    "address": address,
                    "error": str(e),
                    "message": "Failed to geocode address. Please try with a different location description.",
                },
            }


class ReverseGeocodeInput(BaseModel):
    """Input schema for reverseGeocode tool."""
    
    latitude: float = Field(..., description="The latitude of the location")
    longitude: float = Field(..., description="The longitude of the location")


class ReverseGeocodeTool(BaseTool):
    """Convert coordinates to a human-readable address."""
    
    name: str = "reverseGeocode"
    description: str = """Converts geographical coordinates to a human-readable address.
Use this when you have coordinates but need to tell the user the address in a friendly format."""
    
    args_schema = ReverseGeocodeInput
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute reverseGeocode tool.
        
        Args:
            latitude: The latitude
            longitude: The longitude
            
        Returns:
            Dictionary containing the address.
        """
        latitude = kwargs.get("latitude")
        longitude = kwargs.get("longitude")
        
        if latitude is None or longitude is None:
            return {
                "status": "error",
                "data": {"message": "latitude and longitude are required"},
            }
        
        try:
            geocoding_service = _get_geocoding_service()
            
            result = await geocoding_service.reverse_geocode(
                latitude=latitude,
                longitude=longitude,
            )
            
            if not result:
                return {
                    "status": "not_found",
                    "data": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "message": f"Could not find address for coordinates ({latitude}, {longitude})",
                    },
                }
            
            return {
                "status": "ok",
                "data": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "address": result.get("display_name"),
                    "address_components": result.get("address", {}),
                    "message": f"Location: {result.get('display_name', 'Unknown')}",
                },
            }
            
        except Exception as e:
            return {
                "status": "error",
                "data": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "error": str(e),
                },
            }
