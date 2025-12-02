#!/usr/bin/env python3
"""
Test Gemini API conversation with clipboard interaction
Press Enter to read clipboard and send to AI
Type 'quit' to exit
"""

import subprocess
import sys
import os
from google import genai
from google.genai import types


def get_clipboard():
    """Get current clipboard content using wl-paste"""
    try:
        result = subprocess.run(
            ["wl-paste"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error reading clipboard: {e}", file=sys.stderr)
        return None


def set_clipboard(text):
    """Set clipboard content using wl-copy"""
    try:
        subprocess.run(["wl-copy"], input=text, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error setting clipboard: {e}", file=sys.stderr)
        return False


def get_api_key():
    """Get API key - HARDCODED FOR TESTING ONLY"""
    # TODO: In production, read from ~/.config/clipboard-ai/config.json
    api_key = "YOUR_API_KEY_HERE"  # <-- PASTE YOUR API KEY HERE

    if api_key == "YOUR_API_KEY_HERE":
        print("⚠️  Please edit tests/ai_test.py and paste your API key!")
        return None

    return api_key


def main():
    print("=== Gemini Clipboard Chat Test ===\n")

    # Get API key
    api_key = get_api_key()
    if not api_key:
        print("No API key provided. Exiting.")
        return 1

    # Initialize Gemini client
    print("Initializing Gemini client...")
    try:
        client = genai.Client(api_key=api_key)

        # Create chat with thinking disabled for speed
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                temperature=0.7, thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        print("✓ Connected to Gemini API\n")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return 1

    print("Instructions:")
    print("1. Copy text to clipboard")
    print("2. Press Enter to send it to AI")
    print("3. AI response will be copied to clipboard")
    print("4. Type 'quit' and press Enter to exit\n")

    message_count = 0

    while True:
        # Wait for user
        user_input = (
            input("Press Enter to read clipboard (or type 'quit'): ").strip().lower()
        )

        if user_input == "quit":
            print("\nGoodbye!")
            break

        # Read clipboard
        clipboard_content = get_clipboard()
        if not clipboard_content:
            print("✗ Clipboard is empty or couldn't be read\n")
            continue

        print(f"\n📋 Read from clipboard ({len(clipboard_content)} chars):")
        print(
            f"---\n{clipboard_content[:200]}{'...' if len(clipboard_content) > 200 else ''}\n---"
        )

        # Send to AI
        print("🤖 Sending to Gemini...")
        try:
            response = chat.send_message(clipboard_content)
            response_text = response.text

            message_count += 1
            print(f"✓ Response received ({len(response_text)} chars)")
            print(f"Messages in conversation: {message_count * 2}\n")

            # Show preview
            print(
                f"AI Response preview:\n---\n{response_text[:300]}{'...' if len(response_text) > 300 else ''}\n---\n"
            )

            # Copy to clipboard
            if set_clipboard(response_text):
                print("✓ Response copied to clipboard!\n")
            else:
                print("✗ Failed to copy response to clipboard\n")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"✗ {error_msg}\n")
            set_clipboard(error_msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
