"""Create MongoDB indexes for query patterns and uniqueness."""

import logging
from typing import Any, List, Tuple

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


def _key_spec_matches(existing_key: List[Tuple[str, Any]], wanted_key: List[Tuple[str, Any]]) -> bool:
    """Return True if existing index key matches wanted key (order and direction)."""
    if len(existing_key) != len(wanted_key):
        return False
    return all(
        ek[0] == wk[0] and ek[1] == wk[1]
        for ek, wk in zip(existing_key, wanted_key)
    )


async def _index_with_spec_exists(
    coll: AsyncIOMotorCollection,
    keys: List[Tuple[str, Any]],
    *,
    unique: bool = False,
) -> bool:
    """
    Return True if an index with the same key (and unique option) already exists.
    Checks by key/spec so we skip creation when MongoDB has an index under a different name.
    """
    try:
        info = await coll.index_information()
    except Exception:
        return False
    for name, spec in info.items():
        if name == "_id_":
            continue
        existing_key = spec.get("key")
        if not existing_key:
            continue
        # index_information() returns key as list of (name, direction) e.g. [("user_id", 1)]
        key_list = list(existing_key.items()) if hasattr(existing_key, "items") else existing_key
        if not _key_spec_matches(key_list, keys):
            continue
        existing_unique = spec.get("unique", False)
        if existing_unique == unique:
            return True
    return False


async def _ensure_index(
    coll: AsyncIOMotorCollection,
    keys: List[Tuple[str, Any]],
    *,
    unique: bool = False,
    name: str,
) -> bool:
    """
    Create index only if one with the same key (and unique) does not exist.
    Return True if created, False if already existed (by any name).
    """
    if await _index_with_spec_exists(coll, keys, unique=unique):
        return False
    await coll.create_index(keys, unique=unique, name=name)
    return True


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Create indexes on all collections. Only creates when missing (Option B).
    Logs only when an index is actually created; ends with "Indexes ensured".
    """
    total_created = 0

    # users: unique on user_id; phone_number for Twilio user lookup
    c = 0
    if await _ensure_index(db.users, [("user_id", 1)], unique=True, name="user_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.users, [("phone_number", 1)], name="phone_number_1"):
        c += 1
        total_created += 1
    if c:
        logger.info("Index users.* created")

    # stations: unique on station_id; 2dsphere on location for nearest-station queries
    c = 0
    if await _ensure_index(db.stations, [("station_id", 1)], unique=True, name="station_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.stations, [("location", "2dsphere")], name="location_2dsphere"):
        c += 1
        total_created += 1
    if c:
        logger.info("Indexes stations.* created")

    # conversations: session_id unique, user_id, start_time
    c = 0
    if await _ensure_index(db.conversations, [("session_id", 1)], unique=True, name="session_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.conversations, [("user_id", 1)], name="user_id_1"):
        c += 1
        total_created += 1
    if await _ensure_index(db.conversations, [("start_time", 1)], name="start_time_1"):
        c += 1
        total_created += 1
    if c:
        logger.info("Indexes conversations.* created")

    # agents: unique on agent_id
    if await _ensure_index(db.agents, [("agent_id", 1)], unique=True, name="agent_id_unique"):
        total_created += 1
        logger.info("Index agents.agent_id created")

    # intent_logs: intent_id unique, session_id
    c = 0
    if await _ensure_index(db.intent_logs, [("intent_id", 1)], unique=True, name="intent_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.intent_logs, [("session_id", 1)], name="session_id_1"):
        c += 1
        total_created += 1
    if c:
        logger.info("Indexes intent_logs.* created")

    # subscriptions: subscription_id unique, user_id, status
    c = 0
    if await _ensure_index(db.subscriptions, [("subscription_id", 1)], unique=True, name="subscription_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.subscriptions, [("user_id", 1)], name="user_id_1"):
        c += 1
        total_created += 1
    if await _ensure_index(db.subscriptions, [("status", 1)], name="status_1"):
        c += 1
        total_created += 1
    if c:
        logger.info("Indexes subscriptions.* created")

    # handoffs: handoff_id unique, session_id, agent_id
    c = 0
    if await _ensure_index(db.handoffs, [("handoff_id", 1)], unique=True, name="handoff_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.handoffs, [("session_id", 1)], name="session_id_1"):
        c += 1
        total_created += 1
    if await _ensure_index(db.handoffs, [("agent_id", 1)], name="agent_id_1"):
        c += 1
        total_created += 1
    if c:
        logger.info("Indexes handoffs.* created")

    # swaps: swap_id unique, user_id, station_id, date
    c = 0
    if await _ensure_index(db.swaps, [("swap_id", 1)], unique=True, name="swap_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.swaps, [("user_id", 1)], name="user_id_1"):
        c += 1
        total_created += 1
    if await _ensure_index(db.swaps, [("station_id", 1)], name="station_id_1"):
        c += 1
        total_created += 1
    if await _ensure_index(db.swaps, [("date", 1)], name="date_1"):
        c += 1
        total_created += 1
    if c:
        logger.info("Indexes swaps.* created")

    # batteries: battery_id unique; station_id for query by station
    c = 0
    if await _ensure_index(db.batteries, [("battery_id", 1)], unique=True, name="battery_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.batteries, [("station_id", 1)], name="station_id_1"):
        c += 1
        total_created += 1
    if c:
        logger.info("Indexes batteries.* created")

    # call_transcripts: call_id unique, user_id for user query, start_time for chronological queries
    c = 0
    if await _ensure_index(db.call_transcripts, [("call_id", 1)], unique=True, name="call_id_unique"):
        c += 1
        total_created += 1
    if await _ensure_index(db.call_transcripts, [("user_id", 1)], name="user_id_1"):
        c += 1
        total_created += 1
    if await _ensure_index(db.call_transcripts, [("start_time", -1)], name="start_time_-1"):
        c += 1
        total_created += 1
    if await _ensure_index(db.call_transcripts, [("twilio_call_sid", 1)], name="twilio_call_sid_1"):
        c += 1
        total_created += 1
    if c:
        logger.info("Indexes call_transcripts.* created")

    logger.info("Indexes ensured for all collections (%s created this run)", total_created)
