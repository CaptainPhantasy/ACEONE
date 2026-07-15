import httpx
import logging
from datetime import datetime
from agent.config import config  # Import our central config

logger = logging.getLogger(__name__)


async def get_ipc_event_list(
    start_date: str, end_date: str, category_id: int = None
) -> str:
    """
    Fetches the event list from the CourtReserve API.
    This is the real function that OpenAI's "get_ipc_event_list" will trigger.
    """

    logger.info(f"CourtReserve: Fetching events from {start_date} to {end_date}")

    # 1. Set up the API call
    api_url = f"{config.courtreserve_base_url}/api/v1/eventcalendar/eventlist"

    # 2. Set up headers with the Bearer Token
    headers = {"Authorization": f"Bearer {config.courtreserve_api_key}"}

    # 3. Set up query parameters
    params = {
        "startDate": f"{start_date}T00:00:00",
        "endDate": f"{end_date}T23:59:59",
        "includeRegisteredPlayersCount": True,
        "includePriceInfo": True,
    }
    if category_id:
        params["categoryId"] = category_id

    # 4. Make the async API call
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json().get("Data", [])
                if not data:
                    return f"I checked the calendar, but I don't see any events scheduled between {start_date} and {end_date}."

                # 5. Format the JSON into a natural language response
                response_text = (
                    f"Here's what I found between {start_date} and {end_date}:\n"
                )

                for event in data[:10]:  # Limit to 10 to avoid huge response
                    event_name = event.get("EventName")
                    start_time_str = event.get("StartDateTime")
                    start_time = datetime.fromisoformat(start_time_str).strftime(
                        "%A, %b %d at %I:%M %p"
                    )
                    registered = event.get("RegisteredCount", 0)
                    max_players = event.get("MaxRegistrants", 0)

                    spots_info = ""
                    if max_players > 0:
                        spots_left = max_players - registered
                        if spots_left > 0:
                            spots_info = f"({spots_left} spots left)"
                        else:
                            spots_info = "(it's full)"

                    response_text += f"- {event_name} on {start_time} {spots_info}\n"

                if len(data) > 10:
                    response_text += f"...and {len(data) - 10} other events."

                return response_text
            else:
                logger.error(
                    f"CourtReserve API error: {response.status_code} - {response.text}"
                )
                return f"Sorry, I had trouble checking the calendar. The system returned a {response.status_code} error."

    except Exception as e:
        logger.error(f"CourtReserve API call failed: {e}")
        return (
            f"Sorry, I ran into an error trying to check the CourtReserve calendar: {e}"
        )
