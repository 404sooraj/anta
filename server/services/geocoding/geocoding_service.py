"""
Geocoding Service - Address to Coordinates Conversion
Uses geocode.maps.co API for forward and reverse geocoding
"""
import logging
from typing import Optional, Dict, Any
import httpx

from modules.config import ConfigEnv

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for converting addresses to coordinates and vice versa."""
    
    BASE_URL = "https://geocode.maps.co"
    
    def __init__(self):
        """Initialize geocoding service with API key."""
        self.api_key = ConfigEnv.GEOCODING_API_KEY
        if not self.api_key:
            logger.warning("GEOCODING_API_KEY not set - geocoding will not work")
    
    async def forward_geocode(
        self, 
        address: str,
        timeout: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """
        Convert an address to coordinates (forward geocoding).
        
        Args:
            address: The address to geocode (e.g., "Mumbai Central", "Andheri Station")
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary containing:
            - latitude: Latitude of the location
            - longitude: Longitude of the location
            - display_name: Full formatted address
            - place_id: Unique place identifier
            
            Returns None if geocoding fails or no results found.
        """
        if not self.api_key:
            logger.error("Geocoding API key not configured")
            return None
        
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                "q": address,
                "api_key": self.api_key,
                "format": "json",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                
                results = response.json()
                
                if not results:
                    logger.info(f"No geocoding results for address: {address}")
                    return None
                
                # Return the first (most relevant) result
                first_result = results[0]
                
                return {
                    "latitude": float(first_result.get("lat")),
                    "longitude": float(first_result.get("lon")),
                    "display_name": first_result.get("display_name"),
                    "place_id": first_result.get("place_id"),
                    "type": first_result.get("type"),
                    "importance": first_result.get("importance"),
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Geocoding API HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Geocoding API timeout for address: {address}")
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        timeout: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """
        Convert coordinates to an address (reverse geocoding).
        
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary containing:
            - display_name: Full formatted address
            - address: Structured address components
            - place_id: Unique place identifier
            
            Returns None if reverse geocoding fails.
        """
        if not self.api_key:
            logger.error("Geocoding API key not configured")
            return None
        
        try:
            url = f"{self.BASE_URL}/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "api_key": self.api_key,
                "format": "json",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                
                result = response.json()
                
                if not result or "error" in result:
                    logger.info(f"No reverse geocoding results for: {latitude}, {longitude}")
                    return None
                
                return {
                    "display_name": result.get("display_name"),
                    "address": result.get("address", {}),
                    "place_id": result.get("place_id"),
                    "latitude": float(result.get("lat", latitude)),
                    "longitude": float(result.get("lon", longitude)),
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Reverse geocoding API HTTP error: {e.response.status_code}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Reverse geocoding API timeout for: {latitude}, {longitude}")
            return None
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return None
    
    async def geocode_indian_location(
        self,
        location: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Geocode an Indian location with optional city/state context.
        
        Adds "India" to the query for better results.
        
        Args:
            location: The location name (e.g., "Andheri Station", "Mumbai Central")
            city: Optional city name for better accuracy
            state: Optional state name for better accuracy
            
        Returns:
            Geocoding result dictionary or None if not found.
        """
        # Build search query with context
        parts = [location]
        if city:
            parts.append(city)
        if state:
            parts.append(state)
        parts.append("India")
        
        full_query = ", ".join(parts)
        
        return await self.forward_geocode(full_query)


# Singleton instance
_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Get the singleton geocoding service instance."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
