from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional

import jwt
from db.connection import get_db
from modules.config import ConfigEnv

from routers.auth import UserResponse

router = APIRouter(prefix="/api/user", tags=["user"])


def _decode_token(authorization: Optional[str]) -> Optional[dict]:
    """Decode JWT from Authorization header using AUTH_JWT_SECRET. Returns payload or None."""
    if not authorization:
        return None
    try:
        token = authorization[7:] if authorization.startswith("Bearer ") else authorization
        secret = ConfigEnv.AUTH_JWT_SECRET
        if not secret:
            return None
        return jwt.decode(token, secret, algorithms=["HS256"])
    except Exception:
        return None


@router.get("/me", response_model=UserResponse)
async def me(authorization: Optional[str] = Header(None)) -> UserResponse:
    """
    Return the current user from the JWT in the Authorization header.
    Validates the token with AUTH_JWT_SECRET and returns user_id and name from the payload;
    optionally enriches with phone_number and email from the database.
    """
    payload = _decode_token(authorization)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization token",
        )
    user_id = payload.get("sub") or ""
    name = payload.get("name") or ""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )
    db = get_db()
    user = await db.users.find_one({"user_id": user_id})
    if user:
        return UserResponse(
            user_id=user.get("user_id", user_id),
            name=user.get("name", name),
            phone_number=user.get("phone_number"),
            email=user.get("email"),
        )
    return UserResponse(user_id=user_id, name=name, phone_number=None, email=None)
