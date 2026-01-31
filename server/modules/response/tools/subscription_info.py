"""Tool for retrieving user subscription information."""

from datetime import datetime, timezone
from typing import Dict, Any

from pydantic import BaseModel, Field

from db.connection import get_db
from .base import BaseTool


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Make MongoDB doc JSON-serializable (datetime, ObjectId)."""
    if doc is None:
        return {}
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    for key, val in list(out.items()):
        if hasattr(val, "isoformat"):
            out[key] = val.isoformat()
    return out


class GetSubscriptionInfoInput(BaseModel):
    """Input schema for getSubscriptionInfo tool."""

    userId: str = Field(..., description="The unique identifier of the user")


class GetSubscriptionInfoTool(BaseTool):
    """Retrieve subscription information for a user."""

    name: str = "getSubscriptionInfo"
    description: str = """Retrieves the user's subscription/plan information including:
- Current active plan name and status
- Plan validity/expiry date
- Subscription history
- Payment/pricing details

Use this tool when the user asks about:
- Their subscription or plan ("मेरा प्लान क्या है?", "what is my plan?")
- Plan validity or expiry ("कब तक valid है?", "when does my plan expire?")
- Subscription status ("is my subscription active?")
- Plan renewal or pricing ("how much is my plan?", "kitna paisa lagta hai?")

DO NOT use for: Battery queries, swap history, or general account info."""
    args_schema = GetSubscriptionInfoInput

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute getSubscriptionInfo tool.

        Args:
            userId: The unique identifier of the user.

        Returns:
            Dictionary containing subscription information.
        """
        user_id = kwargs.get("userId") or kwargs.get("user_id")
        if not user_id:
            return {
                "status": "error",
                "data": {"message": "userId is required"},
            }

        try:
            db = get_db()
            
            # First check user's embedded active_plan
            user = await db.users.find_one(
                {"user_id": user_id},
                {"active_plan": 1, "user_id": 1, "name": 1}
            )
            
            if not user:
                return {
                    "status": "not_found",
                    "data": {"userId": user_id, "message": "User not found"},
                }
            
            result = {
                "userId": user_id,
                "userName": user.get("name", "Unknown"),
            }
            
            # Get active plan from embedded document
            active_plan = user.get("active_plan")
            if active_plan:
                now = datetime.now(timezone.utc)
                valid_till = active_plan.get("valid_till")
                
                # Check if plan is still valid
                is_expired = False
                days_remaining = None
                if valid_till:
                    if isinstance(valid_till, str):
                        valid_till = datetime.fromisoformat(valid_till.replace("Z", "+00:00"))
                    is_expired = valid_till < now
                    if not is_expired:
                        days_remaining = (valid_till - now).days
                
                result["activePlan"] = {
                    "plan": active_plan.get("plan"),
                    "status": "expired" if is_expired else active_plan.get("status", "active"),
                    "validTill": valid_till.isoformat() if hasattr(valid_till, "isoformat") else valid_till,
                    "daysRemaining": days_remaining,
                    "isExpired": is_expired,
                }
            else:
                result["activePlan"] = None
            
            # Get subscription history from subscriptions collection
            subscriptions = []
            async for sub in db.subscriptions.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(5):
                sub_data = _serialize_doc(sub)
                subscriptions.append({
                    "subscriptionId": sub_data.get("subscription_id"),
                    "plan": sub_data.get("plan"),
                    "price": sub_data.get("price"),
                    "validity": sub_data.get("validity"),
                    "createdAt": sub_data.get("created_at"),
                })
            
            result["subscriptionHistory"] = subscriptions
            result["totalSubscriptions"] = len(subscriptions)
            
            # Get global pricing info for reference
            pricing = await db.global_pricing.find_one({"pricing_id": "GLOBAL_V1"})
            if pricing:
                result["pricing"] = {
                    "baseSwapPrice": pricing.get("base_swap_price"),
                    "secondarySwapPrice": pricing.get("secondary_swap_price"),
                    "serviceChargePerSwap": pricing.get("service_charge_per_swap"),
                    "freeLeaveDaysPerMonth": pricing.get("free_leave_days_per_month"),
                    "leavePenaltyAmount": pricing.get("leave_penalty_amount"),
                }
            
            return {
                "status": "ok",
                "data": result,
            }

        except Exception as e:
            return {
                "status": "error",
                "data": {"message": f"Failed to fetch subscription info: {str(e)}"},
            }
