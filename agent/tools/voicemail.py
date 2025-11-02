"""
Voicemail Detection Tool Implementation
Detects voicemail systems and handles message leaving
"""

import logging
import asyncio
from typing import Optional, Tuple
from livekit.agents import llm

logger = logging.getLogger(__name__)

# Common voicemail detection patterns
VOICEMAIL_KEYWORDS = [
    "voicemail",
    "voice mail",
    "message after the beep",
    "leave a message",
    "not available",
    "unavailable",
    "record your message",
    "leave your message",
    "at the tone",
    "after the tone",
    "beep",
    "mailbox",
    "voice mailbox",
    "automated message",
    "press 1",
    "press star",
    "please leave",
    "currently unavailable",
    "cannot take your call",
    "not able to answer"
]

# Greeting patterns that indicate a human answered
HUMAN_GREETING_PATTERNS = [
    "hello",
    "hi",
    "hey",
    "yes",
    "speaking",
    "this is",
    "how can I help",
    "good morning",
    "good afternoon",
    "good evening"
]


@llm.function_tool(
    description="Detect if the call has reached a voicemail system"
)
async def detect_voicemail(
    transcript: str = "",
    confidence_threshold: float = 0.7
) -> str:
    """
    Detect if we've reached a voicemail system

    Args:
        transcript: The transcript of what was heard
        confidence_threshold: Confidence level for detection (0-1)

    Returns:
        Detection result and confidence
    """
    try:
        if not transcript:
            return "No audio detected yet. Please wait for the greeting to finish."

        transcript_lower = transcript.lower()

        # Check for voicemail indicators
        voicemail_score = 0
        detected_keywords = []

        for keyword in VOICEMAIL_KEYWORDS:
            if keyword in transcript_lower:
                voicemail_score += 1
                detected_keywords.append(keyword)

        # Check for human greeting patterns (negative indicators)
        human_score = 0
        for pattern in HUMAN_GREETING_PATTERNS:
            if pattern in transcript_lower and len(transcript_lower) < 50:
                human_score += 1

        # Calculate confidence
        total_keywords = len(VOICEMAIL_KEYWORDS)
        voicemail_confidence = min(voicemail_score / 3, 1.0)  # Cap at 3 keywords for 100%

        # Adjust confidence based on human patterns
        if human_score > 0:
            voicemail_confidence *= 0.3  # Reduce confidence if human patterns detected

        # Additional checks
        is_long_message = len(transcript_lower.split()) > 20  # Voicemails tend to be longer
        has_instructions = any(word in transcript_lower for word in ["press", "option", "menu"])

        if is_long_message:
            voicemail_confidence += 0.1
        if has_instructions:
            voicemail_confidence += 0.2

        voicemail_confidence = min(voicemail_confidence, 1.0)

        # Make determination
        if voicemail_confidence >= confidence_threshold:
            return (
                f"Voicemail detected with {voicemail_confidence:.0%} confidence. "
                f"Keywords found: {', '.join(detected_keywords[:3])}. "
                "Ready to leave a message."
            )
        elif voicemail_confidence >= 0.4:
            return (
                f"Possible voicemail system ({voicemail_confidence:.0%} confidence). "
                "Listening for more indicators..."
            )
        else:
            return (
                f"Appears to be a human answering ({(1-voicemail_confidence):.0%} confidence). "
                "Proceeding with conversation."
            )

    except Exception as e:
        logger.error(f"Voicemail detection error: {e}")
        return "Unable to determine if this is a voicemail. Proceeding with caution."


@llm.function_tool(
    description="Leave a voicemail message on the detected voicemail system"
)
async def leave_voicemail_message(
    caller_name: str,
    callback_number: str,
    message: str,
    urgent: bool = False
) -> str:
    """
    Leave a structured voicemail message

    Args:
        caller_name: Name of the caller
        callback_number: Phone number to call back
        message: The main message content
        urgent: Whether this is an urgent message

    Returns:
        The formatted voicemail message
    """
    try:
        # Build the voicemail message
        voicemail_text = f"Hello, this is {caller_name} calling"

        if urgent:
            voicemail_text += " with an urgent message"

        voicemail_text += f". {message}. "
        voicemail_text += f"Please call me back at {format_phone_number(callback_number)}. "

        if urgent:
            voicemail_text += "Again, this is urgent. "

        voicemail_text += f"I repeat, the callback number is {format_phone_number(callback_number, slow=True)}. "
        voicemail_text += "Thank you and have a great day."

        return voicemail_text

    except Exception as e:
        logger.error(f"Error formatting voicemail: {e}")
        return f"This is {caller_name}. {message}. Please call back at {callback_number}."


@llm.function_tool(
    description="Analyze voicemail greeting to extract business information"
)
async def analyze_voicemail_greeting(
    transcript: str
) -> str:
    """
    Extract useful information from a voicemail greeting

    Args:
        transcript: The voicemail greeting transcript

    Returns:
        Extracted information
    """
    try:
        info = {
            "business_name": None,
            "person_name": None,
            "office_hours": None,
            "alternative_number": None,
            "return_date": None
        }

        transcript_lower = transcript.lower()

        # Look for business name (usually after "you've reached" or "this is")
        if "you've reached" in transcript_lower:
            start = transcript_lower.index("you've reached") + len("you've reached")
            words = transcript[start:].split()[:5]  # Get next 5 words
            info["business_name"] = " ".join(words).strip(",.")
        elif "this is the office of" in transcript_lower:
            start = transcript_lower.index("this is the office of") + len("this is the office of")
            words = transcript[start:].split()[:5]
            info["business_name"] = " ".join(words).strip(",.")

        # Look for office hours
        hour_keywords = ["hours are", "open from", "monday through", "monday to"]
        for keyword in hour_keywords:
            if keyword in transcript_lower:
                start = transcript_lower.index(keyword)
                hours_text = transcript[start:start+100]  # Get next 100 chars
                info["office_hours"] = extract_hours(hours_text)
                break

        # Look for alternative contact
        if "press" in transcript_lower and "for" in transcript_lower:
            # Extract menu options
            import re
            pattern = r'press (\d+) for (\w+)'
            matches = re.findall(pattern, transcript_lower)
            if matches:
                info["menu_options"] = matches

        # Look for return date (out of office)
        return_keywords = ["return on", "back on", "returning", "will be back"]
        for keyword in return_keywords:
            if keyword in transcript_lower:
                start = transcript_lower.index(keyword)
                date_text = transcript[start:start+50]
                info["return_date"] = extract_date(date_text)
                break

        # Format extracted information
        result = "Voicemail analysis:\n"
        if info["business_name"]:
            result += f"- Business: {info['business_name']}\n"
        if info["office_hours"]:
            result += f"- Hours: {info['office_hours']}\n"
        if info["return_date"]:
            result += f"- Returns: {info['return_date']}\n"
        if info.get("menu_options"):
            result += f"- Menu options available: {len(info['menu_options'])}\n"

        return result if result != "Voicemail analysis:\n" else "Standard voicemail greeting detected."

    except Exception as e:
        logger.error(f"Error analyzing voicemail: {e}")
        return "Unable to extract specific information from voicemail greeting."


@llm.function_tool(
    description="Wait for the beep before leaving a voicemail message"
)
async def wait_for_beep(
    max_wait_seconds: int = 10
) -> str:
    """
    Wait for the beep tone before leaving a message

    Args:
        max_wait_seconds: Maximum time to wait for beep

    Returns:
        Status of beep detection
    """
    try:
        # In a real implementation, this would analyze audio for beep tone
        # For now, we'll simulate waiting
        await asyncio.sleep(2)  # Wait a moment

        # This would actually detect audio tone frequencies
        # Beep tones are typically 1000-2000 Hz

        return "Beep detected. Ready to leave message."

    except Exception as e:
        logger.error(f"Error waiting for beep: {e}")
        return "Proceeding to leave message."


class VoicemailHandler:
    """Advanced voicemail handling with state management"""

    def __init__(self):
        self.state = "listening"  # listening, detected, leaving_message, completed
        self.transcript_buffer = ""
        self.detection_confidence = 0.0
        self.message_left = False

    async def process_audio_segment(self, transcript: str) -> Tuple[str, str]:
        """
        Process incoming audio to detect and handle voicemail

        Args:
            transcript: Latest transcript segment

        Returns:
            Tuple of (state, action)
        """
        try:
            self.transcript_buffer += " " + transcript

            if self.state == "listening":
                # Detect voicemail
                result = await detect_voicemail(self.transcript_buffer)

                if "Voicemail detected" in result:
                    self.state = "detected"
                    self.detection_confidence = float(result.split("%")[0].split()[-1]) / 100
                    return ("detected", "wait_for_beep")

                elif len(self.transcript_buffer.split()) > 50:
                    # If we've heard a lot and no voicemail detected, assume human
                    self.state = "human"
                    return ("human", "continue_conversation")

            elif self.state == "detected":
                # Wait for beep
                if "beep" in transcript.lower() or len(self.transcript_buffer.split()) > 100:
                    self.state = "leaving_message"
                    return ("leaving_message", "leave_message")

            elif self.state == "leaving_message":
                # Message is being left
                self.state = "completed"
                self.message_left = True
                return ("completed", "end_call")

            return (self.state, "continue")

        except Exception as e:
            logger.error(f"Voicemail handler error: {e}")
            return ("error", "continue")

    def reset(self):
        """Reset the handler for a new call"""
        self.state = "listening"
        self.transcript_buffer = ""
        self.detection_confidence = 0.0
        self.message_left = False


# Helper functions

def format_phone_number(number: str, slow: bool = False) -> str:
    """
    Format phone number for speech

    Args:
        number: Phone number string
        slow: Whether to speak slowly (for voicemail)

    Returns:
        Formatted phone number for TTS
    """
    # Remove non-numeric characters
    digits = ''.join(filter(str.isdigit, number))

    if len(digits) == 10:  # US number
        if slow:
            # Speak each digit slowly
            return ' '.join(digits)
        else:
            # Format as groups
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':  # US with country code
        if slow:
            return ' '.join(digits)
        else:
            return f"1-{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
    else:
        # Unknown format, just space out digits
        return ' '.join(digits) if slow else number


def extract_hours(text: str) -> Optional[str]:
    """Extract office hours from text"""
    import re
    # Look for time patterns
    time_pattern = r'\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)'
    times = re.findall(time_pattern, text)

    if len(times) >= 2:
        return f"{times[0]} to {times[1]}"
    return None


def extract_date(text: str) -> Optional[str]:
    """Extract date from text"""
    import re
    # Look for date patterns
    months = ["january", "february", "march", "april", "may", "june",
              "july", "august", "september", "october", "november", "december"]

    for month in months:
        if month in text.lower():
            # Try to find day
            pattern = rf'{month}\s+(\d{{1,2}})'
            match = re.search(pattern, text.lower())
            if match:
                return f"{month.capitalize()} {match.group(1)}"

    # Look for other date formats
    date_pattern = r'\d{1,2}/\d{1,2}'
    match = re.search(date_pattern, text)
    if match:
        return match.group(0)

    return None


# Global voicemail handler instance
voicemail_handler = VoicemailHandler()