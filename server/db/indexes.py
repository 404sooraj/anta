"""Create MongoDB indexes for query patterns and uniqueness."""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Create indexes on all collections. Idempotent (create_index with same spec is safe).
    """
    # users: unique on user_id (we use user_id as _id or as separate field)
    await db.users.create_index("user_id", unique=True)
    logger.info("Index users.user_id created")

    # stations: unique on station_id
    await db.stations.create_index("station_id", unique=True)
    logger.info("Index stations.station_id created")

    # conversations: index on user_id and start_time
    await db.conversations.create_index("session_id", unique=True)
    await db.conversations.create_index("user_id")
    await db.conversations.create_index("start_time")
    logger.info("Indexes conversations.* created")

    # agents: unique on agent_id
    await db.agents.create_index("agent_id", unique=True)
    logger.info("Index agents.agent_id created")

    # intent_logs: index on session_id
    await db.intent_logs.create_index("intent_id", unique=True)
    await db.intent_logs.create_index("session_id")
    logger.info("Indexes intent_logs.* created")

    # subscriptions: index on user_id, status
    await db.subscriptions.create_index("subscription_id", unique=True)
    await db.subscriptions.create_index("user_id")
    await db.subscriptions.create_index("status")
    logger.info("Indexes subscriptions.* created")

    # handoffs: index on session_id, agent_id
    await db.handoffs.create_index("handoff_id", unique=True)
    await db.handoffs.create_index("session_id")
    await db.handoffs.create_index("agent_id")
    logger.info("Indexes handoffs.* created")

    # swaps: index on user_id, station_id, date
    await db.swaps.create_index("swap_id", unique=True)
    await db.swaps.create_index("user_id")
    await db.swaps.create_index("station_id")
    await db.swaps.create_index("date")
    logger.info("Indexes swaps.* created")
