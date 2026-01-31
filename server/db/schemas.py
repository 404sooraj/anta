"""Pydantic schemas for MongoDB collections."""

from datetime import datetime
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# GeoJSON Point for station location (2dsphere index)
class GeoPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: List[float]  # [longitude, latitude]


class User(BaseModel):
    """User document."""

    user_id: str
    name: str
    phone_number: str
    password_hash: Optional[str] = None  # bcrypt hashed password
    language: str = "en"
    location: Optional[Union[str, dict[str, Any]]] = None  # last known or preferred; str or GeoJSON
    active_plan: Optional["ActivePlan"] = None  # denormalized snapshot; updated when subscription changes


class ActivePlan(BaseModel):
    """Embedded snapshot of active subscription on user document."""
    plan: str
    valid_till: datetime
    status: str
    renewal_info: Optional[str] = None



class Station(BaseModel):
    """Station document."""

    station_id: str
    name: str
    location: Union[GeoPoint, dict[str, Any]]  # GeoJSON Point for 2dsphere
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


class StationSnapshot(BaseModel):
    """Embedded snapshot of station on swap document (avoids join at read time)."""

    name: str
    location: Optional[Union[GeoPoint, dict[str, Any]]] = None


class Swap(BaseModel):
    """Swap document."""

    swap_id: str
    user_id: str
    station_id: str
    date: datetime
    amount: int = 1
    station_snapshot: Optional[StationSnapshot] = None  # denormalized; set when swap is written


class BatteryIssue(BaseModel):
    """Embedded issue on battery document (no separate battery_issues collection)."""

    type: str
    classification: str
    reported_at: datetime
    details: Optional[str] = None


class Battery(BaseModel):
    """Battery document with embedded issues."""

    battery_id: str
    station_id: Optional[str] = None
    issues: List[BatteryIssue] = Field(default_factory=list)
