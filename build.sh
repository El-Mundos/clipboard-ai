#!/bin/bash
set -e

# Ensure we're on Linux
if [[ "$(uname)" != "Linux" ]]; then
    echo "Error: build.sh is for Linux only. Use build.ps1 on Windows."
    exit 1
fi

echo "==================================="
echo "Building Clipboard AI (Linux)"
echo "==================================="
echo

# Check if PyInstaller is installed
if ! command -v pyinstaller &>/dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Create a single entry point that handles both daemon and client
echo "Creating unified entry point..."
cat >src/clipboard_ai.py <<'EOF'
#!/usr/bin/env python3
"""
Unified entry point for clipboard-ai
Handles both daemon and client mode based on how it's called
"""
import sys
import os

# Determine mode based on argv[0] or first argument
binary_name = os.path.basename(sys.argv[0])

if binary_name == 'clipboard-ai-daemon' or '--daemon' in sys.argv:
    # Run as daemon
    if '--daemon' in sys.argv:
        sys.argv.remove('--daemon')
    from daemon import main
    sys.exit(main())
else:
    # Run as client (default)
    from client import main
    sys.exit(main())
EOF

# Build the binary
echo
echo "Building binary with PyInstaller..."
pyinstaller \
    --onefile \
    --name clipboard-ai-linux-x86_64 \
    --hidden-import=google.genai \
    --hidden-import=google.genai.types \
    --hidden-import=google.genai.errors \
    --exclude-module=pyperclip \
    --add-data "src/config.py:." \
    --add-data "src/state.py:." \
    --add-data "src/daemon.py:." \
    --add-data "src/client.py:." \
    --add-data "src/platform:platform" \
    --clean \
    src/clipboard_ai.py

echo
echo "✓ Binary built successfully!"
echo "  Location: dist/clipboard-ai-linux-x86_64"
echo
echo "Testing binary..."
./dist/clipboard-ai-linux-x86_64 --help

echo
echo "==================================="
echo "Build Complete!"
echo "==================================="
echo
echo "The binary is at: dist/clipboard-ai-linux-x86_64"
echo "File size: $(du -h dist/clipboard-ai-linux-x86_64 | cut -f1)"
echo
echo "To create daemon link:"
echo "  ln -s clipboard-ai-linux-x86_64 clipboard-ai-daemon"
echo
