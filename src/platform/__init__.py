"""
Platform detection and abstraction factory for clipboard-ai
Provides cross-platform support for clipboard operations, IPC, and configuration
"""
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import PlatformInterface


def get_platform() -> "PlatformInterface":
    """Return the appropriate platform implementation for the current OS"""
    if sys.platform == "win32":
        from .windows import WindowsPlatform
        return WindowsPlatform()
    else:
        from .linux import LinuxPlatform
        return LinuxPlatform()


__all__ = ["get_platform"]
