"""Battery API: PUT to update battery and append issues (classification & storage in DB)."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batteries", tags=["batteries"])


class BatteryIssueIn(BaseModel):
    """Issue to append to a battery document."""

    type: str
    classification: str
    details: Optional[str] = None


class BatteryPutBody(BaseModel):
    """Body for PUT /api/batteries/{battery_id}."""

    station_id: Optional[str] = None
    issues: Optional[List[BatteryIssueIn]] = None  # append to embedded issues array


def _serialize_doc(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Make MongoDB doc JSON-serializable."""
    if doc is None:
        return {}
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    for key, val in list(out.items()):
        if hasattr(val, "isoformat"):
            out[key] = val.isoformat()
    return out


@router.put("/{battery_id}")
async def put_battery(battery_id: str, request: Request, body: Optional[BatteryPutBody] = None):
    """
    Create or update a battery document. Append issues to embedded issues array.
    No separate battery_issues collection; issues live inside the battery document.
    """
    db = request.app.state.db
    if body is None:
        body = BatteryPutBody()

    set_fields: Dict[str, Any] = {}
    if body.station_id is not None:
        set_fields["station_id"] = body.station_id

    new_issues: List[Dict[str, Any]] = []
    if body.issues:
        now = datetime.now(timezone.utc)
        new_issues = [
            {
                "type": i.type,
                "classification": i.classification,
                "reported_at": now,
                "details": i.details,
            }
            for i in body.issues
        ]

    existing = await db.batteries.find_one({"battery_id": battery_id})
    if existing:
        update_op: Dict[str, Any] = {}
        if set_fields:
            update_op["$set"] = set_fields
        if new_issues:
            update_op["$push"] = {"issues": {"$each": new_issues}}
        if update_op:
            await db.batteries.update_one(
                {"battery_id": battery_id},
                update_op,
            )
    else:
        # Create new battery document
        doc: Dict[str, Any] = {
            "battery_id": battery_id,
            "issues": new_issues if new_issues else [],
        }
        if body.station_id is not None:
            doc["station_id"] = body.station_id
        await db.batteries.insert_one(doc)

    battery = await db.batteries.find_one({"battery_id": battery_id})
    return {"status": "ok", "data": _serialize_doc(battery)}


@router.get("/{battery_id}")
async def get_battery(battery_id: str, request: Request):
    """Get battery document by battery_id."""
    db = request.app.state.db
    battery = await db.batteries.find_one({"battery_id": battery_id})
    if not battery:
        return {"status": "not_found", "data": {"battery_id": battery_id, "message": "Battery not found"}}
    return {"status": "ok", "data": _serialize_doc(battery)}
