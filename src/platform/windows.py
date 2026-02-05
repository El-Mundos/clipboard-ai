"""
Windows platform implementation for clipboard-ai
Uses pyperclip for clipboard access and localhost TCP for IPC
"""
import os
import signal
import socket
import subprocess
from pathlib import Path
from typing import Optional, Callable, Union, Tuple

from .base import PlatformInterface


# Windows-specific constants
DAEMON_PORT = 61472
DAEMON_HOST = "127.0.0.1"


class WindowsPlatform(PlatformInterface):
    """Windows implementation using pyperclip and TCP sockets"""

    def __init__(self):
        self._address = (DAEMON_HOST, DAEMON_PORT)

    @property
    def name(self) -> str:
        return "Windows"

    # --- Clipboard Operations ---

    def get_clipboard(self) -> str:
        """Read clipboard using pyperclip"""
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return ""

    def set_clipboard(self, text: str) -> bool:
        """Write to clipboard using pyperclip"""
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except Exception:
            return False

    # --- IPC/Socket Operations ---

    def get_socket_address(self) -> Union[str, Tuple[str, int]]:
        """Return TCP address tuple (host, port)"""
        return self._address

    def create_server_socket(self) -> socket.socket:
        """Create TCP socket server on localhost"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self._address)
        sock.listen(5)
        return sock

    def create_client_socket(self) -> socket.socket:
        """Create TCP socket client connected to daemon"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(self._address)
        return sock

    def cleanup_socket(self) -> None:
        """No cleanup needed for TCP sockets"""
        pass

    def is_daemon_running(self) -> bool:
        """Check if daemon is running by attempting TCP connection"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(self._address)
            sock.close()
            return True
        except (socket.error, socket.timeout):
            return False

    # --- Configuration Paths ---

    def get_config_dir(self) -> Path:
        """Return Windows AppData config directory (%APPDATA%/clipboard-ai/)"""
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "clipboard-ai"
        # Fallback if APPDATA not set
        return Path.home() / "AppData" / "Roaming" / "clipboard-ai"

    # --- Process Management ---

    def start_daemon_process(self, daemon_command: list) -> bool:
        """Start daemon as detached background process (Windows style)"""
        try:
            # Windows-specific flags for detached process
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            CREATE_NO_WINDOW = 0x08000000

            subprocess.Popen(
                daemon_command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
            )
            return True
        except Exception:
            return False

    # --- Signal Handling ---

    def setup_signal_handlers(self, shutdown_callback: Callable) -> None:
        """Set up Windows signal handlers (only SIGINT/Ctrl+C works)"""
        # Windows only supports SIGINT (Ctrl+C), SIGTERM doesn't exist
        signal.signal(signal.SIGINT, shutdown_callback)

    # --- Systemd (not applicable on Windows) ---

    def check_systemd_socket_activation(self) -> Optional[socket.socket]:
        """Systemd is not available on Windows"""
        return None
