"""Tool for reporting battery issues."""

from datetime import datetime, timezone
from typing import Dict, Any

from pydantic import BaseModel, Field

from db.connection import get_db
from .base import BaseTool

# Import classifier - using function import to avoid circular dependency
def _get_classifier():
    from modules.response.tools.battery_issue_classifier import get_battery_issue_classifier
    return get_battery_issue_classifier()


class ReportBatteryIssueInput(BaseModel):
    """Input schema for reportBatteryIssue tool."""
    userId: str = Field(..., description="The unique identifier of the user")
    issueDescription: str = Field(
        ..., 
        description="The user's description of the battery issue they are experiencing"
    )


class ReportBatteryIssueTool(BaseTool):
    """Report and classify a battery issue from user complaint."""

    name: str = "reportBatteryIssue"
    description: str = """IMPORTANT: Use this tool when the user COMPLAINS about or REPORTS a battery problem.

This is for recording complaints like:
- "Battery is getting hot/heating/garam" (overheating complaint)
- "Battery not charging" (charging problem)
- "Battery drains fast" (discharge complaint)  
- "Battery is swollen/damaged" (physical issue)
- Any sentence where user says their battery HAS a problem

DO NOT use getBatteryInfo for complaints - use THIS tool instead.
getBatteryInfo is only for when user ASKS about battery status/health.

Pass the user's exact complaint text as issueDescription."""
    args_schema = ReportBatteryIssueInput

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute reportBatteryIssue tool.

        Args:
            userId: The unique identifier of the user.
            issueDescription: Description of the battery issue.

        Returns:
            Dictionary containing the result of the issue report.
        """
        userId = kwargs.get("userId")
        issue_description = kwargs.get("issueDescription", "")
        
        if not userId:
            return {
                "status": "error",
                "data": {"message": "userId is required"},
            }
        
        if not issue_description:
            return {
                "status": "error",
                "data": {"message": "Issue description is required"},
            }
        
        try:
            db = get_db()
            
            # Get user to find their battery_id
            user = await db.users.find_one(
                {"user_id": userId},
                {"battery_id": 1, "user_id": 1, "name": 1}
            )
            
            if not user:
                return {
                    "status": "error",
                    "data": {"message": f"User {userId} not found"},
                }
            
            battery_id = user.get("battery_id")
            if not battery_id:
                return {
                    "status": "error",
                    "data": {
                        "message": "No battery is currently assigned to this user. Cannot report an issue without an assigned battery.",
                        "suggestion": "Please swap for a battery first, or contact support if you believe this is an error.",
                    },
                }
            
            # Verify battery exists
            battery = await db.batteries.find_one({"battery_id": battery_id})
            if not battery:
                return {
                    "status": "error",
                    "data": {
                        "message": f"Battery {battery_id} not found in system.",
                        "suggestion": "Please contact support for assistance.",
                    },
                }
            
            # Classify the issue
            classifier = _get_classifier()
            classification_result = await classifier.classify(issue_description)
            
            # Create the issue document
            issue_doc = {
                "classification": classification_result["classification"],
                "reported_at": datetime.now(timezone.utc),
                "details": issue_description,
                "status": "pending",
                # Additional metadata
                "reported_by": userId,
                "classification_confidence": classification_result.get("confidence", 0),
                "classification_method": classification_result.get("method", "unknown"),
            }
            
            # Add issue to battery's issues array
            result = await db.batteries.update_one(
                {"battery_id": battery_id},
                {
                    "$push": {"issues": issue_doc},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                }
            )
            
            if result.modified_count == 0:
                return {
                    "status": "error",
                    "data": {"message": "Failed to record the issue. Please try again."},
                }
            
            # Check if this is a critical issue that needs immediate attention
            critical_categories = [
                "overheating", "swelling", "leakage", "physical_damage"
            ]
            is_critical = classification_result["classification"] in critical_categories
            
            # Build response message
            category_display = classification_result["classification"].replace("_", " ").title()
            
            if is_critical:
                message = (
                    f"⚠️ SAFETY ALERT: Your battery issue has been recorded as '{category_display}'. "
                    f"This is a critical issue. Please stop using the battery immediately and "
                    f"visit the nearest service center or swap station for assistance. "
                    f"Your safety is our priority."
                )
            else:
                message = (
                    f"Your battery issue has been recorded successfully. "
                    f"Issue category: {category_display}. "
                    f"Our team will review this and take appropriate action. "
                    f"Reference Battery ID: {battery_id}."
                )
            
            return {
                "status": "ok",
                "data": {
                    "message": message,
                    "issue_recorded": True,
                    "battery_id": battery_id,
                    "classification": classification_result["classification"],
                    "classification_display": category_display,
                    "is_critical": is_critical,
                    "reported_at": issue_doc["reported_at"].isoformat(),
                    "issue_status": "pending",
                },
            }
            
        except Exception as e:
            return {
                "status": "error",
                "data": {"error": str(e)},
            }
