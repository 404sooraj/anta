"""Tests for API route handlers."""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(test_client):
    """Test the root endpoint returns correct status."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "status" in data
    assert data["status"] == "running"


def test_process_text_endpoint_success(test_client, mock_pipeline):
    """Test process-text endpoint with valid input."""
    response = test_client.post(
        "/api/process-text",
        json={"text": "Test prompt"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data
    assert "intent" in data
    assert "tool_calls" in data
    assert "tool_results" in data
    assert "metadata" in data
    
    # Verify mock was called
    mock_pipeline.process_text.assert_called_once_with("Test prompt")


def test_process_text_endpoint_empty_text(test_client):
    """Test process-text endpoint with empty text."""
    response = test_client.post(
        "/api/process-text",
        json={"text": ""}
    )
    
    # Should still process but might return less meaningful results
    assert response.status_code == 200


def test_get_test_prompts_endpoint(test_client, mock_pipeline):
    """Test get test prompts endpoint."""
    response = test_client.get("/api/test-prompts")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "prompts" in data
    assert "count" in data
    assert isinstance(data["prompts"], list)
    assert data["count"] == len(data["prompts"])
    
    # Verify mock was called
    mock_pipeline.load_test_prompts.assert_called_once()


def test_process_test_prompts_endpoint(test_client, mock_pipeline):
    """Test process test prompts endpoint."""
    response = test_client.post("/api/process-test-prompts")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert "count" in data
    assert isinstance(data["results"], list)
    
    # Should have processed 2 prompts (from mock)
    assert data["count"] == 2
    
    # Verify pipeline methods were called
    mock_pipeline.load_test_prompts.assert_called_once()
    assert mock_pipeline.process_text.call_count == 2


def test_process_text_endpoint_invalid_json(test_client):
    """Test process-text endpoint with invalid JSON."""
    response = test_client.post(
        "/api/process-text",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 422  # Validation error
