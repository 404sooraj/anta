"""Location routes for updating and retrieving user location."""

from datetime import datetime, timezone
from typing import Optional
import logging

import httpx
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel
import jwt

from db.connection import get_db
from modules.config import ConfigEnv

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/location", tags=["location"])


class LocationUpdate(BaseModel):
    """Request body for updating user location."""
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    address: Optional[str] = None  # Optional - backend will geocode if not provided


class LocationResponse(BaseModel):
    """Response for location operations."""
    status: str
    message: str
    location: Optional[dict] = None


async def reverse_geocode(latitude: float, longitude: float) -> Optional[str]:
    """
    Perform reverse geocoding using geocode.maps.co API.
    Returns a human-readable address or None if geocoding fails.
    """
    api_key = ConfigEnv.GEOCODING_API_KEY
    if not api_key:
        logger.warning("GEOCODING_API_KEY not configured, skipping reverse geocoding")
        return None
    
    try:
        url = f"https://geocode.maps.co/reverse?lat={latitude}&lon={longitude}&api_key={api_key}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.warning(f"Geocoding API returned status {response.status_code}")
                return None
            
            data = response.json()
            
            if "error" in data:
                logger.warning(f"Geocoding API error: {data['error']}")
                return None
            
            # Get the display_name which contains the full address
            address = data.get("display_name")
            if address:
                logger.info(f"Reverse geocoded location: {address[:50]}...")
                return address
            
            return None
    except Exception as e:
        logger.error(f"Reverse geocoding failed: {e}")
        return None


def get_user_id_from_token(authorization: Optional[str]) -> Optional[str]:
    """Extract user_id from JWT token in Authorization header."""
    if not authorization:
        return None
    
    try:
        # Handle "Bearer <token>" format
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
        
        secret = ConfigEnv.AUTH_JWT_SECRET
        if not secret:
            return None
        
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None


@router.post("/update", response_model=LocationResponse)
async def update_location(
    location: LocationUpdate,
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> LocationResponse:
    """
    Update the current location of a user.
    
    The user can be identified via:
    1. JWT token in Authorization header
    2. X-User-ID header
    """
    # Get user_id from token or header
    authenticated_user_id = get_user_id_from_token(authorization)
    final_user_id = authenticated_user_id or user_id
    
    if not final_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identification required (token or X-User-ID header)",
        )
    
    try:
        db = get_db()
        
        # If address not provided, do reverse geocoding
        address = location.address
        if not address:
            logger.info(f"No address provided, performing reverse geocoding for ({location.latitude}, {location.longitude})")
            address = await reverse_geocode(location.latitude, location.longitude)
        
        # Build location document with GeoJSON format for MongoDB geospatial queries
        location_doc = {
            "type": "Point",
            "coordinates": [location.longitude, location.latitude],  # GeoJSON: [lng, lat]
            "accuracy": location.accuracy,
            "address": address,
            "updated_at": datetime.now(timezone.utc),
        }
        
        # Update user's location
        result = await db.users.update_one(
            {"user_id": final_user_id},
            {"$set": {"location": location_doc}},
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {final_user_id} not found",
            )
        
        return LocationResponse(
            status="ok",
            message="Location updated successfully",
            location={
                "latitude": location.latitude,
                "longitude": location.longitude,
                "accuracy": location.accuracy,
                "address": address,
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update location: {str(e)}",
        )


@router.get("/current", response_model=LocationResponse)
async def get_current_location(
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> LocationResponse:
    """
    Get the current location of a user.
    """
    authenticated_user_id = get_user_id_from_token(authorization)
    final_user_id = authenticated_user_id or user_id
    
    if not final_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identification required",
        )
    
    try:
        db = get_db()
        user = await db.users.find_one(
            {"user_id": final_user_id},
            {"location": 1},
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {final_user_id} not found",
            )
        
        location = user.get("location")
        if not location:
            return LocationResponse(
                status="ok",
                message="No location on file",
                location=None,
            )
        
        # Convert from GeoJSON format to lat/lng
        coords = location.get("coordinates", [])
        return LocationResponse(
            status="ok",
            message="Location retrieved successfully",
            location={
                "latitude": coords[1] if len(coords) > 1 else None,
                "longitude": coords[0] if len(coords) > 0 else None,
                "accuracy": location.get("accuracy"),
                "address": location.get("address"),
                "updated_at": location.get("updated_at"),
            },
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get location: {str(e)}",
        )
