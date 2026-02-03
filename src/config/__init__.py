"""
Config module
=============
YAML-based configuration for Felix Hospital Voice AI.

Usage:
    from config import config

    # Get hospital name
    hospital_name = config.hospital_name

    # Get agent prompt with variable substitution
    prompt = config.get_agent_prompt("orchestrator")

    # Get task prompt
    task_prompt = config.get_task_prompt("data_collection", memory_context="...")

    # Get STT/TTS/LLM config
    stt_config = config.stt_config
    tts_config = config.tts_config
    llm_config = config.llm_config

Configuration files:
- settings.yaml: Hospital info, STT/TTS/LLM config, feature flags
- agents.yaml: Agent prompts with variable substitution
- tasks.yaml: Task prompts with variable substitution
"""

from config.config_loader import config, ConfigLoader, get_config, reload_config
from config.settings import settings, Settings

__all__ = [
    "config",
    "ConfigLoader",
    "get_config",
    "reload_config",
    "settings",
    "Settings",
]
