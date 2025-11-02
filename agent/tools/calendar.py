"""
Calendar Tool Implementation
Manages calendar appointments and scheduling
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from livekit.agents import llm
import httpx
import json

logger = logging.getLogger(__name__)

# In-memory calendar storage (replace with database in production)
calendar_store = {}


@llm.function_tool(
    description="Create a new calendar appointment or meeting"
)
async def calendar_tool(
    title: str,
    date: str,
    time: str,
    duration_minutes: int = 60,
    description: Optional[str] = None,
    location: Optional[str] = None
) -> str:
    """
    Create a calendar appointment

    Args:
        title: Title of the appointment
        date: Date in format "YYYY-MM-DD" or "tomorrow", "today"
        time: Time in format "HH:MM" (24-hour)
        duration_minutes: Duration in minutes (default 60)
        description: Optional description
        location: Optional location

    Returns:
        Confirmation message
    """
    try:
        # Parse date
        if date.lower() == "today":
            appointment_date = datetime.now().date()
        elif date.lower() == "tomorrow":
            appointment_date = (datetime.now() + timedelta(days=1)).date()
        else:
            appointment_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Parse time
        appointment_time = datetime.strptime(time, "%H:%M").time()

        # Combine date and time
        appointment_datetime = datetime.combine(appointment_date, appointment_time)

        # Check if time is in the past
        if appointment_datetime < datetime.now():
            return "I cannot create appointments in the past. Please provide a future date and time."

        # Create appointment ID
        appointment_id = f"apt_{datetime.now().timestamp()}"

        # Store appointment
        appointment = {
            "id": appointment_id,
            "title": title,
            "datetime": appointment_datetime.isoformat(),
            "duration_minutes": duration_minutes,
            "description": description,
            "location": location,
            "created_at": datetime.now().isoformat()
        }

        # Check for conflicts
        conflict = await check_conflicts(appointment_datetime, duration_minutes)
        if conflict:
            return (
                f"There's a scheduling conflict. You have '{conflict['title']}' "
                f"at {conflict['datetime']}. Would you like to schedule at a different time?"
            )

        # Store in calendar
        calendar_store[appointment_id] = appointment

        # Format confirmation
        formatted_date = appointment_datetime.strftime("%B %d, %Y")
        formatted_time = appointment_datetime.strftime("%I:%M %p")

        response = (
            f"I've scheduled '{title}' for {formatted_date} at {formatted_time} "
            f"for {duration_minutes} minutes."
        )

        if location:
            response += f" Location: {location}."

        if description:
            response += f" Note: {description}"

        return response

    except ValueError as e:
        logger.error(f"Date/time parsing error: {e}")
        return (
            "I couldn't understand the date or time format. "
            "Please use YYYY-MM-DD for date and HH:MM for time."
        )

    except Exception as e:
        logger.error(f"Calendar creation error: {e}")
        return "I encountered an error while creating the appointment."


@llm.function_tool(
    description="Check calendar availability for a specific date and time"
)
async def check_availability(
    date: str,
    time: Optional[str] = None
) -> str:
    """
    Check calendar availability

    Args:
        date: Date to check (YYYY-MM-DD, "today", or "tomorrow")
        time: Optional specific time to check (HH:MM)

    Returns:
        Availability information
    """
    try:
        # Parse date
        if date.lower() == "today":
            check_date = datetime.now().date()
        elif date.lower() == "tomorrow":
            check_date = (datetime.now() + timedelta(days=1)).date()
        else:
            check_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Get appointments for the date
        appointments_on_date = []
        for apt_id, apt in calendar_store.items():
            apt_datetime = datetime.fromisoformat(apt["datetime"])
            if apt_datetime.date() == check_date:
                appointments_on_date.append(apt)

        # Sort by time
        appointments_on_date.sort(key=lambda x: x["datetime"])

        if not appointments_on_date:
            return f"You have no appointments on {check_date.strftime('%B %d, %Y')}. The entire day is available."

        # If specific time requested
        if time:
            check_time = datetime.strptime(time, "%H:%M").time()
            check_datetime = datetime.combine(check_date, check_time)

            for apt in appointments_on_date:
                apt_datetime = datetime.fromisoformat(apt["datetime"])
                apt_end = apt_datetime + timedelta(minutes=apt["duration_minutes"])

                if apt_datetime <= check_datetime < apt_end:
                    return (
                        f"You are not available at {time}. "
                        f"You have '{apt['title']}' from "
                        f"{apt_datetime.strftime('%I:%M %p')} to {apt_end.strftime('%I:%M %p')}."
                    )

            return f"You are available at {time} on {check_date.strftime('%B %d, %Y')}."

        # List all appointments for the day
        response = f"Your schedule for {check_date.strftime('%B %d, %Y')}:\n"
        for apt in appointments_on_date:
            apt_datetime = datetime.fromisoformat(apt["datetime"])
            response += f"- {apt_datetime.strftime('%I:%M %p')}: {apt['title']} ({apt['duration_minutes']} min)\n"

        # Find available slots
        available_slots = find_available_slots(appointments_on_date, check_date)
        if available_slots:
            response += "\nAvailable time slots: " + ", ".join(available_slots)

        return response

    except Exception as e:
        logger.error(f"Availability check error: {e}")
        return "I encountered an error while checking availability."


@llm.function_tool(
    description="List upcoming calendar appointments"
)
async def list_appointments(
    days_ahead: int = 7
) -> str:
    """
    List upcoming appointments

    Args:
        days_ahead: Number of days to look ahead (default 7)

    Returns:
        List of upcoming appointments
    """
    try:
        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)

        upcoming = []
        for apt_id, apt in calendar_store.items():
            apt_datetime = datetime.fromisoformat(apt["datetime"])
            if now <= apt_datetime <= end_date:
                upcoming.append(apt)

        if not upcoming:
            return f"You have no appointments in the next {days_ahead} days."

        # Sort by datetime
        upcoming.sort(key=lambda x: x["datetime"])

        response = f"Your upcoming appointments for the next {days_ahead} days:\n"
        for apt in upcoming:
            apt_datetime = datetime.fromisoformat(apt["datetime"])
            formatted_date = apt_datetime.strftime("%B %d at %I:%M %p")
            response += f"- {formatted_date}: {apt['title']}"

            if apt.get("location"):
                response += f" at {apt['location']}"

            response += f" ({apt['duration_minutes']} minutes)\n"

        return response

    except Exception as e:
        logger.error(f"List appointments error: {e}")
        return "I encountered an error while listing appointments."


@llm.function_tool(
    description="Cancel or delete a calendar appointment"
)
async def cancel_appointment(
    title: str,
    date: Optional[str] = None
) -> str:
    """
    Cancel an appointment

    Args:
        title: Title of the appointment to cancel
        date: Optional date to help identify the appointment

    Returns:
        Confirmation or error message
    """
    try:
        # Find appointment by title (and optionally date)
        found_appointments = []

        for apt_id, apt in calendar_store.items():
            if title.lower() in apt["title"].lower():
                if date:
                    apt_datetime = datetime.fromisoformat(apt["datetime"])
                    if date.lower() == "today":
                        check_date = datetime.now().date()
                    elif date.lower() == "tomorrow":
                        check_date = (datetime.now() + timedelta(days=1)).date()
                    else:
                        check_date = datetime.strptime(date, "%Y-%m-%d").date()

                    if apt_datetime.date() == check_date:
                        found_appointments.append((apt_id, apt))
                else:
                    found_appointments.append((apt_id, apt))

        if not found_appointments:
            return f"I couldn't find an appointment matching '{title}'."

        if len(found_appointments) > 1:
            response = f"I found {len(found_appointments)} appointments matching '{title}':\n"
            for apt_id, apt in found_appointments:
                apt_datetime = datetime.fromisoformat(apt["datetime"])
                response += f"- {apt_datetime.strftime('%B %d at %I:%M %p')}: {apt['title']}\n"
            response += "Please be more specific about which one to cancel."
            return response

        # Cancel the appointment
        apt_id, apt = found_appointments[0]
        del calendar_store[apt_id]

        apt_datetime = datetime.fromisoformat(apt["datetime"])
        return (
            f"I've cancelled '{apt['title']}' scheduled for "
            f"{apt_datetime.strftime('%B %d at %I:%M %p')}."
        )

    except Exception as e:
        logger.error(f"Cancel appointment error: {e}")
        return "I encountered an error while cancelling the appointment."


@llm.function_tool(
    description="Reschedule an existing appointment to a new date/time"
)
async def reschedule_appointment(
    title: str,
    new_date: str,
    new_time: str,
    duration_minutes: Optional[int] = None
) -> str:
    """
    Reschedule an appointment

    Args:
        title: Title of the appointment to reschedule
        new_date: New date (YYYY-MM-DD, "today", or "tomorrow")
        new_time: New time (HH:MM)
        duration_minutes: Optional new duration

    Returns:
        Confirmation or error message
    """
    try:
        # Find the appointment
        found = None
        for apt_id, apt in calendar_store.items():
            if title.lower() in apt["title"].lower():
                found = (apt_id, apt)
                break

        if not found:
            return f"I couldn't find an appointment matching '{title}'."

        apt_id, apt = found

        # Parse new date and time
        if new_date.lower() == "today":
            new_date_obj = datetime.now().date()
        elif new_date.lower() == "tomorrow":
            new_date_obj = (datetime.now() + timedelta(days=1)).date()
        else:
            new_date_obj = datetime.strptime(new_date, "%Y-%m-%d").date()

        new_time_obj = datetime.strptime(new_time, "%H:%M").time()
        new_datetime = datetime.combine(new_date_obj, new_time_obj)

        if new_datetime < datetime.now():
            return "I cannot reschedule appointments to the past."

        # Check for conflicts
        duration = duration_minutes or apt["duration_minutes"]
        conflict = await check_conflicts(new_datetime, duration, exclude_id=apt_id)
        if conflict:
            return (
                f"There's a conflict at the new time. You have '{conflict['title']}' "
                f"at {conflict['datetime']}."
            )

        # Update appointment
        old_datetime = datetime.fromisoformat(apt["datetime"])
        apt["datetime"] = new_datetime.isoformat()
        if duration_minutes:
            apt["duration_minutes"] = duration_minutes

        return (
            f"I've rescheduled '{apt['title']}' from "
            f"{old_datetime.strftime('%B %d at %I:%M %p')} to "
            f"{new_datetime.strftime('%B %d at %I:%M %p')}."
        )

    except Exception as e:
        logger.error(f"Reschedule error: {e}")
        return "I encountered an error while rescheduling the appointment."


# Helper functions

async def check_conflicts(
    datetime_obj: datetime,
    duration_minutes: int,
    exclude_id: Optional[str] = None
) -> Optional[Dict]:
    """Check for scheduling conflicts"""
    end_time = datetime_obj + timedelta(minutes=duration_minutes)

    for apt_id, apt in calendar_store.items():
        if apt_id == exclude_id:
            continue

        apt_datetime = datetime.fromisoformat(apt["datetime"])
        apt_end = apt_datetime + timedelta(minutes=apt["duration_minutes"])

        # Check for overlap
        if (datetime_obj < apt_end and end_time > apt_datetime):
            return apt

    return None


def find_available_slots(appointments: List[Dict], date: datetime.date) -> List[str]:
    """Find available time slots in a day"""
    slots = []
    business_start = datetime.combine(date, datetime.strptime("09:00", "%H:%M").time())
    business_end = datetime.combine(date, datetime.strptime("17:00", "%H:%M").time())

    if not appointments:
        return ["9:00 AM - 5:00 PM"]

    # Check slot before first appointment
    first_apt = datetime.fromisoformat(appointments[0]["datetime"])
    if first_apt > business_start:
        slots.append(f"{business_start.strftime('%I:%M %p')} - {first_apt.strftime('%I:%M %p')}")

    # Check slots between appointments
    for i in range(len(appointments) - 1):
        current_end = datetime.fromisoformat(appointments[i]["datetime"]) + \
                     timedelta(minutes=appointments[i]["duration_minutes"])
        next_start = datetime.fromisoformat(appointments[i + 1]["datetime"])

        if next_start > current_end:
            slots.append(f"{current_end.strftime('%I:%M %p')} - {next_start.strftime('%I:%M %p')}")

    # Check slot after last appointment
    last_apt = datetime.fromisoformat(appointments[-1]["datetime"])
    last_end = last_apt + timedelta(minutes=appointments[-1]["duration_minutes"])
    if last_end < business_end:
        slots.append(f"{last_end.strftime('%I:%M %p')} - {business_end.strftime('%I:%M %p')}")

    return slots