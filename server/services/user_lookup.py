"""
User lookup service for identifying users by phone number.
Used primarily for Twilio calls where we need to identify the caller.
"""
import logging
import re
from typing import Optional, Dict, Any

from db.connection import get_db

logger = logging.getLogger(__name__)


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to a standard format for matching.
    
    Examples:
        "+919876543210" -> "919876543210"
        "+91 98765 43210" -> "919876543210"
        "09876543210" -> "9876543210"
        "9876543210" -> "9876543210"
        
    Args:
        phone: The phone number to normalize
        
    Returns:
        Normalized phone number (digits only)
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Remove leading zeros
    digits_only = digits_only.lstrip('0')
    
    return digits_only


async def lookup_user_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Look up a user by their phone number.
    
    Args:
        phone_number: The phone number to search for (Twilio format: +919876543210)
        
    Returns:
        User document if found, None otherwise
    """
    if not phone_number:
        logger.warning("Empty phone number provided for lookup")
        return None
    
    try:
        db = get_db()
        
        # Try exact match first
        user = await db.users.find_one(
            {"phone_number": phone_number},
            {"password_hash": 0}  # Exclude password
        )
        
        if user:
            logger.info(f"Found user by exact phone match: {user.get('user_id')}")
            return user
        
        # Normalize phone number and try matching
        normalized = normalize_phone_number(phone_number)
        logger.info(f"Trying normalized phone lookup: {normalized}")
        
        # Search for users whose normalized phone matches
        # Use regex to match the last N digits (for partial matching)
        if len(normalized) >= 10:
            # Try matching the last 10 digits
            last_10 = normalized[-10:]
            
            # Find users where phone ends with these digits
            regex_pattern = f".*{last_10}$"
            user = await db.users.find_one(
                {"phone_number": {"$regex": regex_pattern}},
                {"password_hash": 0}
            )
            
            if user:
                logger.info(f"Found user by phone suffix match: {user.get('user_id')}")
                return user
        
        # Try with country code variations
        # If input is 919876543210, also try +919876543210
        variations = [
            phone_number,
            f"+{normalized}",
            f"+91{normalized[-10:]}" if len(normalized) >= 10 else None,
            normalized,
            normalized[-10:] if len(normalized) >= 10 else None,
        ]
        
        for variant in variations:
            if variant:
                user = await db.users.find_one(
                    {"phone_number": variant},
                    {"password_hash": 0}
                )
                if user:
                    logger.info(f"Found user with phone variant '{variant}': {user.get('user_id')}")
                    return user
        
        logger.info(f"No user found for phone number: {phone_number}")
        return None
        
    except Exception as e:
        logger.error(f"Error looking up user by phone: {e}")
        return None


async def get_user_id_from_phone(phone_number: str) -> Optional[str]:
    """
    Get just the user_id from a phone number.
    
    Args:
        phone_number: The phone number to search for
        
    Returns:
        user_id if found, None otherwise
    """
    user = await lookup_user_by_phone(phone_number)
    if user:
        return user.get("user_id")
    return None


async def create_anonymous_twilio_user(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Create an anonymous user record for a Twilio caller if they don't exist.
    
    This allows the system to track conversations for unknown callers
    and potentially link them to an account later.
    
    Args:
        phone_number: The caller's phone number
        
    Returns:
        The created or existing user document, or None on error
    """
    from datetime import datetime, timezone
    import uuid
    
    try:
        db = get_db()
        
        # Generate anonymous user_id
        user_id = f"twilio_anon_{uuid.uuid4().hex[:8]}"
        
        user_doc = {
            "user_id": user_id,
            "name": f"Twilio Caller ({phone_number[-4:]})",  # Last 4 digits for reference
            "phone_number": phone_number,
            "password_hash": None,  # No password for anonymous users
            "location": None,
            "active_plan": None,
            "vehicle_id": None,
            "battery_id": None,
            "is_anonymous": True,
            "source": "twilio",
            "created_at": datetime.now(timezone.utc),
        }
        
        await db.users.insert_one(user_doc)
        logger.info(f"Created anonymous Twilio user: {user_id}")
        
        return user_doc
        
    except Exception as e:
        logger.error(f"Error creating anonymous Twilio user: {e}")
        return None
