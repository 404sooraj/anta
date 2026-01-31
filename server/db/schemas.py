from __future__ import annotations

from datetime import datetime, timezone
from site import USER_BASE
from typing import Literal, Optional

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict


class PyObjectId(ObjectId):
    """Custom type for handling MongoDB ObjectId in Pydantic models."""
    
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ])
        ], serialization=core_schema.plain_serializer_function_ser_schema(str))
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")


class MongoModel(BaseModel):
    """Base model for MongoDB documents with ObjectId support."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Optional[PyObjectId] = Field(default=None, alias="_id")


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
    station_id: Optional[str] = None
    issues: List[BatteryIssue] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    """Individual message in a call transcript."""
    
    role: Literal["user", "assistant"]
    text: str
    timestamp: Optional[datetime] = None


class CallTranscript(BaseModel):
    """Complete call transcript with AI-generated summary and satisfaction score."""
    
    call_id: str  # Unique identifier for this call
    user_id: Optional[str] = None  # User who made the call (if authenticated)
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    
    # Conversation data
    messages: List[ConversationMessage] = Field(default_factory=list)
    detected_language: str = "en"
    
    # AI-generated insights
    summary: Optional[str] = None  # AI-generated summary of the conversation
    satisfaction_score: Optional[int] = Field(None, ge=1, le=5)  # 1-5 rating
    satisfaction_reasoning: Optional[str] = None  # Why this score was given
    
    # Call metadata
    call_source: Literal["web", "twilio"] = "web"  # Where the call came from
    twilio_call_sid: Optional[str] = None  # Twilio-specific identifier
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
