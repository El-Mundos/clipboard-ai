"""
Abstract base class defining the platform interface for clipboard-ai
All platform implementations must follow this interface
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable, Union, Tuple
import socket


class PlatformInterface(ABC):
    """Interface that all platform implementations must follow"""

    # --- Clipboard Operations ---

    @abstractmethod
    def get_clipboard(self) -> str:
        """Read text from system clipboard

        Returns:
            The clipboard contents as a string, or empty string on error
        """
        pass

    @abstractmethod
    def set_clipboard(self, text: str) -> bool:
        """Write text to system clipboard

        Args:
            text: The text to copy to clipboard

        Returns:
            True if successful, False otherwise
        """
        pass

    # --- IPC/Socket Operations ---

    @abstractmethod
    def get_socket_address(self) -> Union[str, Tuple[str, int]]:
        """Return socket address for daemon communication

        Returns:
            Unix socket path (str) on Linux, or (host, port) tuple on Windows
        """
        pass

    @abstractmethod
    def create_server_socket(self) -> socket.socket:
        """Create and bind a server socket for the daemon

        Returns:
            A bound and listening socket
        """
        pass

    @abstractmethod
    def create_client_socket(self) -> socket.socket:
        """Create a client socket connected to the daemon

        Returns:
            A connected socket ready for communication
        """
        pass

    @abstractmethod
    def cleanup_socket(self) -> None:
        """Clean up socket resources (e.g., unlink Unix socket file)"""
        pass

    @abstractmethod
    def is_daemon_running(self) -> bool:
        """Check if daemon is already running

        Returns:
            True if daemon appears to be running, False otherwise
        """
        pass

    # --- Configuration Paths ---

    @abstractmethod
    def get_config_dir(self) -> Path:
        """Return platform-specific config directory

        Returns:
            Path to the configuration directory
            - Linux: ~/.config/clipboard-ai/
            - Windows: %APPDATA%/clipboard-ai/
        """
        pass

    # --- Process Management ---

    @abstractmethod
    def start_daemon_process(self, daemon_command: list) -> bool:
        """Start daemon as a detached background process

        Args:
            daemon_command: Command list to execute (e.g., [sys.executable, 'daemon.py'])

        Returns:
            True if process was started successfully, False otherwise
        """
        pass

    # --- Signal Handling ---

    @abstractmethod
    def setup_signal_handlers(self, shutdown_callback: Callable) -> None:
        """Set up platform-specific signal handlers for graceful shutdown

        Args:
            shutdown_callback: Function to call on shutdown signal
        """
        pass

    # --- Systemd (Linux-only, no-op on Windows) ---

    def check_systemd_socket_activation(self) -> Optional[socket.socket]:
        """Check for systemd socket activation (Linux only)

        Returns:
            Socket from systemd if activated, None otherwise
        """
        return None

    # --- Platform Information ---

    @property
    @abstractmethod
    def name(self) -> str:
        """Return platform name for logging/display"""
        pass
