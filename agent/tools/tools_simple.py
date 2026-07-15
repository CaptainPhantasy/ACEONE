"""
Simplified Tools for LiveKit 1.2.17 Compatibility
All tools work without decorators
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# Weather Tool
async def get_weather(location: str, units: str = "metric") -> str:
    """Get weather information for a location."""
    logger.info(f"Weather request for {location}")

    # Mock weather data
    weather_map = {
        "san francisco": {"temp": 18, "condition": "Partly cloudy"},
        "new york": {"temp": 22, "condition": "Clear"},
        "london": {"temp": 15, "condition": "Light rain"},
    }

    weather = weather_map.get(location.lower(), {"temp": 20, "condition": "Clear"})
    temp_unit = "°C" if units == "metric" else "°F"
    temp = weather["temp"] if units == "metric" else int(weather["temp"] * 9 / 5 + 32)

    return f"The weather in {location} is {weather['condition']} with a temperature of {temp}{temp_unit}."


# Calendar Tool
async def check_calendar(date: str = None) -> str:
    """Check calendar availability for a specific date."""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Checking calendar for {date}")

    # Mock calendar data
    busy_dates = ["2025-11-05", "2025-11-10", "2025-11-15"]

    if date in busy_dates:
        return f"You have appointments scheduled on {date}. The day is busy."
    else:
        return f"You have no appointments on {date}. The day is free."


async def create_appointment(
    title: str, date: str, time: str, duration_minutes: int = 30
) -> str:
    """Create a calendar appointment."""
    logger.info(f"Creating appointment: {title} on {date} at {time}")

    return f"Appointment '{title}' has been created for {date} at {time} for {duration_minutes} minutes."


# Database Tool
async def query_database(query: str) -> str:
    """Query the database for information."""
    logger.info(f"Database query: {query}")

    # Mock database responses
    if "customer" in query.lower():
        return "Found 3 customer records matching your query."
    elif "product" in query.lower():
        return "Found 10 products in the database."
    elif "order" in query.lower():
        return "Found 25 recent orders."
    else:
        return f"Query executed successfully. No specific data found for: {query}"


# Activity Recommendation Tool
async def recommend_activity(weather: str = None, preferences: str = None) -> str:
    """Recommend activities based on weather and preferences."""
    logger.info(
        f"Recommending activity for weather: {weather}, preferences: {preferences}"
    )

    if weather and "rain" in weather.lower():
        return "Since it's raining, I recommend indoor activities like visiting a museum, watching a movie, or reading a book."
    elif weather and "sunny" in weather.lower():
        return "It's sunny! Great day for outdoor activities like hiking, having a picnic, or going to the beach."
    else:
        return "I suggest checking local events, trying a new restaurant, or exploring a nearby neighborhood."


# Simple Calculation Tool
async def calculate(expression: str) -> str:
    """Perform simple calculations."""
    logger.info(f"Calculating: {expression}")

    try:
        # Only allow safe math operations
        allowed_names = {k: v for k, v in {"__builtins__": None}.items()}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"The result of {expression} is {result}"
    except Exception:
        return "I couldn't calculate that. Please provide a simple mathematical expression."


# Time Tool
async def get_current_time(timezone: str = None) -> str:
    """Get the current time."""
    from datetime import datetime

    # Note: pytz handling removed for simplicity
    # Could be added back if pytz is installed

    time = datetime.now()
    if timezone:
        return f"The current time is {time.strftime('%I:%M %p on %B %d, %Y')} (timezone support requires pytz)"
    else:
        return f"The current time is {time.strftime('%I:%M %p on %B %d, %Y')}"


# Note-taking Tool
async def take_note(content: str, title: str = None) -> str:
    """Take a note or reminder."""
    logger.info(f"Taking note: {title or 'Untitled'}")

    if title:
        return f"I've saved your note titled '{title}': {content}"
    else:
        return f"I've saved your note: {content}"


# All tools dictionary for easy import
SIMPLE_TOOLS = {
    "get_weather": get_weather,
    "check_calendar": check_calendar,
    "create_appointment": create_appointment,
    "query_database": query_database,
    "recommend_activity": recommend_activity,
    "calculate": calculate,
    "get_current_time": get_current_time,
    "take_note": take_note,
}
