"""Database module: MongoDB connection and utilities."""

from .connection import get_db, get_client, close_client, DB_NAME
from .indexes import create_indexes
from .user_plan_sync import sync_user_active_plan

__all__ = [
    "get_db",
    "get_client",
    "close_client",
    "DB_NAME",
    "create_indexes",
    "sync_user_active_plan",
]
