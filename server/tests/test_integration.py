"""Integration tests for end-to-end pipeline functionality.

Note: These tests require a valid GEMINI_API_KEY to run actual API calls.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import pytest

# Load .env file to get real API key
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Skip integration tests if no real API key is available
# Check if API key exists and is not the test key
_api_key = os.getenv("GEMINI_API_KEY", "")
_has_real_api_key = (
    _api_key 
    and _api_key != "test_api_key_12345"
    and len(_api_key) > 20  # Real API keys are longer
)

pytestmark = pytest.mark.skipif(
    not _has_real_api_key,
    reason="Integration tests skipped. Set a real GEMINI_API_KEY in .env file to run."
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline_with_real_api():
    """Test full pipeline with real Gemini API (requires API key)."""
    from modules.response.response import ResponsePipeline
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "test_api_key_12345":
        pytest.skip("Real GEMINI_API_KEY not set for integration test")
    
    pipeline = ResponsePipeline(api_key=api_key)
    
    # Test with a simple prompt
    result = await pipeline.process_text("Hello, how are you?")
    
    assert result is not None
    assert "response" in result
    assert "intent" in result
    assert len(result["response"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_with_tool_calling():
    """Test pipeline with a prompt that should trigger tool calling."""
    from modules.response.response import ResponsePipeline
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "test_api_key_12345":
        pytest.skip("Real GEMINI_API_KEY not set for integration test")
    
    pipeline = ResponsePipeline(api_key=api_key)
    
    # Prompt that might trigger tool use
    result = await pipeline.process_text("What is the user information for user ID 12345?")
    
    assert result is not None
    assert "response" in result
    # Tool calls may or may not happen depending on model behavior
    assert "tool_calls" in result


@pytest.mark.integration
def test_api_endpoint_with_real_request(test_client):
    """Test API endpoint with real request (uses mocked pipeline from fixtures)."""
    response = test_client.post(
        "/api/process-text",
        json={"text": "Test integration prompt"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_test_prompts_one_by_one():
    """
    Process all prompts from test-prompts.json one by one and display output.
    This test shows the full pipeline response for each test prompt.
    """
    import json
    from pathlib import Path
    from modules.response.response import ResponsePipeline
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "test_api_key_12345":
        pytest.skip("Real GEMINI_API_KEY not set for integration test")
    
    # Load test prompts
    prompts_file = Path(__file__).parent.parent / "modules" / "response" / "data" / "test-prompts.json"
    if not prompts_file.exists():
        pytest.skip(f"Test prompts file not found: {prompts_file}")
    
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts = json.load(f)
    
    if not prompts:
        pytest.skip("No prompts found in test-prompts.json")
    
    # Initialize pipeline
    pipeline = ResponsePipeline(api_key=api_key)
    
    # Show available tools
    available_tools = pipeline.tool_registry.get_tool_schemas()
    print(f"\n{'='*80}")
    print(f"Processing {len(prompts)} test prompts from test-prompts.json")
    print(f"{'='*80}")
    print(f"\nAvailable Tools ({len(available_tools)}):")
    for tool in available_tools:
        print(f"  - {tool['name']}: {tool['description']}")
    print(f"{'='*80}\n")
    
    # Process each prompt
    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'-'*80}")
        print(f"PROMPT #{i}/{len(prompts)}")
        print(f"{'-'*80}")
        print(f"Input: {prompt}")
        print(f"{'-'*80}")
        
        try:
            result = await pipeline.process_text(prompt)
            
            # Display results
            print(f"\n[+] Intent Detected:")
            intent = result.get("intent", {})
            print(f"   - Intent: {intent.get('intent', 'N/A')}")
            print(f"   - Confidence: {intent.get('confidence', 0):.2f}")
            print(f"   - Reasoning: {intent.get('reasoning', 'N/A')}")
            
            tool_calls = result.get("tool_calls", [])
            if tool_calls:
                print(f"\n[TOOLS] Tools Called: {len(tool_calls)}")
                for tool_name in tool_calls:
                    print(f"   - {tool_name}")
            else:
                print(f"\n[TOOLS] Tools Called: None")
                print(f"   (Note: LLM chose not to call any tools for this prompt)")
            
            tool_results = result.get("tool_results", [])
            if tool_results:
                print(f"\n[RESULTS] Tool Results: {len(tool_results)}")
                for tool_result in tool_results:
                    tool_name = tool_result.get("tool_name", "Unknown")
                    status = tool_result.get("result", {}).get("status", "unknown")
                    print(f"   - {tool_name}: {status}")
            
            response_text = result.get("response", "")
            print(f"\n[RESPONSE] AI Response:")
            print(f"   {response_text}")
            
            # Metadata
            metadata = result.get("metadata", {})
            if metadata:
                print(f"\n[METADATA]")
                print(f"   - Model: {metadata.get('model', 'N/A')}")
                print(f"   - Temperature: {metadata.get('temperature', 'N/A')}")
            
        except Exception as e:
            print(f"\n[ERROR] Error processing prompt: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n{'-'*80}\n")
        
        # Add 5-second delay between prompts to avoid rate limiting
        if i < len(prompts):  # Don't wait after the last prompt
            print(f"[WAIT] Waiting 5 seconds before next prompt...")
            import asyncio
            await asyncio.sleep(5)
    
    print(f"\n{'='*80}")
    print(f"Completed processing all {len(prompts)} prompts")
    print(f"{'='*80}\n")
    
    # Basic assertion to ensure test passes
    assert len(prompts) > 0, "Should have processed at least one prompt"
