"""Mapping of intents to appropriate tools."""

from typing import Dict, List, Set

# Maps intent categories to the tools that should be available for that intent
# "all" is a special key that includes tools available for all intents
INTENT_TOOL_MAPPING: Dict[str, List[str]] = {
    # Tools available for all intents (always included)
    "all": [
        "getUserInfo",  # User can always ask about their account
    ],
    
    # User asking about their profile, name, account details
    "user_query": [
        "getUserInfo",
    ],
    
    # User requesting a service
    "service_request": [
        "getUserInfo",
        "getCurrentLocation",
        "getLastServiceCenterVisit",
        "getNearestStation",
    ],
    
    # User reporting a problem or issue
    "problem_report": [
        "getUserInfo",
        "getProblemContext",
        "getLastSwapAttempt",
        "getLastServiceCenterVisit",
    ],
    
    # User asking about their location
    "location_query": [
        "getUserInfo",
        "getCurrentLocation",
        "getNearestStation",  # Often follows location queries
    ],
    
    # User asking about service center visits
    "service_center_query": [
        "getUserInfo",
        "getLastServiceCenterVisit",
        "getNearestStation",
    ],
    
    # User asking about swap attempts
    "swap_attempt_query": [
        "getUserInfo",
        "getLastSwapAttempt",
        "getNearestStation",  # May need to find a station after failed swap
    ],
    
    # User looking for nearest station or where to swap battery
    "station_query": [
        "getUserInfo",
        "getCurrentLocation",
        "getNearestStation",
    ],
    
    # General conversation - provide basic tools
    "general": [
        "getUserInfo",
        "getCurrentLocation",
        "getNearestStation",  # Station queries are common
    ],
}


def get_tools_for_intent(intent: str) -> Set[str]:
    """
    Get the set of tool names appropriate for a given intent.
    
    Args:
        intent: The detected intent category.
        
    Returns:
        Set of tool names to make available.
    """
    tools = set(INTENT_TOOL_MAPPING.get("all", []))
    tools.update(INTENT_TOOL_MAPPING.get(intent, []))
    return tools


def get_all_tool_names() -> Set[str]:
    """
    Get all unique tool names from the mapping.
    
    Returns:
        Set of all tool names.
    """
    all_tools: Set[str] = set()
    for tools in INTENT_TOOL_MAPPING.values():
        all_tools.update(tools)
    return all_tools
