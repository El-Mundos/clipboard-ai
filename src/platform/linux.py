"""
Linux platform implementation for clipboard-ai
Uses wl-clipboard for clipboard access and Unix domain sockets for IPC
"""
import os
import signal
import socket
import subprocess
from pathlib import Path
from typing import Optional, Callable, Union, Tuple

from .base import PlatformInterface


class LinuxPlatform(PlatformInterface):
    """Linux/Wayland implementation using wl-clipboard and Unix sockets"""

    def __init__(self):
        self._socket_path = f"/tmp/clipboard-ai-{os.getuid()}.sock"

    @property
    def name(self) -> str:
        return "Linux"

    # --- Clipboard Operations ---

    def get_clipboard(self) -> str:
        """Read clipboard using wl-paste (Wayland)"""
        try:
            result = subprocess.run(
                ["wl-paste"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
        except subprocess.TimeoutExpired:
            return ""
        except FileNotFoundError:
            # wl-paste not installed
            return ""

    def set_clipboard(self, text: str) -> bool:
        """Write to clipboard using wl-copy (Wayland)"""
        try:
            subprocess.run(
                ["wl-copy"],
                input=text,
                text=True,
                check=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    # --- IPC/Socket Operations ---

    def get_socket_address(self) -> Union[str, Tuple[str, int]]:
        """Return Unix socket path"""
        return self._socket_path

    def create_server_socket(self) -> socket.socket:
        """Create Unix domain socket server"""
        # Remove existing socket if it exists
        if os.path.exists(self._socket_path):
            try:
                os.unlink(self._socket_path)
            except OSError:
                pass

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self._socket_path)
        sock.listen(5)
        return sock

    def create_client_socket(self) -> socket.socket:
        """Create Unix domain socket client"""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(self._socket_path)
        return sock

    def cleanup_socket(self) -> None:
        """Remove Unix socket file"""
        if os.path.exists(self._socket_path):
            try:
                os.unlink(self._socket_path)
            except OSError:
                pass

    def is_daemon_running(self) -> bool:
        """Check if daemon is running by checking if socket file exists"""
        return os.path.exists(self._socket_path)

    # --- Configuration Paths ---

    def get_config_dir(self) -> Path:
        """Return XDG config directory (~/.config/clipboard-ai/)"""
        return Path.home() / ".config" / "clipboard-ai"

    # --- Process Management ---

    def start_daemon_process(self, daemon_command: list) -> bool:
        """Start daemon as detached background process (Unix style)"""
        try:
            subprocess.Popen(
                daemon_command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
        except Exception:
            return False

    # --- Signal Handling ---

    def setup_signal_handlers(self, shutdown_callback: Callable) -> None:
        """Set up Unix signal handlers (SIGINT, SIGTERM)"""
        signal.signal(signal.SIGINT, shutdown_callback)
        signal.signal(signal.SIGTERM, shutdown_callback)

    # --- Systemd Socket Activation ---

    def check_systemd_socket_activation(self) -> Optional[socket.socket]:
        """Check for systemd socket activation via LISTEN_FDS"""
        sd_listen_fds = os.environ.get("LISTEN_FDS")
        if sd_listen_fds and int(sd_listen_fds) > 0:
            # File descriptor 3 is the first socket passed by systemd
            return socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
        return None
