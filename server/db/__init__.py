"""Database module: MongoDB connection and utilities."""

from .connection import get_db, get_client, close_client, DB_NAME
from .indexes import create_indexes

__all__ = ["get_db", "get_client", "close_client", "DB_NAME", "create_indexes"]
