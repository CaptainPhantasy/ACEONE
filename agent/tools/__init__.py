"""
ClaudeVoice Tools Package - Fixed Version
Simplified tools without decorators for LiveKit 1.2.17 compatibility
"""

# Import only the simplified tools that work without decorators
try:
    from .tools_simple import SIMPLE_TOOLS

    # Export individual functions for convenience
    get_weather = SIMPLE_TOOLS.get("get_weather")
    check_calendar = SIMPLE_TOOLS.get("check_calendar")
    create_appointment = SIMPLE_TOOLS.get("create_appointment")
    query_database = SIMPLE_TOOLS.get("query_database")
    recommend_activity = SIMPLE_TOOLS.get("recommend_activity")
    calculate = SIMPLE_TOOLS.get("calculate")
    get_current_time = SIMPLE_TOOLS.get("get_current_time")
    take_note = SIMPLE_TOOLS.get("take_note")

    __all__ = [
        "SIMPLE_TOOLS",
        "get_weather",
        "check_calendar",
        "create_appointment",
        "query_database",
        "recommend_activity",
        "calculate",
        "get_current_time",
        "take_note",
    ]
except ImportError as e:
    # If simplified tools not available, provide empty dict
    SIMPLE_TOOLS = {}
    __all__ = ["SIMPLE_TOOLS"]
    print(f"Warning: Could not import simplified tools: {e}")
