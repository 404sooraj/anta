"""Pydantic schemas for MongoDB collections."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """User document."""

    user_id: str
    name: str
    phone_number: str
    language: str = "en"
    location: Optional[str] = None  # last known or preferred location for getCurrentLocation


class Station(BaseModel):
    """Station document."""

    station_id: str
    name: str
    location: str
    available_batteries: int = 0


class Conversation(BaseModel):
    """Conversation (session) document."""

    session_id: str
    user_id: str
    language: str = "en"
    start_time: datetime
    end_time: Optional[datetime] = None
    outcome: Optional[Literal["resolved", "handoff"]] = None


class Agent(BaseModel):
    """Agent document."""

    agent_id: str
    name: str


class IntentLog(BaseModel):
    """Intent log document (per turn)."""

    intent_id: str
    session_id: str
    intent_name: str
    confidence: float = Field(ge=0, le=1)


class Subscription(BaseModel):
    """Subscription document."""

    subscription_id: str
    user_id: str
    plan: str
    valid_till: datetime
    status: str


class Handoff(BaseModel):
    """Handoff document."""

    handoff_id: str
    session_id: str
    agent_id: str
    reason: str
    summary: Optional[str] = None


class Swap(BaseModel):
    """Swap document."""

    swap_id: str
    user_id: str
    station_id: str
    date: datetime
    amount: int = 1
