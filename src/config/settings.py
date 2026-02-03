"""
Application Settings
====================
Loads configuration from environment variables and YAML files.
This module provides backward compatibility while transitioning to YAML-based config.
"""

from pydantic_settings import BaseSettings
from config.config_loader import config as yaml_config


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # LiveKit Configuration (from environment)
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"

    # LLM Configuration (from environment - API keys)
    openai_api_key: str

    # Feature Flags (can be overridden by YAML)
    enable_living_memory: bool = True
    enable_mock_api: bool = True

    # Current Date (for testing)
    current_date: str = "2026-01-20"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow extra env vars like deepgram_api_key, sarvam_api_key, etc.

    # ========================================
    # YAML Config Proxies
    # ========================================
    # These properties provide access to YAML config for backward compatibility

    @property
    def hospital_name(self) -> str:
        """Get hospital name from YAML config."""
        return yaml_config.hospital_name

    @property
    def agent_name(self) -> str:
        """Get AI agent name from YAML config."""
        return yaml_config.agent_name

    @property
    def facilities(self) -> list:
        """Get facilities from YAML config."""
        return yaml_config.facilities

    @property
    def stt_provider(self) -> str:
        """Get STT provider from YAML config."""
        return yaml_config.stt_config.get("provider", "sarvam")

    @property
    def stt_language(self) -> str:
        """Get STT language from YAML config."""
        return yaml_config.stt_config.get("language", "hi-IN")

    @property
    def tts_provider(self) -> str:
        """Get TTS provider from YAML config."""
        return yaml_config.tts_config.get("provider", "elevenlabs")

    @property
    def tts_voice_id(self) -> str:
        """Get TTS voice ID from YAML config."""
        return yaml_config.tts_config.get("voice_id", "h3vxoHEil3T93VGdTQQu")

    @property
    def llm_provider(self) -> str:
        """Get LLM provider from YAML config."""
        return yaml_config.llm_config.get("provider", "openai")

    @property
    def llm_model(self) -> str:
        """Get LLM model from YAML config."""
        return yaml_config.llm_config.get("model", "gpt-4o-mini")

    @property
    def timing_config(self) -> dict:
        """Get timing configuration from YAML config."""
        return yaml_config.timing_config


# Global settings instance
settings = Settings()


# For convenience, also export the YAML config
def get_yaml_config():
    """Get the YAML config loader instance."""
    return yaml_config
