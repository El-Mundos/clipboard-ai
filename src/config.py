#!/usr/bin/env python3
"""
Configuration management for clipboard-ai
Handles config files, directory structure, and prompt loading
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Any


class Config:
    """Manages clipboard-ai configuration"""

    # Default paths
    CONFIG_DIR = Path.home() / ".config" / "clipboard-ai"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    PROMPTS_DIR = CONFIG_DIR / "prompts"
    STATE_DIR = CONFIG_DIR / "state"
    HISTORY_DIR = STATE_DIR / "history"
    CURRENT_STATE = STATE_DIR / "current.json"
    DEBUG_LOG = CONFIG_DIR / "debug.log"

    # Default configuration
    DEFAULT_CONFIG = {
        "api_key": "",
        "default_prompt": "default",
        "default_model": "gemini-2.5-flash",
        "conversation_timeout_hours": 12,
        "thinking_enabled": False,
        "debug": False,
        "max_retries": 3,
        "retry_delay_seconds": 2,
    }

    # Default prompt
    DEFAULT_PROMPT = {
        "name": "default",
        "first_message": """You are an AI assistant running through clipboard-ai, a clipboard-based interface on Linux. Here's how you work:

- The user copies text to their clipboard and presses a keybind
- You receive that text and respond
- Your response is automatically copied back to their clipboard
- They can paste your response anywhere
- Conversations continue until 12 hours of inactivity

Important guidelines:
- Be concise and direct - your responses go straight to the clipboard
- Format your responses to be immediately useful when pasted
- Use markdown sparingly (only when it adds clarity)
- If the user's input is unclear, ask for clarification
- Remember context from previous messages in this conversation
- You cannot see files, images, or anything except the text they copy

Respond with ONLY: 'Ready. Paste your query.'""",
        "model": "gemini-2.5-flash",
        "temperature": 0.7,
        "thinking_enabled": False,
    }

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self._ensure_structure()
        self.load()

    def _ensure_structure(self):
        """Create config directory structure if it doesn't exist"""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.HISTORY_DIR.mkdir(parents=True, exist_ok=True)

        # Create default prompt if it doesn't exist
        default_prompt_file = self.PROMPTS_DIR / "default.json"
        if not default_prompt_file.exists():
            self._save_json(default_prompt_file, self.DEFAULT_PROMPT)

    def load(self) -> Dict[str, Any]:
        """Load configuration from file, create if doesn't exist"""
        if not self.CONFIG_FILE.exists():
            # First run - create default config
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()
            return self.config

        try:
            with open(self.CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                # Merge with defaults to handle new config keys
                self.config = {**self.DEFAULT_CONFIG, **loaded}
                return self.config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            # Fall back to defaults
            self.config = self.DEFAULT_CONFIG.copy()
            return self.config

    def save(self):
        """Save current configuration to file"""
        self._save_json(self.CONFIG_FILE, self.config)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value and save"""
        self.config[key] = value
        self.save()

    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.config.get("api_key"))

    def load_prompt(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        """Load a prompt configuration by name"""
        prompt_file = self.PROMPTS_DIR / f"{prompt_name}.json"

        if not prompt_file.exists():
            return None

        try:
            with open(prompt_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading prompt '{prompt_name}': {e}")
            return None

    def list_prompts(self) -> list[str]:
        """List all available prompt names"""
        if not self.PROMPTS_DIR.exists():
            return []

        prompts = []
        for file in self.PROMPTS_DIR.glob("*.json"):
            prompts.append(file.stem)

        return sorted(prompts)

    def get_all_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Load all prompts with their configurations"""
        prompts = {}
        for prompt_name in self.list_prompts():
            prompt_config = self.load_prompt(prompt_name)
            if prompt_config:
                prompts[prompt_name] = prompt_config
        return prompts

    def validate_prompt(self, prompt_config: Dict[str, Any]) -> list[str]:
        """Validate prompt configuration, return list of errors"""
        errors = []

        # Required fields
        if "name" not in prompt_config:
            errors.append("Missing required field: name")
        if "first_message" not in prompt_config:
            errors.append("Missing required field: first_message")

        # Validate temperature
        if "temperature" in prompt_config:
            temp = prompt_config["temperature"]
            if not isinstance(temp, (int, float)) or not 0.0 <= temp <= 2.0:
                errors.append(f"Temperature must be 0.0-2.0, got {temp}")

        # Validate model
        if "model" in prompt_config:
            valid_models = [
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.5-pro",
                "gemini-3-pro-preview",
            ]
            if prompt_config["model"] not in valid_models:
                errors.append(f"Invalid model: {prompt_config['model']}")

        return errors

    @staticmethod
    def _save_json(filepath: Path, data: Dict):
        """Save JSON data to file"""
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving to {filepath}: {e}")

    def __repr__(self):
        return f"Config(api_key={'set' if self.is_configured() else 'not set'}, prompts={len(self.list_prompts())})"


# Convenience function for quick access
def load_config() -> Config:
    """Load configuration (convenience function)"""
    return Config()


if __name__ == "__main__":
    # Test the config system
    print("Testing config system...")
    config = Config()
    print(f"Config loaded: {config}")
    print(f"Config dir: {Config.CONFIG_DIR}")
    print(f"API key configured: {config.is_configured()}")
    print(f"Available prompts: {config.list_prompts()}")
