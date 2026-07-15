"""
Comprehensive test suite for ClaudeVoice Agent
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

# Import agent modules
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.main import ClaudeVoiceAgent, entrypoint
from agent.config import Config
from agent.tools.weather import weather_tool, weather_forecast
from agent.tools.calendar import calendar_tool, check_availability
from agent.tools.database import database_query, get_customer_info
from agent.tools.voicemail import detect_voicemail, VoicemailHandler


class TestClaudeVoiceAgent:
    """Test the main agent class"""

    def test_agent_initialization(self):
        """Test agent initializes correctly"""
        agent = ClaudeVoiceAgent()
        assert agent.agent_name == "claudevoice-agent"
        assert not agent.is_telephony
        assert agent.call_metadata == {}

    def test_system_instructions_phone(self):
        """Test system instructions for phone calls"""
        agent = ClaudeVoiceAgent()
        instructions = agent.get_system_instructions()

        assert "PHONE CALL BEHAVIOR" in instructions
        assert "voicemail" in instructions.lower()
        assert "Indianapolis Pickleball Club" in instructions

    def test_system_instructions_include_persona(self):
        """Test the phone-only agent includes the maintained persona."""
        agent = ClaudeVoiceAgent()
        instructions = agent.get_system_instructions()

        assert "You are **ACE**" in instructions
        assert "QUALITY ASSURANCE LITMUS TEST" in instructions


class TestConfig:
    """Test startup configuration boundaries."""

    def test_optional_integrations_do_not_block_startup(self, monkeypatch):
        required = {
            "LIVEKIT_URL": "wss://example.invalid",
            "LIVEKIT_API_KEY": "test-key",
            "LIVEKIT_API_SECRET": "test-secret",
            "OPENAI_API_KEY": "test-openai-key",
        }
        for name, value in required.items():
            monkeypatch.setenv(name, value)
        monkeypatch.delenv("COURTRESERVE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_ASSISTANT_ID", raising=False)

        assert Config().validate() is True

    def test_missing_required_credentials_are_named(self, monkeypatch):
        for name in (
            "LIVEKIT_URL",
            "LK_URL",
            "LIVEKIT_API_KEY",
            "LK_API_KEY",
            "LIVEKIT_API_SECRET",
            "LK_API_SECRET",
            "OPENAI_API_KEY",
        ):
            monkeypatch.delenv(name, raising=False)

        with pytest.raises(ValueError, match="LIVEKIT_URL.*OPENAI_API_KEY"):
            Config().validate()


class TestWeatherTools:
    """Test weather tool functions"""

    @pytest.mark.asyncio
    async def test_weather_tool_success(self):
        """Test weather tool with mock API response"""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "main": {"temp": 20, "feels_like": 18, "humidity": 65},
                "weather": [{"description": "partly cloudy"}],
                "wind": {"speed": 5},
            }
            mock_get.return_value = mock_response

            result = await weather_tool("London", "metric")

            assert "London" in result
            assert "20°C" in result
            assert "partly cloudy" in result
            assert "65%" in result

    @pytest.mark.asyncio
    async def test_weather_tool_city_not_found(self):
        """Test weather tool when city is not found"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            result = await weather_tool("InvalidCity")

            assert "couldn't find" in result
            assert "InvalidCity" in result

    @pytest.mark.asyncio
    async def test_weather_forecast(self):
        """Test weather forecast function"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "list": [
                    {
                        "dt_txt": "2024-01-20 12:00:00",
                        "main": {"temp": 15},
                        "weather": [{"description": "clear sky"}],
                    },
                    {
                        "dt_txt": "2024-01-20 15:00:00",
                        "main": {"temp": 18},
                        "weather": [{"description": "clear sky"}],
                    },
                ]
            }
            mock_get.return_value = mock_response

            result = await weather_forecast("London", 1)

            assert "forecast" in result.lower()
            assert "2024-01-20" in result


class TestCalendarTools:
    """Test calendar management tools"""

    @pytest.mark.asyncio
    async def test_create_appointment(self):
        """Test creating a calendar appointment"""
        from agent.tools import calendar

        # Clear calendar store
        calendar.calendar_store.clear()

        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = await calendar_tool(
            title="Team Meeting",
            date=future_date,
            time="14:00",
            duration_minutes=60,
            location="Conference Room A",
        )

        assert "scheduled" in result
        assert "Team Meeting" in result
        assert "Conference Room A" in result
        assert len(calendar.calendar_store) == 1

    @pytest.mark.asyncio
    async def test_check_availability(self):
        """Test checking calendar availability"""
        from agent.tools import calendar

        # Add a test appointment
        calendar.calendar_store.clear()
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        await calendar_tool(
            title="Existing Meeting",
            date=future_date,
            time="10:00",
            duration_minutes=60,
        )

        # Check availability for the same day
        result = await check_availability(future_date)

        assert "Existing Meeting" in result
        assert "10:00" in result.lower() or "10:00" in result

    @pytest.mark.asyncio
    async def test_appointment_conflict(self):
        """Test detecting scheduling conflicts"""
        from agent.tools import calendar

        calendar.calendar_store.clear()

        # Create first appointment
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        await calendar_tool(
            title="First Meeting", date=future_date, time="14:00", duration_minutes=60
        )

        # Try to create conflicting appointment
        result = await calendar_tool(
            title="Second Meeting", date=future_date, time="14:30", duration_minutes=60
        )

        assert "conflict" in result.lower()
        assert "First Meeting" in result


class TestDatabaseTools:
    """Test database query tools"""

    @pytest.mark.asyncio
    async def test_database_query_customers(self):
        """Test querying customer data"""
        result = await database_query("customers")

        assert "customers" in result.lower() or "John Doe" in result
        assert result != ""

    @pytest.mark.asyncio
    async def test_get_customer_info(self):
        """Test getting specific customer information"""
        result = await get_customer_info("John Doe")

        assert "John Doe" in result
        assert "email" in result.lower()
        assert "phone" in result.lower() or "+1234567890" in result

    @pytest.mark.asyncio
    async def test_database_query_with_filter(self):
        """Test database query with filters"""
        result = await database_query(
            "customers", filters=json.dumps({"status": "active"})
        )

        # Should return active customers
        assert (
            "active" in result.lower() or "John Doe" in result or "Jane Smith" in result
        )
        assert "Bob Johnson" not in result or "inactive" not in result.lower()


class TestVoicemailDetection:
    """Test voicemail detection functionality"""

    @pytest.mark.asyncio
    async def test_detect_voicemail_positive(self):
        """Test detecting a voicemail greeting"""
        transcript = "Hi, you've reached John's voicemail. Please leave a message after the beep."

        result = await detect_voicemail(transcript)

        assert "Voicemail detected" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_detect_voicemail_negative(self):
        """Test detecting human answer"""
        transcript = "Hello, this is John speaking."

        result = await detect_voicemail(transcript)

        assert "human" in result.lower() or "Voicemail detected" not in result

    def test_voicemail_handler_state_transitions(self):
        """Test voicemail handler state management"""
        handler = VoicemailHandler()

        assert handler.state == "listening"

        # Simulate voicemail detection
        handler.state = "detected"
        assert handler.state == "detected"

        # Simulate leaving message
        handler.state = "leaving_message"
        assert handler.state == "leaving_message"

        # Reset
        handler.reset()
        assert handler.state == "listening"
        assert handler.transcript_buffer == ""


class TestAgentIntegration:
    """Integration tests for the full agent"""

    @pytest.mark.asyncio
    async def test_agent_entrypoint_mock(self):
        """Test agent entrypoint with mocked LiveKit context"""
        # Create mock context
        mock_ctx = MagicMock()
        mock_ctx.connect = AsyncMock()
        mock_ctx.room = MagicMock()
        mock_ctx.room.name = "call-123456-test"
        mock_ctx.room.metadata = json.dumps(
            {"from_number": "+1234567890", "to_number": "+0987654321"}
        )
        mock_ctx.connect = AsyncMock()

        mock_session = MagicMock()
        mock_session.start = AsyncMock()
        mock_session.aclose = AsyncMock()
        mock_session.on = Mock()

        with (
            patch("agent.main.IPCAssistant") as mock_assistant,
            patch("agent.main.AgentSession", return_value=mock_session),
            patch("agent.main.silero.VAD.load", return_value=Mock()),
            patch("agent.main.openai.STT", return_value=Mock()),
            patch("agent.main.openai.LLM", return_value=Mock()),
            patch("agent.main.openai.TTS", return_value=Mock()),
            patch("agent.main.HAS_BACKGROUND_AUDIO", False),
        ):
            mock_assistant.return_value.transcription_node = None
            try:
                await asyncio.wait_for(entrypoint(mock_ctx), timeout=0.2)
            except asyncio.TimeoutError:
                pass

            mock_ctx.connect.assert_awaited_once()
            mock_session.start.assert_awaited_once()


class TestEndToEnd:
    """End-to-end workflow tests"""

    @pytest.mark.asyncio
    async def test_complete_call_flow(self):
        """Test a complete call flow scenario"""
        from agent.tools import calendar

        # Clear calendar
        calendar.calendar_store.clear()

        # Simulate scheduling appointment via voice
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        appointment_result = await calendar_tool(
            title="Doctor Appointment",
            date=future_date,
            time="15:00",
            duration_minutes=30,
            description="Annual checkup",
        )

        assert "scheduled" in appointment_result

        # Check availability
        availability_result = await check_availability(future_date, "15:00")
        assert (
            "not available" in availability_result.lower()
            or "Doctor Appointment" in availability_result
        )

        # Query customer info
        customer_result = await get_customer_info("John Doe")
        assert "John Doe" in customer_result

        # Check weather
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "main": {"temp": 22, "feels_like": 20, "humidity": 60},
                "weather": [{"description": "sunny"}],
                "wind": {"speed": 3},
            }
            mock_get.return_value = mock_response

            weather_result = await weather_tool("New York")
            assert "New York" in weather_result


@pytest.fixture
def mock_livekit_room():
    """Fixture for mocked LiveKit room"""
    room = Mock()
    room.name = "test-room"
    room.metadata = "{}"
    room.local_participant = Mock()
    room.remote_participants = []
    return room


@pytest.fixture
def mock_job_context(mock_livekit_room):
    """Fixture for mocked JobContext"""
    ctx = AsyncMock()
    ctx.room = mock_livekit_room
    ctx.api = Mock()
    return ctx


# Performance tests
class TestPerformance:
    """Performance and load tests"""

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test handling multiple concurrent tool calls"""
        tasks = []

        # Create multiple concurrent requests
        for i in range(10):
            if i % 3 == 0:
                tasks.append(database_query("customers"))
            elif i % 3 == 1:
                tasks.append(check_availability("2025-12-01"))
            else:
                with patch("httpx.AsyncClient.get") as mock_get:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "main": {"temp": 20, "feels_like": 18, "humidity": 65},
                        "weather": [{"description": "clear"}],
                        "wind": {"speed": 5},
                    }
                    mock_get.return_value = mock_response
                    tasks.append(weather_tool(f"City{i}"))

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Verify all completed
        assert len(results) == 10
        assert all(result for result in results)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
