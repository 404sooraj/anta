"""Tool registry for managing and executing tools."""

from typing import Dict, Any, List, Optional, Set
import logging

from langchain_core.tools import StructuredTool

from .tools import (
    GetUserInfoTool,
    GetCurrentLocationTool,
    GetLastServiceCenterVisitTool,
    GetNearestStationTool,
    GetProblemContextTool,
    GetLastSwapAttemptTool,
    GetBatteryInfoTool,
    ReportBatteryIssueTool,
    RequestHumanAgentTool,
    GetSubscriptionInfoTool,
    GeocodeAddressTool,
    ReverseGeocodeTool,
)
from .tools.base import BaseTool
from .intent_tools_mapping import get_tools_for_intent

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all available tools."""
    
    def __init__(self):
        """Initialize the tool registry with all available tools."""
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register all default tools."""
        tools = [
            GetUserInfoTool(),
            GetCurrentLocationTool(),
            GetLastServiceCenterVisitTool(),
            GetNearestStationTool(),
            GetProblemContextTool(),
            GetLastSwapAttemptTool(),
            GetBatteryInfoTool(),
            ReportBatteryIssueTool(),
            RequestHumanAgentTool(),
            GetSubscriptionInfoTool(),
            GeocodeAddressTool(),
            ReverseGeocodeTool(),
        ]
        
        for tool in tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: BaseTool):
        """
        Register a tool in the registry.
        
        Args:
            tool: The tool instance to register.
        """
        if not tool.name:
            raise ValueError("Tool must have a name")
        
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} is already registered. Overwriting.")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name: The name of the tool.
            
        Returns:
            The tool instance if found, None otherwise.
        """
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            Dictionary mapping tool names to tool instances.
        """
        return self._tools.copy()
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get function calling schemas for all registered tools.
        
        Returns:
            List of tool schemas in Gemini function calling format.
        """
        return [tool.get_schema() for tool in self._tools.values()]

    def get_langchain_tools(self, intent: Optional[str] = None) -> List[StructuredTool]:
        """
        Get LangChain tool objects for registered tools.

        Args:
            intent: Optional intent to filter tools by. If None, returns all tools.

        Returns:
            List of LangChain StructuredTool instances.
        """
        if intent:
            allowed_tools = get_tools_for_intent(intent)
            tools_to_convert = [
                tool for name, tool in self._tools.items() 
                if name in allowed_tools
            ]
            logger.info(f"[ToolRegistry] Filtering tools for intent '{intent}': {allowed_tools}")
        else:
            tools_to_convert = list(self._tools.values())
        
        tools = [self._to_langchain_tool(tool) for tool in tools_to_convert]
        logger.info(f"[ToolRegistry] Generated {len(tools)} LangChain tools")
        for t in tools:
            logger.info(f"[ToolRegistry] Tool '{t.name}': description='{t.description[:50]}...', args_schema={t.args_schema}")
        return tools

    @staticmethod
    def _to_langchain_tool(tool: BaseTool) -> StructuredTool:
        """Convert a BaseTool to a LangChain StructuredTool."""
        return StructuredTool.from_function(
            func=None,
            coroutine=tool.execute,
            name=tool.name,
            description=tool.description,
            infer_schema=tool.args_schema is None,
            args_schema=tool.args_schema,
        )
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with given arguments.
        
        Args:
            name: The name of the tool to execute.
            arguments: Dictionary of arguments to pass to the tool.
            
        Returns:
            Dictionary containing the tool execution result.
            
        Raises:
            ValueError: If the tool is not found.
            Exception: If tool execution fails.
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry")
        
        try:
            logger.info(f"Executing tool: {name} with arguments: {arguments}")
            result = await tool.execute(**arguments)
            logger.info(f"Tool {name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "tool": name
            }


# Global tool registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Returns:
        The global ToolRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
