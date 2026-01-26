"""Base tool interface for all tools in the system."""

from abc import ABC, abstractmethod
from typing import Any, Dict
import inspect


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    name: str = ""
    description: str = ""
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        
        Returns:
            Dictionary containing the tool execution result.
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Generate Gemini function calling schema for this tool.
        
        Returns:
            Dictionary in Gemini function calling format.
        """
        # Get the execute method signature
        sig = inspect.signature(self.execute)
        parameters = {}
        required = []
        
        # Extract parameters from the execute method
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            
            param_info = {
                "type": self._python_type_to_json_type(param.annotation),
                "description": param.default if isinstance(param.default, str) else f"Parameter {param_name}"
            }
            
            # If parameter has no default, it's required
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            
            parameters[param_name] = param_info
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required
            }
        }
    
    @staticmethod
    def _python_type_to_json_type(python_type: Any) -> str:
        """Convert Python type annotation to JSON schema type."""
        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        
        # Handle typing module types
        if hasattr(python_type, "__origin__"):
            origin = python_type.__origin__
            if origin is list:
                return "array"
            elif origin is dict:
                return "object"
        
        # Handle direct type checks
        if python_type in type_mapping:
            return type_mapping[python_type]
        
        # Default to string if type is unknown
        return "string"
