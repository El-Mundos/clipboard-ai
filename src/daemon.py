#!/usr/bin/env python3
"""
Daemon for clipboard-ai
Runs in background, maintains chat state, handles socket communication
"""

import json
import os
import signal
import socket
import sys
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from google import genai
from google.genai import types, errors

from config import Config
from state import StateManager, ConversationState, Message


class ClipboardAIDaemon:
    """Main daemon that manages AI chat and socket communication"""

    def __init__(self):
        self.config = Config()
        self.state_manager = StateManager(self.config.CONFIG_DIR)

        # Socket setup
        self.socket_path = f"/tmp/clipboard-ai-{os.getuid()}.sock"
        self.socket = None
        self.running = False

        # AI client and chat
        self.client: Optional[genai.Client] = None
        self.chat = None
        self.current_state: Optional[ConversationState] = None

        # Timeout tracking
        self.last_activity = datetime.now()
        self.timeout_hours = self.config.get("conversation_timeout_hours", 12)

        # Debug mode
        self.debug = self.config.get("debug", False)

    def log(self, message: str, level: str = "INFO"):
        """Log message if debug mode is enabled"""
        if self.debug:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {level}: {message}\n"

            try:
                with open(self.config.DEBUG_LOG, "a") as f:
                    f.write(log_entry)
            except IOError:
                pass

            # Also print to console in debug mode
            print(log_entry.strip())

    def initialize_api(self) -> bool:
        """Initialize Gemini API client"""
        api_key = self.config.get("api_key")

        if not api_key:
            self.log("No API key configured", "ERROR")
            return False

        try:
            self.client = genai.Client(api_key=api_key)
            self.log("Gemini API client initialized")
            return True
        except Exception as e:
            self.log(f"Failed to initialize API client: {e}", "ERROR")
            return False

    def create_chat(self, model: str, temperature: float, thinking_enabled: bool):
        """Create a new chat instance"""
        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0 if not thinking_enabled else None
                ),
            )

            self.chat = self.client.chats.create(model=model, config=config)
            self.log(
                f"Created chat with model={model}, temp={temperature}, thinking={thinking_enabled}"
            )
            return True
        except Exception as e:
            self.log(f"Failed to create chat: {e}", "ERROR")
            return False

    def start_new_conversation(self, prompt_name: str) -> str:
        """Start a new conversation with given prompt"""
        self.log(f"Starting new conversation with prompt: {prompt_name}")

        # Load prompt configuration
        prompt_config = self.config.load_prompt(prompt_name)
        if not prompt_config:
            self.log(f"Prompt '{prompt_name}' not found, using default", "WARN")
            prompt_name = "default"
            prompt_config = self.config.load_prompt("default")

        # Extract configuration
        model = prompt_config.get("model", self.config.get("default_model"))
        temperature = prompt_config.get("temperature", 0.7)
        thinking_enabled = prompt_config.get("thinking_enabled", False)
        first_message = prompt_config.get("first_message", "")

        # Create new chat
        if not self.create_chat(model, temperature, thinking_enabled):
            return "Error: Failed to create chat"

        # Create new state
        self.current_state = self.state_manager.create_new(prompt_name, model)

        # Send first message to initialize
        try:
            self.log(f"Sending first message ({len(first_message)} chars)")
            response = self.chat.send_message(first_message)
            response_text = response.text

            # Store in conversation history
            self.current_state.add_message("user", first_message)
            self.current_state.add_message("model", response_text)

            # Save state
            self.state_manager.save_current(self.current_state)
            self.last_activity = datetime.now()

            self.log(f"Conversation initialized, response: {len(response_text)} chars")
            return response_text

        except errors.ResourceExhausted:
            return "Error: Rate limit exceeded. Try again in a moment."
        except errors.InvalidArgument as e:
            return f"Error: Invalid request - {str(e)}"
        except Exception as e:
            self.log(f"Error in start_new_conversation: {e}", "ERROR")
            return f"Error: {str(e)}"

    def send_message(self, content: str) -> str:
        """Send message to current conversation"""
        if not self.chat or not self.current_state:
            return "Error: No active conversation"

        self.log(f"Sending message ({len(content)} chars)")

        # Retry logic with exponential backoff
        max_retries = self.config.get("max_retries", 3)
        retry_delay = self.config.get("retry_delay_seconds", 2)

        for attempt in range(max_retries):
            try:
                response = self.chat.send_message(content)
                response_text = response.text

                # Store in conversation history
                self.current_state.add_message("user", content)
                self.current_state.add_message("model", response_text)

                # Save state
                self.state_manager.save_current(self.current_state)
                self.last_activity = datetime.now()

                self.log(
                    f"Message sent successfully, response: {len(response_text)} chars"
                )
                return response_text

            except errors.ResourceExhausted:
                if attempt < max_retries - 1:
                    delay = retry_delay * (2**attempt)
                    self.log(
                        f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{max_retries})",
                        "WARN",
                    )
                    time.sleep(delay)
                else:
                    return "Error: Rate limit exceeded after retries"

            except errors.InternalError:
                if attempt < max_retries - 1:
                    self.log(
                        f"Server error, retrying (attempt {attempt + 1}/{max_retries})",
                        "WARN",
                    )
                    time.sleep(retry_delay)
                else:
                    return "Error: Server error after retries"

            except errors.InvalidArgument as e:
                return f"Error: Invalid request - {str(e)}"

            except Exception as e:
                self.log(f"Error sending message: {e}", "ERROR")
                return f"Error: {str(e)}"

        return "Error: Max retries exceeded"

    def check_and_resume_conversation(self) -> bool:
        """Check if there's an active conversation and resume it"""
        self.log("Checking for existing conversation")

        state = self.state_manager.load_current()
        if not state:
            self.log("No existing conversation found")
            return False

        # Check if expired
        if state.is_expired(self.timeout_hours):
            self.log(
                f"Conversation expired (older than {self.timeout_hours}h), archiving"
            )
            self.state_manager.archive_current()
            return False

        self.log(
            f"Resuming conversation: {state.prompt_name}, {state.get_message_count()} messages"
        )

        # Resume the conversation
        prompt_config = self.config.load_prompt(state.prompt_name)
        if not prompt_config:
            prompt_config = self.config.load_prompt("default")

        model = state.model
        temperature = prompt_config.get("temperature", 0.7)
        thinking_enabled = prompt_config.get("thinking_enabled", False)

        # Create chat
        if not self.create_chat(model, temperature, thinking_enabled):
            return False

        # Rebuild conversation history by replaying messages
        self.log(f"Replaying {len(state.messages)} messages to rebuild context")
        for msg in state.messages:
            try:
                if msg.role == "user":
                    # Send message but don't store response (it's already in history)
                    self.chat.send_message(msg.content)
            except Exception as e:
                self.log(f"Error replaying message: {e}", "ERROR")
                return False

        self.current_state = state
        self.last_activity = datetime.now()
        self.log("Conversation resumed successfully")
        return True

    def handle_client(self, client_socket):
        """Handle incoming client request"""
        try:
            # Receive data
            data = client_socket.recv(4096).decode("utf-8")
            if not data:
                return

            request = json.loads(data)
            action = request.get("action")

            self.log(f"Received action: {action}")

            response = {"status": "error", "message": "Unknown action"}

            if action == "send":
                content = request.get("content", "")

                # Check if we need to start a new conversation
                if not self.current_state:
                    # Check if content matches a prompt name
                    content_clean = content.strip().lower()
                    available_prompts = [p.lower() for p in self.config.list_prompts()]

                    if content_clean in available_prompts:
                        # Start new conversation with this prompt
                        result = self.start_new_conversation(content_clean)
                    else:
                        # Start with default prompt, then send this as first message
                        result = self.start_new_conversation("default")
                        # After initialization, send the actual content
                        if not result.startswith("Error:"):
                            result = self.send_message(content)
                else:
                    # Continue existing conversation
                    result = self.send_message(content)

                response = {"status": "success", "message": result}

            elif action == "new":
                # Force new conversation
                self.log("Forcing new conversation")
                if self.current_state:
                    self.state_manager.archive_current()
                self.current_state = None
                self.chat = None
                response = {
                    "status": "success",
                    "message": "Conversation reset. Next message will start fresh.",
                }

            elif action == "status":
                status = self.state_manager.get_status()
                if self.current_state:
                    status["timeout_hours"] = self.timeout_hours
                response = {"status": "success", "data": status}

            elif action == "ping":
                response = {"status": "success", "message": "pong"}

            # Send response
            client_socket.sendall(json.dumps(response).encode("utf-8"))

        except json.JSONDecodeError:
            error_response = {"status": "error", "message": "Invalid JSON"}
            client_socket.sendall(json.dumps(error_response).encode("utf-8"))
        except Exception as e:
            self.log(f"Error handling client: {e}", "ERROR")
            error_response = {"status": "error", "message": str(e)}
            client_socket.sendall(json.dumps(error_response).encode("utf-8"))
        finally:
            client_socket.close()

    def check_timeout(self):
        """Check if daemon should shut down due to inactivity"""
        if self.current_state:
            idle_time = datetime.now() - self.last_activity
            if idle_time > timedelta(hours=self.timeout_hours):
                self.log(f"Timeout reached ({self.timeout_hours}h), shutting down")
                self.state_manager.archive_current()
                self.shutdown()

    def timeout_checker_thread(self):
        """Background thread to check for timeouts"""
        while self.running:
            time.sleep(60)  # Check every minute
            self.check_timeout()

    def setup_socket(self) -> bool:
        """Set up Unix domain socket (supports systemd socket activation)"""
        # Check for systemd socket activation
        sd_listen_fds = os.environ.get("LISTEN_FDS")
        if sd_listen_fds and int(sd_listen_fds) > 0:
            # Use socket passed by systemd
            self.log("Using systemd socket activation")
            self.socket = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
            return True

        # Manual socket creation (for non-systemd usage)
        # Remove existing socket if it exists
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.bind(self.socket_path)
            self.socket.listen(5)
            self.log(f"Socket listening at {self.socket_path}")
            return True
        except Exception as e:
            self.log(f"Failed to set up socket: {e}", "ERROR")
            return False

    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown"""
        self.log("Shutting down daemon")
        self.running = False

        if self.socket:
            self.socket.close()

        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

        sys.exit(0)

    def run(self):
        """Main daemon loop"""
        self.log("Starting clipboard-ai daemon")

        # Initialize API
        if not self.initialize_api():
            print("Error: Failed to initialize API. Check your API key.")
            return 1

        # Check for existing conversation
        self.check_and_resume_conversation()

        # Set up socket
        if not self.setup_socket():
            return 1

        # Set up signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        # Start timeout checker thread
        self.running = True
        timeout_thread = threading.Thread(
            target=self.timeout_checker_thread, daemon=True
        )
        timeout_thread.start()

        self.log("Daemon ready, waiting for connections")

        # Main loop
        try:
            while self.running:
                client_socket, _ = self.socket.accept()
                self.handle_client(client_socket)
        except KeyboardInterrupt:
            self.shutdown()

        return 0


def main():
    daemon = ClipboardAIDaemon()
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
