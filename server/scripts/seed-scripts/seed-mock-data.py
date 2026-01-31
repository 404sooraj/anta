"""Seed MongoDB with minimal mock data for users, stations, batteries, subscriptions.

This script will:
1. Delete all existing data from collections
2. Insert fresh seed data matching the updated schema
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import bcrypt
from dotenv import load_dotenv

# Add server directory to path for imports
SERVER_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SERVER_DIR))

# Load .env file from server directory
env_path = SERVER_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from db.connection import get_db

DATA_DIR = Path(__file__).resolve().parent.parent / "seed-data"
CREDENTIALS_FILE = DATA_DIR / "_generated_credentials.json"

# Collections to seed (and clear)
COLLECTIONS = [
    "users",
    "stations",
    "batteries",
    "subscriptions",
    "swaps",
    "conversations",
    "agents",
]


def _load_json(filename: str) -> List[Dict[str, Any]]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _parse_datetime(value: str) -> datetime:
    """Parse ISO datetime string to datetime object."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _add_timestamps(item: Dict[str, Any]) -> Dict[str, Any]:
    """Add created_at, updated_at, deleted_at timestamps to item."""
    now = datetime.now(timezone.utc)
    item["created_at"] = now
    item["updated_at"] = None
    item["deleted_at"] = None
    return item


def _normalize_subscription(sub: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize subscription data to match schema."""
    # Handle validity - convert string to datetime if needed
    if "validity" in sub and isinstance(sub["validity"], str):
        sub["validity"] = _parse_datetime(sub["validity"])
    elif "valid_till_days" in sub:
        days = int(sub.pop("valid_till_days", 90))
        sub["validity"] = datetime.now(timezone.utc) + timedelta(days=days)

    # Ensure price is float
    if "price" in sub:
        sub["price"] = float(sub["price"])

    return _add_timestamps(sub)


def _normalize_battery(battery: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize battery data to match schema."""
    # Parse issue timestamps
    if "issues" in battery:
        for issue in battery["issues"]:
            if "reported_at" in issue and isinstance(issue["reported_at"], str):
                issue["reported_at"] = _parse_datetime(issue["reported_at"])
            # Ensure status field exists
            if "status" not in issue:
                issue["status"] = "pending"

    # Ensure battery_health is float between 0 and 1
    if "battery_health" in battery:
        battery["battery_health"] = float(battery["battery_health"])

    # Ensure capacity is int
    if "capacity" in battery:
        battery["capacity"] = int(battery["capacity"])

    return _add_timestamps(battery)


def _normalize_station(station: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize station data to match schema."""
    # Ensure available_batteries and total_capacity are ints
    if "available_batteries" in station:
        station["available_batteries"] = int(station["available_batteries"])
    if "total_capacity" in station:
        station["total_capacity"] = int(station["total_capacity"])

    # Default status if not provided
    if "status" not in station:
        station["status"] = "available"

    return _add_timestamps(station)


def _normalize_swap(swap: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize swap data to match schema."""
    # Parse date
    if "date" in swap and isinstance(swap["date"], str):
        swap["date"] = _parse_datetime(swap["date"])

    # Ensure amount is int
    if "amount" in swap:
        swap["amount"] = int(swap["amount"])

    # Ensure battery_available_count is int
    if "battery_available_count" in swap:
        swap["battery_available_count"] = int(swap["battery_available_count"])

    return swap


def _normalize_user(
    user: Dict[str, Any], subscriptions_by_user: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Normalize user data to match schema."""
    # Hash password
    plain_password = user.pop("password", None)
    if plain_password:
        user["password_hash"] = _hash_password(plain_password)
    else:
        user["password_hash"] = None

    # Add active_plan from subscription if exists
    sub = subscriptions_by_user.get(user["user_id"])
    if sub:
        user["active_plan"] = {
            "plan": sub["plan"],
            "valid_till": sub["validity"],
            "status": "active"
            if sub["validity"] > datetime.now(timezone.utc)
            else "expired",
        }
    else:
        user["active_plan"] = None

    return _add_timestamps(user)


async def _delete_all_data(db) -> Dict[str, int]:
    """Delete all data from collections and return counts."""
    deleted_counts = {}
    for collection_name in COLLECTIONS:
        collection = getattr(db, collection_name, None)
        if collection is not None:
            result = await collection.delete_many({})
            deleted_counts[collection_name] = result.deleted_count
            logger.info(
                f"   🗑️  Deleted {result.deleted_count} documents from {collection_name}"
            )
    return deleted_counts


async def _insert_many(collection, items: List[Dict[str, Any]]) -> int:
    """Insert many documents and return count."""
    if not items:
        return 0
    result = await collection.insert_many(items)
    return len(result.inserted_ids)


async def main() -> None:
    logger.info("=" * 70)
    logger.info("STARTING SEED SCRIPT")
    logger.info("=" * 70)

    # Log environment configuration
    logger.info(f"📂 Server directory: {SERVER_DIR}")
    logger.info(f"📂 Data directory: {DATA_DIR}")
    logger.info(f"📂 .env file path: {SERVER_DIR / '.env'}")
    logger.info(f"📂 .env file exists: {(SERVER_DIR / '.env').exists()}")

    # Log MongoDB configuration
    mongodb_url = os.getenv("MONGODB_URL", "NOT_SET")
    if mongodb_url == "NOT_SET":
        logger.error("❌ MONGODB_URL environment variable is not set!")
        logger.error("   Make sure .env file exists and contains MONGODB_URL")
        sys.exit(1)

    # Hide password in logs for security
    if "@" in mongodb_url and "://" in mongodb_url:
        parts = mongodb_url.split("://")
        if len(parts) == 2:
            scheme = parts[0]
            rest = parts[1]
            if "@" in rest:
                creds, host = rest.split("@", 1)
                safe_url = f"{scheme}://***:***@{host}"
            else:
                safe_url = mongodb_url
        else:
            safe_url = mongodb_url
    else:
        safe_url = mongodb_url

    logger.info(f"🔗 MongoDB URL: {safe_url}")
    logger.info(f"🔗 Connecting to MongoDB...")

    db = get_db()
    logger.info("✅ Database connection obtained")

    # Step 1: Delete all existing data
    logger.info("")
    logger.info("🗑️  DELETING ALL EXISTING DATA...")
    logger.info("-" * 70)
    deleted_counts = await _delete_all_data(db)
    total_deleted = sum(deleted_counts.values())
    logger.info(f"✅ Deleted {total_deleted} total documents")

    # Step 2: Load and normalize data
    logger.info("")
    logger.info("📥 LOADING AND NORMALIZING DATA FILES...")
    logger.info("-" * 70)

    # Load raw data
    raw_users = _load_json("users.json")
    raw_stations = _load_json("stations.json")
    raw_batteries = _load_json("batteries.json")
    raw_subscriptions = _load_json("subscriptions.json")
    raw_swaps = _load_json("swaps.json")
    raw_agents = _load_json("agents.json")

    logger.info(
        f"   Loaded {len(raw_users)} users, {len(raw_stations)} stations, {len(raw_batteries)} batteries, {len(raw_subscriptions)} subscriptions, {len(raw_swaps)} swaps, {len(raw_agents)} agents"
    )

    # Normalize subscriptions first (needed for user active_plan)
    logger.info("   Normalizing subscriptions...")
    subscriptions = [_normalize_subscription(s) for s in raw_subscriptions]
    subscriptions_by_user = {sub["user_id"]: sub for sub in subscriptions}

    # Normalize stations
    logger.info("   Normalizing stations...")
    stations = [_normalize_station(s) for s in raw_stations]

    # Normalize batteries
    logger.info("   Normalizing batteries...")
    batteries = [_normalize_battery(b) for b in raw_batteries]

    # Normalize swaps
    logger.info("   Normalizing swaps...")
    swaps = [_normalize_swap(s) for s in raw_swaps]

    # Agents don't have timestamps in schema, use as-is
    logger.info("   Loading agents...")
    agents = raw_agents

    # Normalize users (includes password hashing and active_plan)
    logger.info("🔐 Hashing passwords and normalizing users...")
    user_credentials: List[Dict[str, str]] = []
    users = []
    for raw_user in raw_users:
        # Save credentials before hashing
        if "password" in raw_user:
            user_credentials.append(
                {
                    "user_id": raw_user["user_id"],
                    "name": raw_user["name"],
                    "phone_number": raw_user["phone_number"],
                    "password": raw_user["password"],
                }
            )
        users.append(_normalize_user(raw_user.copy(), subscriptions_by_user))

    # Reload raw users for processing since we modified them
    raw_users = _load_json("users.json")
    users = []
    for raw_user in raw_users:
        users.append(_normalize_user(raw_user, subscriptions_by_user))

    logger.info(f"✅ Normalized all data")

    # Step 3: Insert new data
    logger.info("")
    logger.info("💾 INSERTING NEW DATA TO MONGODB...")
    logger.info("-" * 70)

    logger.info("   Inserting users...")
    created_users = await _insert_many(db.users, users)
    logger.info(f"   ✅ Users: {created_users} inserted")

    logger.info("   Inserting stations...")
    created_stations = await _insert_many(db.stations, stations)
    logger.info(f"   ✅ Stations: {created_stations} inserted")

    logger.info("   Inserting batteries...")
    created_batteries = await _insert_many(db.batteries, batteries)
    logger.info(f"   ✅ Batteries: {created_batteries} inserted")

    logger.info("   Inserting subscriptions...")
    created_subscriptions = await _insert_many(db.subscriptions, subscriptions)
    logger.info(f"   ✅ Subscriptions: {created_subscriptions} inserted")

    logger.info("   Inserting swaps...")
    created_swaps = await _insert_many(db.swaps, swaps)
    logger.info(f"   ✅ Swaps: {created_swaps} inserted")

    logger.info("   Inserting agents...")
    created_agents = await _insert_many(db.agents, agents)
    logger.info(f"   ✅ Agents: {created_agents} inserted")

    # Step 4: Save credentials
    logger.info("")
    logger.info(f"💾 Saving credentials to {CREDENTIALS_FILE}...")
    with CREDENTIALS_FILE.open("w", encoding="utf-8") as f:
        json.dump(user_credentials, f, indent=2)
    logger.info("✅ Credentials saved")

    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ SEED COMPLETE")
    logger.info("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   Deleted:")
    for collection_name, count in deleted_counts.items():
        if count > 0:
            print(f"      - {collection_name}: {count} documents")
    print(f"   Inserted:")
    print(f"      - Users: {created_users}")
    print(f"      - Stations: {created_stations}")
    print(f"      - Batteries: {created_batteries}")
    print(f"      - Subscriptions: {created_subscriptions}")
    print(f"      - Swaps: {created_swaps}")
    print(f"      - Agents: {created_agents}")
    print(f"\n🔐 Generated credentials saved to: {CREDENTIALS_FILE}")
    print("⚠️  Keep this file secure and do not commit to version control!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
