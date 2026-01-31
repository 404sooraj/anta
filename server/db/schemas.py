from __future__ import annotations

from datetime import datetime, timezone
from site import USER_BASE
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, Field


class MongoModel(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")


# GeoJSON Point for station location (2dsphere index)
class GeoPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: list[float]  # [longitude, latitude]


class ActivePlan(BaseModel):
    """Embedded snapshot of active subscription on user document."""

    plan: str
    valid_till: datetime
    status: Literal["active", "expired", "cancelled"]


class User(BaseModel):
    """User document."""

    user_id: str
    name: str
    phone_number: str
    password_hash: str | None = None
    location: GeoPoint | None = None
    active_plan: ActivePlan | None = None
    vehicle_id: str | None = None
    battery_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    deleted_at: datetime | None = None  # soft delete


class Station(BaseModel):
    """Station document."""

    station_id: str
    name: str
    location: GeoPoint
    available_batteries: int = 0
    total_capacity: int = 0
    status: Literal["available", "offline"] = "available"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    deleted_at: datetime | None = None  # soft delete


class Conversation(BaseModel):
    """Conversation (session) document."""

    session_id: str
    user_id: str
    agent_id: str | None = None
    language: str = "en"
    start_time: datetime
    end_time: datetime | None = None
    outcome: Literal["resolved", "handoff"] | None = None
    summary: str | None = None
    handoff_reason: str | None = None
    score: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    deleted_at: datetime | None = None  # soft delete


class Agent(BaseModel):
    agent_id: str
    name: str


class Subscription(BaseModel):
    user_id: str
    subscription_id: str
    plan: str
    price: float
    validity: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    deleted_at: datetime | None = None  # soft delete


class Swap(BaseModel):
    swap_id: str
    user_id: str
    station_id: str
    date: datetime
    amount: int = 1
    battery_available_count: (
        int  # available count of batteries at the station during the swap
    )
    battery_id_taken: str | None = None
    battery_id_returned: str | None = None
    status: Literal["pending", "completed", "cancelled"] = "pending"


class BatteryIssue(BaseModel):
    classification: str
    reported_at: datetime
    details: str | None = None
    status: Literal["pending", "resolved", "cancelled"] = "pending"


class Battery(BaseModel):
    battery_id: str
    station_id: str | None = None
    issues: list[BatteryIssue] = Field(default_factory=list)
    battery_type: str
    capacity: int = 0
    status: Literal["available", "offline"] = "available"
    battery_health: float = Field(ge=0, le=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    deleted_at: datetime | None = None  # soft delete


# from datetime import datetime, timezone

# from pydantic import BaseModel, Field


class GlobalPricing(BaseModel):
    pricing_id: str = "GLOBAL_V1"

    base_swap_price: int = 170
    secondary_swap_price: int = 70

    service_charge_per_swap: int = 40

    free_leave_days_per_month: int = 4
    leave_penalty_amount: int = 120
    penalty_recovery_per_swap: int = 60

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
