#!/usr/bin/env python3
"""
Simple test to verify clipboard operations work on Wayland
"""

import subprocess
import sys


def get_clipboard():
    """Get current clipboard content using wl-paste"""
    try:
        result = subprocess.run(
            ["wl-paste"], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error reading clipboard: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(
            "Error: wl-paste not found. Make sure wl-clipboard is installed.",
            file=sys.stderr,
        )
        return None


def set_clipboard(text):
    """Set clipboard content using wl-copy"""
    try:
        subprocess.run(["wl-copy"], input=text, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting clipboard: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(
            "Error: wl-copy not found. Make sure wl-clipboard is installed.",
            file=sys.stderr,
        )
        return False


def main():
    print("=== Clipboard Test ===\n")

    # Read current clipboard
    print("Reading clipboard...")
    content = get_clipboard()

    if content is None:
        print("Failed to read clipboard!")
        return 1

    print(f"Current clipboard content:\n---\n{content}\n---\n")

    # Write test message
    print("Writing 'Success!' to clipboard...")
    if set_clipboard("Success!"):
        print("✓ Clipboard updated successfully!")
        print("\nYou can now paste to verify it worked.")
        return 0
    else:
        print("✗ Failed to update clipboard!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
