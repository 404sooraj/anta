"""Pytest configuration and fixtures for testing."""

import os
from pathlib import Path
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Load .env file first to get real API key if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Set test environment variables (only if not already set from .env)
if not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = "test_api_key_12345"


@pytest.fixture
def mock_genai_client():
    """Mock google genai client for testing."""
    mock = Mock()
    
    # Mock interaction response
    mock_output = Mock()
    mock_output.type = "text"
    mock_output.text = "This is a test response from the LLM."
    
    mock_interaction = Mock()
    mock_interaction.outputs = [mock_output]
    mock_interaction.id = "test_interaction_id_123"
    
    mock.interactions.create.return_value = mock_interaction
    
    return mock


@pytest.fixture
def mock_pipeline():
    """Mock ResponsePipeline for testing."""
    mock = Mock()
    
    # process_text is async - use AsyncMock for assertion support
    async_mock_process_text = AsyncMock()
    async_mock_process_text.return_value = {
        "response": "Test response",
        "intent": {"intent": "general", "confidence": 0.9, "reasoning": "Test"},
        "tool_calls": [],
        "tool_results": [],
        "metadata": {"model": "gemini-2.5-flash", "temperature": 0.7}
    }
    mock.process_text = async_mock_process_text
    
    # load_test_prompts is synchronous
    mock.load_test_prompts.return_value = [
        "Test prompt 1",
        "Test prompt 2"
    ]
    
    return mock


@pytest.fixture
def test_client(mock_pipeline):
    """FastAPI test client with mocked pipeline."""
    # Import here to avoid circular imports
    from main import app
    
    # Override the pipeline in app state
    app.state.pipeline = mock_pipeline
    
    return TestClient(app)


@pytest.fixture
def mock_tool_result():
    """Mock tool execution result."""
    return {
        "status": "success",
        "data": {
            "test_key": "test_value"
        }
    }
