"""Seed MongoDB with minimal mock data for users, stations, batteries, subscriptions."""

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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from db.connection import get_db
from db.indexes import create_indexes

DATA_DIR = Path(__file__).resolve().parent.parent / "seed-data"
CREDENTIALS_FILE = DATA_DIR / "_generated_credentials.json"


def _load_json(filename: str) -> List[Dict[str, Any]]:
	path = DATA_DIR / filename
	with path.open("r", encoding="utf-8") as file:
		return json.load(file)


def _hash_password(password: str) -> str:
	"""Hash password using bcrypt."""
	return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _normalize_subscription(sub: Dict[str, Any]) -> Dict[str, Any]:
	if "valid_till" not in sub:
		days = int(sub.get("valid_till_days", 90))
		valid_till = datetime.now(timezone.utc) + timedelta(days=days)
		sub["valid_till"] = valid_till.isoformat()
	sub.pop("valid_till_days", None)
	return sub


async def _upsert_many(collection, items: List[Dict[str, Any]], unique_key: str) -> int:
	upserts = 0
	for item in items:
		result = await collection.replace_one({unique_key: item[unique_key]}, item, upsert=True)
		if result.upserted_id is not None:
			upserts += 1
	return upserts


async def main() -> None:
	logger.info("="*70)
	logger.info("STARTING SEED SCRIPT")
	logger.info("="*70)
	
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
		# mongodb+srv://user:pass@host -> mongodb+srv://***:***@host
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
	# await create_indexes(db)

	logger.info("📥 Loading data files...")
	users = _load_json("users.json")
	stations = _load_json("stations.json")
	batteries = _load_json("batteries.json")
	subscriptions = [_normalize_subscription(s) for s in _load_json("subscriptions.json")]
	logger.info(f"   Loaded {len(users)} users, {len(stations)} stations, {len(batteries)} batteries, {len(subscriptions)} subscriptions")

	logger.info("🔐 Hashing passwords for users...")
	# Hash passwords for users and save credentials
	user_credentials: List[Dict[str, str]] = []
	for user in users:
		plain_password = user.pop("password", None)
		if plain_password:
			logger.debug(f"   Hashing password for user {user['user_id']}")
			user["password_hash"] = _hash_password(plain_password)
			user_credentials.append({
				"user_id": user["user_id"],
				"name": user["name"],
				"phone_number": user["phone_number"],
				"password": plain_password,
			})
	logger.info(f"✅ Hashed passwords for {len(user_credentials)} users")

	logger.info("📝 Updating users with active_plan snapshots...")
	# Update users with active_plan snapshot for quick reads
	subscriptions_by_user = {sub["user_id"]: sub for sub in subscriptions}
	for user in users:
		sub = subscriptions_by_user.get(user["user_id"])
		if sub:
			user["active_plan"] = {
				"plan": sub["plan"],
				"valid_till": sub["valid_till"],
				"status": sub["status"],
			}
	logger.info("✅ Active plans updated")

	logger.info("💾 Upserting data to MongoDB...")
	logger.info("   Upserting users...")
	created_users = await _upsert_many(db.users, users, "user_id")
	logger.info(f"   ✅ Users: {created_users}/{len(users)} upserted")
	
	logger.info("   Upserting stations...")
	created_stations = await _upsert_many(db.stations, stations, "station_id")
	logger.info(f"   ✅ Stations: {created_stations}/{len(stations)} upserted")
	
	logger.info("   Upserting batteries...")
	created_batteries = await _upsert_many(db.batteries, batteries, "battery_id")
	logger.info(f"   ✅ Batteries: {created_batteries}/{len(batteries)} upserted")
	
	logger.info("   Upserting subscriptions...")
	created_subscriptions = await _upsert_many(db.subscriptions, subscriptions, "subscription_id")
	logger.info(f"   ✅ Subscriptions: {created_subscriptions}/{len(subscriptions)} upserted")

	logger.info(f"💾 Saving credentials to {CREDENTIALS_FILE}...")
	# Save generated credentials to file for dev reference
	with CREDENTIALS_FILE.open("w", encoding="utf-8") as f:
		json.dump(user_credentials, f, indent=2)
	logger.info("✅ Credentials saved")

	logger.info("="*70)
	logger.info("✅ SEED COMPLETE")
	logger.info("="*70)
	print(f"\n📊 Summary:")
	print(f"   Users upserted: {created_users}/{len(users)}")
	print(f"   Stations upserted: {created_stations}/{len(stations)}")
	print(f"   Batteries upserted: {created_batteries}/{len(batteries)}")
	print(f"   Subscriptions upserted: {created_subscriptions}/{len(subscriptions)}")
	print(f"\n🔐 Generated credentials saved to: {CREDENTIALS_FILE}")
	print("⚠️  Keep this file secure and do not commit to version control!")
	print()


if __name__ == "__main__":
	asyncio.run(main())
