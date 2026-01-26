"""LLM client for Gemini API with Interactions API and function calling support."""

import os
import logging
from typing import Dict, Any, List, Optional
from google import genai

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with Google Gemini API using Interactions API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize the LLM client.
        
        Args:
            api_key: Google Gemini API key. If not provided, reads from GEMINI_API_KEY env var.
            model_name: Name of the Gemini model to use.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum number of tokens in response.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided or set as environment variable")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def _prepare_tool_schema(self, tool_schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare tool schemas for Gemini Interactions API.
        
        Args:
            tool_schemas: List of tool schemas from tool registry.
            
        Returns:
            List of tools in Interactions API format.
        """
        tools = []
        for schema in tool_schemas:
            tools.append({
                "type": "function",
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["parameters"]
            })
        return tools
    
    async def generate_with_tools(
        self,
        prompt: str,
        tool_schemas: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response with tool calling support using Interactions API.
        
        Args:
            prompt: The user prompt.
            tool_schemas: List of available tool schemas.
            conversation_history: Optional conversation history (not used in initial call).
            
        Returns:
            Dictionary containing the response, tool calls, and interaction ID.
        """
        try:
            # Prepare tools
            tools = self._prepare_tool_schema(tool_schemas) if tool_schemas else []
            
            # Configure generation config
            generation_config = {
                "temperature": self.temperature,
            }
            if self.max_tokens:
                generation_config["max_output_tokens"] = self.max_tokens
            
            # Create interaction
            interaction = self.client.interactions.create(
                model=self.model_name,
                input=prompt,
                tools=tools if tools else None,
                generation_config=generation_config
            )
            
            # Parse outputs
            tool_calls = []
            text_response = ""
            
            for output in interaction.outputs:
                if output.type == "function_call":
                    tool_calls.append({
                        "name": output.name,
                        "arguments": output.arguments,
                        "call_id": output.id
                    })
                elif output.type == "text":
                    text_response = output.text
                elif output.type == "thought":
                    # Optionally log thinking process
                    if hasattr(output, "summary") and output.summary:
                        logger.debug(f"Model thinking: {output.summary}")
            
            return {
                "text": text_response,
                "tool_calls": tool_calls,
                "interaction_id": interaction.id,
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            raise
    
    async def generate_final_response(
        self,
        prompt: str,
        tool_results: List[Dict[str, Any]],
        interaction_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate final response after tool execution using Interactions API.
        
        Args:
            prompt: Original user prompt.
            tool_results: Results from tool executions.
            interaction_id: ID from the previous interaction.
            conversation_history: Optional conversation history (not used with interaction_id).
            
        Returns:
            Final text response.
        """
        try:
            # Build function results input
            function_results = []
            for tool_result in tool_results:
                function_results.append({
                    "type": "function_result",
                    "name": tool_result.get("tool_name"),
                    "call_id": tool_result.get("call_id"),
                    "result": tool_result.get("result", {})
                })
            
            # Configure generation config
            generation_config = {
                "temperature": self.temperature,
            }
            if self.max_tokens:
                generation_config["max_output_tokens"] = self.max_tokens
            
            # Continue interaction with tool results
            interaction = self.client.interactions.create(
                model=self.model_name,
                previous_interaction_id=interaction_id,
                input=function_results,
                generation_config=generation_config
            )
            
            # Extract text response
            for output in interaction.outputs:
                if output.type == "text":
                    return output.text
            
            return ""
            
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            raise
