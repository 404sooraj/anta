"""Mapping of intents to appropriate tools."""

from typing import Dict, List, Set

# Maps intent categories to the tools that should be available for that intent
# "all" is a special key that includes tools available for all intents
INTENT_TOOL_MAPPING: Dict[str, List[str]] = {
    # Tools available for all intents (always included)
    "all": [
        "getUserInfo",  # User can always ask about their account
        "requestHumanAgent",  # User can always request to speak to a human
    ],
    
    # User asking about their profile, name, account details
    "user_query": [
        "getUserInfo",
        "getBatteryInfo",  # Battery is part of user profile
        "getSubscriptionInfo",  # Subscription is part of user profile
    ],
    
    # User asking about their subscription/plan
    "subscription_query": [
        "getUserInfo",
        "getSubscriptionInfo",
    ],
    
    # User requesting a service
    "service_request": [
        "getUserInfo",
        "getCurrentLocation",
        "getLastServiceCenterVisit",
        "getNearestStation",
        "getBatteryInfo",
        "getSubscriptionInfo",  # May need subscription info for service
        "geocodeAddress",  # For Twilio calls - convert spoken location
    ],
    
    # User reporting a problem or issue
    "problem_report": [
        "getUserInfo",
        "getProblemContext",
        "getLastSwapAttempt",
        "getLastServiceCenterVisit",
        "getBatteryInfo",  # Battery issues are common problems
        "reportBatteryIssue",  # Allow reporting battery issues
    ],
    
    # User asking about their location
    "location_query": [
        "getUserInfo",
        "getCurrentLocation",
        "getNearestStation",  # Often follows location queries
        "geocodeAddress",  # For Twilio calls - convert spoken location to coordinates
    ],
    
    # User asking about service center visits
    "service_center_query": [
        "getUserInfo",
        "getLastServiceCenterVisit",
        "getNearestStation",
        "geocodeAddress",  # For Twilio calls
    ],
    
    # User asking about swap attempts
    "swap_attempt_query": [
        "getUserInfo",
        "getLastSwapAttempt",
        "getNearestStation",  # May need to find a station after failed swap
        "getBatteryInfo",
        "geocodeAddress",  # For Twilio calls
    ],
    
    # User looking for nearest station or where to swap battery
    "station_query": [
        "getUserInfo",
        "getCurrentLocation",
        "getNearestStation",
        "getBatteryInfo",  # Check battery before swapping
        "geocodeAddress",  # For Twilio calls - convert spoken location to coordinates
    ],
    
    # User asking about their battery status/health/issues
    "battery_query": [
        "getUserInfo",
        "getBatteryInfo",
        "getLastSwapAttempt",
        "getNearestStation",  # Suggest swap if battery health is low
        "reportBatteryIssue",  # Allow reporting battery issues
    ],
    
    # General conversation - provide basic tools
    "general": [
        "getUserInfo",
        "getCurrentLocation",
        "getNearestStation",  # Station queries are common
        "getBatteryInfo",
        "geocodeAddress",  # For Twilio calls - convert spoken location
    ],
    
    # User wants to speak to a human agent
    "human_handoff": [
        "getUserInfo",
        "requestHumanAgent",  # Primary tool for handoff
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
