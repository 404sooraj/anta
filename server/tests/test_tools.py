"""Tests for the tool system."""

import pytest
from modules.response.tool_registry import ToolRegistry, get_registry
from modules.response.tools import (
    GetUserInfoTool,
    GetCurrentLocationTool,
    GetLastServiceCenterVisitTool,
    GetProblemContextTool,
    GetLastSwapAttemptTool,
)


def test_tool_registry_initialization():
    """Test tool registry initializes with default tools."""
    registry = ToolRegistry()
    
    assert registry is not None
    tools = registry.get_all_tools()
    assert len(tools) == 5  # Should have 5 default tools


def test_tool_registry_get_tool():
    """Test getting a specific tool from registry."""
    registry = ToolRegistry()
    
    tool = registry.get_tool("getUserInfo")
    assert tool is not None
    assert isinstance(tool, GetUserInfoTool)


def test_tool_registry_get_nonexistent_tool():
    """Test getting a tool that doesn't exist."""
    registry = ToolRegistry()
    
    tool = registry.get_tool("nonExistentTool")
    assert tool is None


def test_get_registry_singleton():
    """Test that get_registry returns singleton instance."""
    registry1 = get_registry()
    registry2 = get_registry()
    
    assert registry1 is registry2


def test_tool_schemas():
    """Test that tools generate proper schemas."""
    registry = ToolRegistry()
    schemas = registry.get_tool_schemas()
    
    assert len(schemas) == 5
    
    for schema in schemas:
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema


@pytest.mark.asyncio
async def test_tool_execution():
    """Test executing a tool."""
    registry = ToolRegistry()
    
    result = await registry.execute_tool("getUserInfo", {"userId": "test123"})
    
    assert result is not None
    assert isinstance(result, dict)
    # Placeholder tools return not_implemented status
    assert result.get("status") == "not_implemented"


@pytest.mark.asyncio
async def test_tool_execution_with_invalid_tool():
    """Test executing a non-existent tool."""
    registry = ToolRegistry()
    
    with pytest.raises(ValueError, match="Tool .* not found"):
        await registry.execute_tool("invalidTool", {})


@pytest.mark.asyncio
async def test_individual_tools():
    """Test individual tool instantiation and execution."""
    tools = [
        GetUserInfoTool(),
        GetCurrentLocationTool(),
        GetLastServiceCenterVisitTool(),
        GetProblemContextTool(),
        GetLastSwapAttemptTool(),
    ]
    
    for tool in tools:
        assert tool.name
        assert tool.description
        
        schema = tool.get_schema()
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
