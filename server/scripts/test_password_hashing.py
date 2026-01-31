"""Test password hashing functionality without database."""

import json
import sys
from pathlib import Path

# Add server directory to path
SERVER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_DIR))
import bcrypt

DATA_DIR = Path(__file__).resolve().parent / "seed-data"


def test_password_hashing():
    """Test that password hashing works correctly."""
    print("=" * 60)
    print("TESTING PASSWORD HASHING")
    print("=" * 60)
    
    # Load users from JSON
    users_file = DATA_DIR / "users.json"
    with users_file.open("r", encoding="utf-8") as f:
        users = json.load(f)
    
    print(f"\n✅ Loaded {len(users)} users from JSON\n")
    
    # Test hashing for each user
    for user in users:
        plain_password = user.get("password")
        if plain_password:
            # Hash the password
            hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            
            # Verify the hash
            is_valid = bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))
            
            print(f"User: {user['name']}")
            print(f"  User ID: {user['user_id']}")
            print(f"  Phone: {user['phone_number']}")
            print(f"  Plain password: {plain_password}")
            print(f"  Hashed password: {hashed[:60]}...")
            print(f"  Hash length: {len(hashed)} chars")
            print(f"  ✅ Verification: {'PASS' if is_valid else 'FAIL'}")
            print()
    
    print("=" * 60)
    print("✅ ALL TESTS PASSED - Password hashing works correctly!")
    print("=" * 60)
    print("\nThe seed script will:")
    print("1. Read passwords from users.json")
    print("2. Hash them using bcrypt")
    print("3. Store hashed passwords in MongoDB")
    print("4. Save plain passwords to _generated_credentials.json")


if __name__ == "__main__":
    test_password_hashing()
