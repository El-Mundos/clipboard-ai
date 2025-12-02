#!/usr/bin/env python3
"""
State management for clipboard-ai
Handles conversation state, message history, and archiving
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class Message:
    """Represents a single message in the conversation"""

    role: str  # "user" or "model"
    content: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Message":
        return cls(**data)


@dataclass
class ConversationState:
    """Represents the current conversation state"""

    active: bool
    prompt_name: str
    model: str
    created_at: str
    last_activity: str
    messages: List[Message]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active": self.active,
            "prompt_name": self.prompt_name,
            "model": self.model,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "messages": [msg.to_dict() for msg in self.messages],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        return cls(
            active=data.get("active", True),
            prompt_name=data.get("prompt_name", "default"),
            model=data.get("model", "gemini-2.5-flash"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_activity=data.get("last_activity", datetime.now().isoformat()),
            messages=messages,
        )

    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append(Message(role=role, content=content))
        self.last_activity = datetime.now().isoformat()

    def is_expired(self, timeout_hours: int) -> bool:
        """Check if conversation has expired based on timeout"""
        last_activity = datetime.fromisoformat(self.last_activity)
        timeout = timedelta(hours=timeout_hours)
        return datetime.now() - last_activity > timeout

    def get_message_count(self) -> int:
        """Get total number of messages in conversation"""
        return len(self.messages)


class StateManager:
    """Manages conversation state persistence"""

    def __init__(self, config_dir: Path):
        self.state_dir = config_dir / "state"
        self.history_dir = self.state_dir / "history"
        self.current_state_file = self.state_dir / "current.json"

        # Ensure directories exist
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def load_current(self) -> Optional[ConversationState]:
        """Load current conversation state if it exists"""
        if not self.current_state_file.exists():
            return None

        try:
            with open(self.current_state_file, "r") as f:
                data = json.load(f)
                return ConversationState.from_dict(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading state: {e}")
            return None

    def save_current(self, state: ConversationState):
        """Save current conversation state"""
        try:
            with open(self.current_state_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
        except IOError as e:
            print(f"Error saving state: {e}")

    def create_new(self, prompt_name: str, model: str) -> ConversationState:
        """Create a new conversation state"""
        now = datetime.now().isoformat()
        return ConversationState(
            active=True,
            prompt_name=prompt_name,
            model=model,
            created_at=now,
            last_activity=now,
            messages=[],
        )

    def archive_current(self) -> bool:
        """Archive current conversation to history"""
        if not self.current_state_file.exists():
            return False

        try:
            # Load current state
            state = self.load_current()
            if not state:
                return False

            # Create archive filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            archive_file = self.history_dir / f"{timestamp}.json"

            # Mark as inactive
            state.active = False

            # Save to history
            with open(archive_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)

            # Remove current state file
            self.current_state_file.unlink()

            return True

        except (IOError, OSError) as e:
            print(f"Error archiving state: {e}")
            return False

    def delete_current(self) -> bool:
        """Delete current conversation without archiving"""
        if not self.current_state_file.exists():
            return False

        try:
            self.current_state_file.unlink()
            return True
        except OSError as e:
            print(f"Error deleting state: {e}")
            return False

    def list_history(self) -> List[Path]:
        """List all archived conversations"""
        if not self.history_dir.exists():
            return []

        return sorted(self.history_dir.glob("*.json"), reverse=True)

    def load_history(self, filename: str) -> Optional[ConversationState]:
        """Load a specific archived conversation"""
        history_file = self.history_dir / filename

        if not history_file.exists():
            return None

        try:
            with open(history_file, "r") as f:
                data = json.load(f)
                return ConversationState.from_dict(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading history: {e}")
            return None

    def clear_all(self) -> bool:
        """Clear all state (nuclear option)"""
        try:
            # Delete current state
            if self.current_state_file.exists():
                self.current_state_file.unlink()

            # Delete all history
            for history_file in self.list_history():
                history_file.unlink()

            return True
        except OSError as e:
            print(f"Error clearing state: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current status information"""
        state = self.load_current()

        if not state:
            return {"active": False, "message": "No active conversation"}

        created = datetime.fromisoformat(state.created_at)
        last_activity = datetime.fromisoformat(state.last_activity)

        return {
            "active": True,
            "prompt_name": state.prompt_name,
            "model": state.model,
            "created_at": created.strftime("%Y-%m-%d %H:%M"),
            "last_activity": last_activity.strftime("%Y-%m-%d %H:%M"),
            "message_count": state.get_message_count(),
            "history_count": len(self.list_history()),
        }


if __name__ == "__main__":
    # Test state management
    from config import Config

    print("Testing state management...")
    config = Config()
    state_manager = StateManager(config.CONFIG_DIR)

    # Test creating new state
    print("\n1. Creating new conversation...")
    state = state_manager.create_new("default", "gemini-2.5-flash")
    state.add_message("user", "Hello!")
    state.add_message("model", "Hi there!")
    state_manager.save_current(state)
    print(f"Created: {state.get_message_count()} messages")

    # Test loading state
    print("\n2. Loading conversation...")
    loaded_state = state_manager.load_current()
    if loaded_state:
        print(f"Loaded: {loaded_state.get_message_count()} messages")
        print(f"Last activity: {loaded_state.last_activity}")

    # Test status
    print("\n3. Getting status...")
    status = state_manager.get_status()
    print(f"Status: {status}")

    # Test archiving
    print("\n4. Archiving conversation...")
    if state_manager.archive_current():
        print("Archived successfully")
        print(f"History files: {len(state_manager.list_history())}")

    print("\n✓ State management test complete!")
