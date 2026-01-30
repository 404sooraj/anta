"""
Quick test script to verify the API structure
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"


async def test_endpoints():
    """Test all API endpoints"""
    async with httpx.AsyncClient() as client:
        print("🧪 Testing BatterySmart API\n")
        
        # Test root endpoint
        print("1️⃣ Testing root endpoint...")
        response = await client.get(f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # Test STT health
        print("2️⃣ Testing STT health...")
        response = await client.get(f"{BASE_URL}/stt/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # Test text health
        print("3️⃣ Testing text processing health...")
        response = await client.get(f"{BASE_URL}/api/text/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # Test text processing
        print("4️⃣ Testing text processing...")
        response = await client.post(
            f"{BASE_URL}/api/text/process",
            json={"text": "Hello, what can you help me with?"}
        )
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Response: {result.get('response', '')[:100]}...")
        print(f"   Intent: {result.get('intent', {}).get('intent', 'unknown')}")
        print(f"   Tools used: {result.get('tool_calls', [])}\n")
        
        print("✅ All tests completed!")


if __name__ == "__main__":
    print("Make sure the server is running: uv run main.py\n")
    asyncio.run(test_endpoints())
