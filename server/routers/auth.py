"""Authentication routes for basic prototype login."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from db.connection import get_db
from modules.config import ConfigEnv

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    identifier: str
    password: str


class UserResponse(BaseModel):
    user_id: str
    name: str
    phone_number: Optional[str] = None
    email: Optional[str] = None


class LoginResponse(BaseModel):
    user: UserResponse
    token: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    db = get_db()
    user = await db.users.find_one(
        {
            "$or": [
                {"phone_number": request.identifier},
                {"user_id": request.identifier},
                {"email": request.identifier},
            ]
        }
    )

    if not user or not user.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not bcrypt.checkpw(
        request.password.encode("utf-8"), user["password_hash"].encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    secret = ConfigEnv.AUTH_JWT_SECRET or ""
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH_JWT_SECRET is not configured",
        )

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.get("user_id", ""),
        "name": user.get("name", ""),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=12)).timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")

    return LoginResponse(
        user=UserResponse(
            user_id=user.get("user_id", ""),
            name=user.get("name", ""),
            phone_number=user.get("phone_number"),
            email=user.get("email"),
        ),
        token=token,
    )
