"""
Configuration settings for ClaudeVoice Agent
"""

import os
from typing import Dict
from enum import Enum


class OpenAIVoice(Enum):
    """Available OpenAI TTS voices"""

    ALLOY = "alloy"  # Neutral and balanced
    ECHO = "echo"  # Warm and engaging
    FABLE = "fable"  # Expressive and dynamic
    ONYX = "onyx"  # Deep and authoritative
    NOVA = "nova"  # Friendly and conversational
    SHIMMER = "shimmer"  # Soft and pleasant


class OpenAITTSModel(Enum):
    """Available OpenAI TTS models"""

    TTS_1 = "tts-1"  # Standard quality, lower latency
    TTS_1_HD = "tts-1-hd"  # Higher quality, slightly higher latency


class OpenAISTTModel(Enum):
    """Available OpenAI STT models"""

    WHISPER_1 = "whisper-1"  # Current Whisper model


class Config:
    """Central configuration for ClaudeVoice Agent"""

    def __init__(self):
        # Load from environment with defaults
        self.load_from_env()

    def load_from_env(self):
        """Load configuration from environment variables"""

        # LiveKit Configuration (support both naming conventions)
        self.livekit_url = os.getenv("LIVEKIT_URL") or os.getenv("LK_URL", "")
        self.livekit_api_key = os.getenv("LIVEKIT_API_KEY") or os.getenv(
            "LK_API_KEY", ""
        )
        self.livekit_api_secret = os.getenv("LIVEKIT_API_SECRET") or os.getenv(
            "LK_API_SECRET", ""
        )

        # OpenAI Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_assistant_id = os.getenv("OPENAI_ASSISTANT_ID", "")

        # CourtReserve API Configuration
        self.courtreserve_api_key = os.getenv("COURTRESERVE_API_KEY", "")
        self.courtreserve_base_url = os.getenv(
            "COURTRESERVE_BASE_URL", "https://api.courtreserve.com"
        )
        self.courtreserve_org_id = os.getenv("COURTRESERVE_ORG_ID", "11710")

        # Model Settings
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4-turbo")
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "150"))

        # STT Settings
        self.stt_model = os.getenv("STT_MODEL", OpenAISTTModel.WHISPER_1.value)
        self.stt_language = os.getenv("STT_LANGUAGE", "en")  # None for auto-detect

        # TTS Settings
        self.tts_model = os.getenv("TTS_MODEL", OpenAITTSModel.TTS_1.value)
        self.tts_voice = os.getenv("TTS_VOICE", OpenAIVoice.ALLOY.value)
        self.tts_speed = float(os.getenv("TTS_SPEED", "1.0"))

        # Agent Settings
        self.agent_name = os.getenv("AGENT_NAME", "claudevoice-agent")
        self.agent_port = int(os.getenv("AGENT_PORT", "8080"))

        # VAD Settings
        self.vad_min_speech_duration = float(os.getenv("VAD_MIN_SPEECH", "0.1"))
        self.vad_min_silence_duration = float(os.getenv("VAD_MIN_SILENCE", "0.5"))
        self.vad_min_silence_duration_phone = float(
            os.getenv("VAD_MIN_SILENCE_PHONE", "0.3")
        )

        # Database Settings
        self.db_type = os.getenv("DB_TYPE", "demo")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(
            os.getenv("DB_PORT", "5432") if os.getenv("DB_PORT") else 5432
        )
        self.db_user = os.getenv("DB_USER", "")
        self.db_password = os.getenv("DB_PASSWORD", "")
        self.db_name = os.getenv("DB_NAME", "claudevoice")

        # External APIs
        self.weather_api_key = os.getenv("OPENWEATHER_API_KEY", "")

        # Feature Flags
        self.enable_noise_cancellation = (
            os.getenv("ENABLE_NOISE_CANCELLATION", "true").lower() == "true"
        )
        self.enable_voicemail_detection = (
            os.getenv("ENABLE_VOICEMAIL_DETECTION", "true").lower() == "true"
        )
        self.enable_call_recording = (
            os.getenv("ENABLE_CALL_RECORDING", "false").lower() == "true"
        )

    def get_tts_voice_info(self) -> Dict[str, str]:
        """Get information about the current TTS voice"""
        voice_descriptions = {
            OpenAIVoice.ALLOY.value: "Neutral and balanced voice",
            OpenAIVoice.ECHO.value: "Warm and engaging voice",
            OpenAIVoice.FABLE.value: "Expressive and dynamic voice",
            OpenAIVoice.ONYX.value: "Deep and authoritative voice",
            OpenAIVoice.NOVA.value: "Friendly and conversational voice",
            OpenAIVoice.SHIMMER.value: "Soft and pleasant voice",
        }
        return {
            "voice": self.tts_voice,
            "description": voice_descriptions.get(self.tts_voice, "Unknown voice"),
            "model": self.tts_model,
            "speed": self.tts_speed,
        }

    def validate(self) -> bool:
        """Validate required configuration"""
        required = [
            self.livekit_url,
            self.livekit_api_key,
            self.livekit_api_secret,
            self.openai_api_key,
        ]

        if not all(required):
            missing = []
            if not self.livekit_url:
                missing.append("LIVEKIT_URL")
            if not self.livekit_api_key:
                missing.append("LIVEKIT_API_KEY")
            if not self.livekit_api_secret:
                missing.append("LIVEKIT_API_SECRET")
            if not self.openai_api_key:
                missing.append("OPENAI_API_KEY")
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return True

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"Config(agent_name={self.agent_name}, "
            f"llm_model={self.llm_model}, "
            f"tts_voice={self.tts_voice}, "
            f"stt_language={self.stt_language})"
        )


# Global config instance
config = Config()
