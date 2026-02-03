"""
Configuration Loader
====================
Loads YAML configuration files and provides variable substitution.
Makes prompts dynamic with ${variable_name} syntax.
"""

import os
import re
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

logger = logging.getLogger("felix-hospital.config")

# Get the config directory path
CONFIG_DIR = Path(__file__).parent


class ConfigLoader:
    """
    Loads and manages YAML configuration with variable substitution.

    Usage:
        config = ConfigLoader()

        # Get settings
        hospital_name = config.settings["hospital"]["name"]

        # Get agent prompt with variable substitution
        prompt = config.get_agent_prompt("orchestrator", memory_context="...")

        # Get task prompt
        task_prompt = config.get_task_prompt("data_collection", memory_context="...")
    """

    _instance: Optional["ConfigLoader"] = None

    def __new__(cls):
        """Singleton pattern - only one config loader instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._settings: Dict[str, Any] = {}
        self._agents: Dict[str, Any] = {}
        self._tasks: Dict[str, Any] = {}

        self._load_all_configs()
        self._initialized = True
        logger.info("Configuration loaded successfully")

    def _load_all_configs(self) -> None:
        """Load all YAML configuration files."""
        self._settings = self._load_yaml("settings.yaml")
        self._agents = self._load_yaml("agents.yaml")
        self._tasks = self._load_yaml("tasks.yaml")

        logger.info(f"Loaded settings: {list(self._settings.keys())}")
        logger.info(f"Loaded agents: {list(self._agents.keys())}")
        logger.info(f"Loaded tasks: {list(self._tasks.keys())}")

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a single YAML file."""
        filepath = CONFIG_DIR / filename

        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}")
            return {}

        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                logger.error(f"Error parsing {filename}: {e}")
                return {}

    def reload(self) -> None:
        """Reload all configuration files (useful for hot-reload during development)."""
        self._load_all_configs()
        logger.info("Configuration reloaded")

    @property
    def settings(self) -> Dict[str, Any]:
        """Get the settings configuration."""
        return self._settings

    @property
    def agents(self) -> Dict[str, Any]:
        """Get the agents configuration."""
        return self._agents

    @property
    def tasks(self) -> Dict[str, Any]:
        """Get the tasks configuration."""
        return self._tasks

    # ========================================
    # Convenience Properties
    # ========================================

    @property
    def hospital_name(self) -> str:
        """Get the hospital name."""
        return self._settings.get("hospital", {}).get("name", "Hospital")

    @property
    def agent_name(self) -> str:
        """Get the AI agent name."""
        return self._settings.get("ai_agent", {}).get("name", "Assistant")

    @property
    def facilities(self) -> list:
        """Get the list of facilities."""
        return self._settings.get("hospital", {}).get("facilities", [])

    @property
    def facility_list(self) -> str:
        """Get facilities as a formatted string."""
        return " या ".join(self.facilities)

    @property
    def stt_config(self) -> Dict[str, Any]:
        """Get STT configuration."""
        return self._settings.get("stt", {})

    @property
    def tts_config(self) -> Dict[str, Any]:
        """Get TTS configuration."""
        return self._settings.get("tts", {})

    @property
    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self._settings.get("llm", {})

    @property
    def timing_config(self) -> Dict[str, Any]:
        """Get timing configuration."""
        return self._settings.get("timing", {})

    @property
    def emergency_keywords(self) -> Dict[str, list]:
        """Get emergency keywords."""
        return self._settings.get("emergency", {}).get("keywords", {})

    # ========================================
    # Variable Substitution
    # ========================================

    def _get_base_variables(self) -> Dict[str, str]:
        """Get base variables for substitution."""
        return {
            "hospital_name": self.hospital_name,
            "agent_name": self.agent_name,
            "facility_list": self.facility_list,
        }

    def substitute_variables(self, text: str, **kwargs) -> str:
        """
        Substitute ${variable_name} placeholders in text.

        Base variables (always available):
        - ${hospital_name}
        - ${agent_name}
        - ${facility_list}

        Additional variables can be passed via kwargs:
        - ${memory_context}
        - ${existing_symptoms}
        - ${slots_text}
        - ${booking_summary}
        """
        if not text:
            return text

        # Combine base variables with custom variables
        variables = self._get_base_variables()
        variables.update(kwargs)

        # Replace ${variable_name} patterns
        def replace_var(match):
            var_name = match.group(1)
            return str(variables.get(var_name, match.group(0)))

        return re.sub(r'\$\{(\w+)\}', replace_var, text)

    # ========================================
    # Agent Prompts
    # ========================================

    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """Get full configuration for an agent."""
        return self._agents.get(agent_id, {})

    def get_agent_prompt(self, agent_id: str, **kwargs) -> str:
        """
        Get the instructions/prompt for an agent with variable substitution.

        Args:
            agent_id: The agent identifier (e.g., "orchestrator", "appointment_booking")
            **kwargs: Additional variables for substitution

        Returns:
            The processed instructions string
        """
        agent_config = self.get_agent_config(agent_id)
        instructions = agent_config.get("instructions", "")
        return self.substitute_variables(instructions, **kwargs)

    def get_agent_name(self, agent_id: str) -> str:
        """Get the display name for an agent."""
        agent_config = self.get_agent_config(agent_id)
        return agent_config.get("name", agent_id)

    # ========================================
    # Task Prompts
    # ========================================

    def get_task_config(self, task_id: str) -> Dict[str, Any]:
        """Get full configuration for a task."""
        return self._tasks.get(task_id, {})

    def get_task_prompt(self, task_id: str, **kwargs) -> str:
        """
        Get the instructions/prompt for a task with variable substitution.

        Args:
            task_id: The task identifier (e.g., "data_collection", "doctor_search")
            **kwargs: Additional variables for substitution

        Returns:
            The processed instructions string
        """
        task_config = self.get_task_config(task_id)
        instructions = task_config.get("instructions", "")
        return self.substitute_variables(instructions, **kwargs)

    def get_task_name(self, task_id: str) -> str:
        """Get the display name for a task."""
        task_config = self.get_task_config(task_id)
        return task_config.get("name", task_id)

    def get_task_examples(self, task_id: str) -> Dict[str, Any]:
        """Get conversation examples for a task."""
        task_config = self.get_task_config(task_id)
        return task_config.get("examples", {})


# ========================================
# Global Config Instance
# ========================================

# Singleton instance - import this in other modules
config = ConfigLoader()


# ========================================
# Utility Functions
# ========================================

def get_config() -> ConfigLoader:
    """Get the global config instance."""
    return config


def reload_config() -> None:
    """Reload all configuration files."""
    config.reload()


# For debugging
if __name__ == "__main__":
    # Test the config loader
    logging.basicConfig(level=logging.INFO)

    print("\n=== Settings ===")
    print(f"Hospital: {config.hospital_name}")
    print(f"Agent: {config.agent_name}")
    print(f"Facilities: {config.facilities}")
    print(f"STT: {config.stt_config}")
    print(f"TTS: {config.tts_config}")
    print(f"LLM: {config.llm_config}")

    print("\n=== Agent Prompts ===")
    prompt = config.get_agent_prompt("orchestrator")
    print(f"Orchestrator prompt (first 200 chars):\n{prompt[:200]}...")

    print("\n=== Task Prompts ===")
    task_prompt = config.get_task_prompt(
        "data_collection",
        memory_context="Patient: None, Age: None"
    )
    print(f"Data Collection prompt (first 200 chars):\n{task_prompt[:200]}...")
