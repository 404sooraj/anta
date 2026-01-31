"""MongoDB connection using Motor (async driver)."""

import os
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

DB_NAME = "antaryami"

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    """Return the global Motor client. Creates it if not yet connected."""
    global _client
    if _client is None:
        url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        _client = AsyncIOMotorClient(url)
        logger.info("MongoDB client created")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Return the database instance. Uses get_client() if needed."""
    global _db
    if _db is None:
        _db = get_client()[DB_NAME]
    return _db


def close_client() -> None:
    """Close the global Motor client. Called on app shutdown."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB client closed")
