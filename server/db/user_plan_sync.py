"""Sync user.active_plan when subscriptions are created or updated."""

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase


async def sync_user_active_plan(
    db: AsyncIOMotorDatabase,
    user_id: str,
    subscription_doc: Dict[str, Any],
) -> None:
    """
    Update user.active_plan from a subscription document.
    Call this when a subscription is created, renewed, or cancelled
    so getUserInfo can return plan from a single user document read.
    """
    active_plan = {
        "plan": subscription_doc.get("plan", ""),
        "valid_till": subscription_doc.get("valid_till"),
        "status": subscription_doc.get("status", ""),
        "renewal_info": subscription_doc.get("renewal_info"),
    }
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"active_plan": active_plan}},
    )
