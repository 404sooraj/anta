"""System prompts for the LLM including tool instructions."""

from typing import Optional, List
from langchain_core.tools import StructuredTool


def build_system_prompt(
    user_id: Optional[str] = None,
    tools: Optional[List[StructuredTool]] = None,
) -> str:
    """
    Build a system prompt with user context and tool instructions.
    
    Args:
        user_id: The user's ID for tool calls requiring user identification.
        tools: List of available tools to describe to the LLM.
        
    Returns:
        Complete system prompt string.
    """
    prompt_parts = []
    
    # Base system identity
    prompt_parts.append(
        "You are a helpful customer service assistant for a battery swap service company. "
        "You help users with their account, swap history, service issues, and general inquiries."
    )
    
    # User context
    if user_id:
        prompt_parts.append(
            f"\n\nCURRENT USER CONTEXT:\n"
            f"- User ID: {user_id}\n"
            f"- Use this user_id when calling any tool that requires a userId parameter."
        )
    
    # Tool instructions
    if tools:
        prompt_parts.append("\n\nAVAILABLE TOOLS:")
        prompt_parts.append(
            "You have access to the following tools. Use them to retrieve information when needed:"
        )
        
        for tool in tools:
            prompt_parts.append(f"\n- {tool.name}: {tool.description}")
        
        prompt_parts.append(
            "\n\nTOOL USAGE GUIDELINES:"
            "\n1. When the user asks about their name, profile, account, or personal information, use the getUserInfo tool."
            "\n2. When the user asks about their location or where they are, use the getCurrentLocation tool."
            "\n3. When the user asks about a recent swap or swap history, use the getLastSwapAttempt tool."
            "\n4. When the user asks about service center visits, use the getLastServiceCenterVisit tool."
            "\n5. When the user reports a problem or issue, use the getProblemContext tool to analyze it."
            "\n6. When the user asks about the nearest station, where to swap, or finding a station, use the getNearestStation tool."
            "\n7. If the user specifically asks for stations with available batteries, call getNearestStation with requireAvailableBatteries=true."
            "\n8. Always use the provided user_id when calling tools that require userId."
            "\n9. If a tool returns an error or 'not found', inform the user politely."
        )
    
    # Response guidelines
    prompt_parts.append(
        "\n\nRESPONSE GUIDELINES:"
        "\n- Be concise and helpful."
        "\n- If you need to use a tool to answer, use it before responding."
        "\n- After receiving tool results, incorporate the information naturally into your response."
        "\n- Don't mention that you're using tools; just provide the information."
    )
    
    return "\n".join(prompt_parts)


def build_tool_result_prompt(tool_name: str, result: dict) -> str:
    """
    Build a prompt explaining a tool result to help the LLM form a response.
    
    Args:
        tool_name: Name of the tool that was executed.
        result: The result dictionary from the tool.
        
    Returns:
        Prompt string describing the tool result.
    """
    status = result.get("status", "unknown")
    data = result.get("data", {})
    
    if status == "ok":
        return f"Tool {tool_name} returned successfully with data: {data}"
    elif status == "not_found":
        return f"Tool {tool_name} could not find the requested information: {data.get('message', 'Not found')}"
    elif status == "not_implemented":
        return f"Tool {tool_name} is not yet available: {data.get('message', 'Not implemented')}"
    else:
        return f"Tool {tool_name} encountered an error: {data.get('error', 'Unknown error')}"
