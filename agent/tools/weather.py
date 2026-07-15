"""
Weather Tool Implementation
Provides weather information using OpenWeatherMap or similar API
"""

import os
import httpx
import logging
from livekit.agents import llm

logger = logging.getLogger(__name__)


@llm.function_tool(
    description="Get current weather information for a specific location"
)
async def weather_tool(location: str, units: str = "metric") -> str:
    """
    Get current weather information for a location

    Args:
        location: City name or location (e.g., "London", "New York, US")
        units: Temperature units - "metric" (Celsius) or "imperial" (Fahrenheit)

    Returns:
        Weather information as a natural language string
    """
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY", "demo")

        # Use OpenWeatherMap API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": location, "appid": api_key, "units": units},
            )

            if response.status_code == 200:
                data = response.json()

                temp = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                description = data["weather"][0]["description"]
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]

                unit_symbol = "°C" if units == "metric" else "°F"
                wind_unit = "m/s" if units == "metric" else "mph"

                return (
                    f"The weather in {location} is currently {description}. "
                    f"The temperature is {temp}{unit_symbol}, "
                    f"feels like {feels_like}{unit_symbol}. "
                    f"Humidity is {humidity}% and wind speed is {wind_speed} {wind_unit}."
                )

            elif response.status_code == 404:
                return f"I couldn't find weather information for {location}. Please check the location name."

            else:
                logger.error(f"Weather API error: {response.status_code}")
                return "I'm having trouble accessing weather information right now. Please try again later."

    except httpx.TimeoutException:
        logger.error("Weather API timeout")
        return "The weather service is taking too long to respond. Please try again."

    except Exception as e:
        logger.error(f"Weather tool error: {e}")
        return "I encountered an error while checking the weather. Please try again."


@llm.function_tool(description="Get weather forecast for the next few days")
async def weather_forecast(location: str, days: int = 3, units: str = "metric") -> str:
    """
    Get weather forecast for a location

    Args:
        location: City name or location
        days: Number of days to forecast (1-5)
        units: Temperature units

    Returns:
        Weather forecast as a natural language string
    """
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY", "demo")
        days = min(max(days, 1), 5)  # Clamp between 1 and 5

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={
                    "q": location,
                    "appid": api_key,
                    "units": units,
                    "cnt": days * 8,  # 8 forecasts per day (every 3 hours)
                },
            )

            if response.status_code == 200:
                data = response.json()
                forecasts = {}

                # Group forecasts by day
                for item in data["list"]:
                    date = item["dt_txt"].split()[0]
                    if date not in forecasts:
                        forecasts[date] = {"temps": [], "descriptions": []}
                    forecasts[date]["temps"].append(item["main"]["temp"])
                    forecasts[date]["descriptions"].append(
                        item["weather"][0]["description"]
                    )

                unit_symbol = "°C" if units == "metric" else "°F"
                forecast_text = f"Weather forecast for {location}: "

                for date, info in list(forecasts.items())[:days]:
                    avg_temp = sum(info["temps"]) / len(info["temps"])
                    # Get most common description
                    description = max(
                        set(info["descriptions"]), key=info["descriptions"].count
                    )
                    forecast_text += f"{date}: {description}, average temperature {avg_temp:.1f}{unit_symbol}. "

                return forecast_text

            else:
                return f"I couldn't get the forecast for {location}. Please check the location name."

    except Exception as e:
        logger.error(f"Weather forecast error: {e}")
        return "I encountered an error while getting the weather forecast."


@llm.function_tool(
    description="Check if weather conditions are suitable for an outdoor activity"
)
async def check_weather_conditions(location: str, activity: str) -> str:
    """
    Check if weather is suitable for a specific activity

    Args:
        location: City name or location
        activity: The outdoor activity (e.g., "picnic", "running", "skiing")

    Returns:
        Recommendation based on weather conditions
    """
    try:
        # Get current weather
        weather_info = await weather_tool(location, "metric")

        # Parse basic conditions from the response
        is_raining = "rain" in weather_info.lower()
        is_snowing = "snow" in weather_info.lower()
        is_clear = "clear" in weather_info.lower() or "sunny" in weather_info.lower()

        # Extract temperature (simple parsing)
        import re

        temp_match = re.search(r"temperature is ([\d.]+)°C", weather_info)
        temp = float(temp_match.group(1)) if temp_match else 20

        # Activity-specific recommendations
        activity_lower = activity.lower()

        if "ski" in activity_lower or "snowboard" in activity_lower:
            if is_snowing or temp < 5:
                return f"Great conditions for {activity} in {location}! {weather_info}"
            else:
                return f"Not ideal for {activity}. {weather_info}"

        elif "picnic" in activity_lower or "barbecue" in activity_lower:
            if is_clear and 15 < temp < 30 and not is_raining:
                return f"Perfect weather for {activity} in {location}! {weather_info}"
            elif is_raining:
                return f"Not recommended for {activity} due to rain. {weather_info}"
            else:
                return f"Weather might not be ideal for {activity}. {weather_info}"

        elif "run" in activity_lower or "jog" in activity_lower:
            if not is_raining and 5 < temp < 25:
                return f"Good conditions for {activity} in {location}. {weather_info}"
            else:
                return f"Consider indoor exercise today. {weather_info}"

        else:
            # Generic outdoor activity
            if is_clear and not is_raining and 10 < temp < 28:
                return (
                    f"Weather looks good for {activity} in {location}. {weather_info}"
                )
            else:
                return f"Check conditions carefully for {activity}. {weather_info}"

    except Exception as e:
        logger.error(f"Weather conditions check error: {e}")
        return f"I couldn't check the weather conditions for {activity} in {location}."
