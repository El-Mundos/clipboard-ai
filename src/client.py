#!/usr/bin/env python3
"""
Client for clipboard-ai
Communicates with daemon via Unix socket
Handles clipboard read/write
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from config import Config


class ClipboardAIClient:
    """Client that communicates with the daemon"""

    def __init__(self):
        self.config = Config()
        self.socket_path = f"/tmp/clipboard-ai-{os.getuid()}.sock"

    def get_clipboard(self) -> str:
        """Get clipboard content using wl-paste"""
        try:
            result = subprocess.run(
                ["wl-paste"], capture_output=True, text=True, check=True, timeout=5
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            self.set_clipboard(
                "Error: wl-paste not found. Install wl-clipboard package."
            )
            return ""

    def set_clipboard(self, text: str) -> bool:
        """Set clipboard content using wl-copy"""
        try:
            subprocess.run(["wl-copy"], input=text, text=True, check=True, timeout=5)
            return True
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            return False

    def is_daemon_running(self) -> bool:
        """Check if daemon is running"""
        return os.path.exists(self.socket_path)

    def start_daemon(self) -> bool:
        """Start the daemon if not running"""
        if self.is_daemon_running():
            return True

        # Start daemon in background
        daemon_script = Path(__file__).parent / "daemon.py"

        try:
            subprocess.Popen(
                [sys.executable, str(daemon_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            # Wait for daemon to start (max 5 seconds)
            for _ in range(50):
                if self.is_daemon_running():
                    return True
                time.sleep(0.1)

            return False
        except Exception as e:
            print(f"Failed to start daemon: {e}", file=sys.stderr)
            return False

    def send_to_daemon(self, action: str, content: str = "") -> dict:
        """Send request to daemon and get response"""
        try:
            # Connect to daemon
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(30)  # 30 second timeout
            sock.connect(self.socket_path)

            # Send request
            request = {"action": action, "content": content}
            sock.sendall(json.dumps(request).encode("utf-8"))

            # Receive response
            response_data = sock.recv(8192).decode("utf-8")
            response = json.loads(response_data)

            sock.close()
            return response

        except socket.timeout:
            return {"status": "error", "message": "Request timed out"}
        except ConnectionRefusedError:
            return {"status": "error", "message": "Daemon not responding"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def handle_send(self) -> int:
        """Handle normal send action (read clipboard, send to AI, write response)"""
        # Check API key
        if not self.config.is_configured():
            self.set_clipboard(
                "Error: API key not configured. Please run: clipboard-ai --setup"
            )
            return 1

        # Start daemon if needed
        if not self.start_daemon():
            self.set_clipboard("Error: Failed to start daemon")
            return 1

        # Read clipboard
        content = self.get_clipboard()
        if not content:
            self.set_clipboard("Error: Clipboard is empty")
            return 1

        # Send to daemon
        response = self.send_to_daemon("send", content)

        if response["status"] == "success":
            # Write response to clipboard
            self.set_clipboard(response["message"])
            return 0
        else:
            self.set_clipboard(f"Error: {response['message']}")
            return 1

    def handle_new(self) -> int:
        """Handle --new flag (force new conversation)"""
        if not self.is_daemon_running():
            self.set_clipboard("No active conversation to reset")
            return 0

        response = self.send_to_daemon("new")

        if response["status"] == "success":
            self.set_clipboard(response["message"])
            return 0
        else:
            self.set_clipboard(f"Error: {response['message']}")
            return 1

    def handle_status(self) -> int:
        """Handle --status flag (show conversation info)"""
        if not self.is_daemon_running():
            print("No active daemon running")
            return 0

        response = self.send_to_daemon("status")

        if response["status"] == "success":
            status = response["data"]

            if not status["active"]:
                print(status["message"])
            else:
                print(f"Active conversation:")
                print(f"  Prompt: {status['prompt_name']}")
                print(f"  Model: {status['model']}")
                print(f"  Started: {status['created_at']}")
                print(f"  Last activity: {status['last_activity']}")
                print(f"  Messages: {status['message_count']}")
                if "timeout_hours" in status:
                    print(f"  Timeout: {status['timeout_hours']} hours")
                print(f"\nArchived conversations: {status['history_count']}")

            return 0
        else:
            print(f"Error: {response['message']}")
            return 1

    def handle_list_prompts(self) -> int:
        """Handle --list-prompts flag (show available prompts)"""
        prompts = self.config.get_all_prompts()

        if not prompts:
            print("No prompts configured")
            return 0

        print("Available prompts:")
        for name, prompt_config in prompts.items():
            model = prompt_config.get("model", "unknown")
            temp = prompt_config.get("temperature", 0.7)
            thinking = "On" if prompt_config.get("thinking_enabled", False) else "Off"

            print(f"\n  {name}")
            print(f"    Model: {model} | Temp: {temp} | Thinking: {thinking}")

        # Show current status
        if self.is_daemon_running():
            print()
            response = self.send_to_daemon("status")
            if response["status"] == "success" and response["data"]["active"]:
                status = response["data"]
                print(f"Current conversation: {status['prompt_name']}")
                print(f"  Started: {status['created_at']}")
                print(f"  Messages: {status['message_count']}")

        return 0

    def handle_setup(self) -> int:
        """Handle --setup flag (configure API key)"""
        print("Clipboard AI Setup")
        print("=" * 50)
        print("\nGet your API key from: https://aistudio.google.com/apikey")

        api_key = input("\nEnter your Gemini API key: ").strip()

        if not api_key:
            print("No API key provided. Setup cancelled.")
            return 1

        # Save to config
        self.config.set("api_key", api_key)
        print(f"\n✓ API key saved to {self.config.CONFIG_FILE}")
        print("✓ Configuration complete!")
        print("\nYou can now use clipboard-ai by:")
        print("1. Copy some text")
        print("2. Press your keybind (or run 'clipboard-ai')")
        print("3. Paste the AI response")

        return 0

    def handle_reset(self) -> int:
        """Handle --reset flag (clear all state)"""
        print("⚠️  This will clear ALL conversations and state.")
        confirm = input("Are you sure? (yes/no): ").strip().lower()

        if confirm != "yes":
            print("Reset cancelled.")
            return 0

        from state import StateManager

        state_manager = StateManager(self.config.CONFIG_DIR)

        if state_manager.clear_all():
            print("✓ All state cleared")
            return 0
        else:
            print("✗ Failed to clear state")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="Clipboard AI - AI assistant through clipboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--new", action="store_true", help="Force start new conversation"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current conversation status"
    )
    parser.add_argument(
        "--list-prompts", action="store_true", help="List available prompts"
    )
    parser.add_argument("--setup", action="store_true", help="Configure API key")
    parser.add_argument(
        "--reset", action="store_true", help="Clear all state (dangerous!)"
    )
    parser.add_argument("--debug", action="store_true", help="Run with debug output")

    args = parser.parse_args()

    client = ClipboardAIClient()

    # Enable debug mode if requested
    if args.debug:
        client.config.set("debug", True)

    # Handle different actions
    if args.setup:
        return client.handle_setup()
    elif args.list_prompts:
        return client.handle_list_prompts()
    elif args.status:
        return client.handle_status()
    elif args.reset:
        return client.handle_reset()
    elif args.new:
        return client.handle_new()
    else:
        # Default action: send clipboard content
        return client.handle_send()


if __name__ == "__main__":
    sys.exit(main())
