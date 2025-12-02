#!/bin/bash
set -e

echo "==================================="
echo "Building Clipboard AI Binary"
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
    --name clipboard-ai \
    --hidden-import=google.genai \
    --hidden-import=google.genai.types \
    --hidden-import=google.genai.errors \
    --add-data "src/config.py:." \
    --add-data "src/state.py:." \
    --add-data "src/daemon.py:." \
    --add-data "src/client.py:." \
    --clean \
    src/clipboard_ai.py

echo
echo "✓ Binary built successfully!"
echo "  Location: dist/clipboard-ai"
echo
echo "Testing binary..."
./dist/clipboard-ai --help

echo
echo "==================================="
echo "Build Complete!"
echo "==================================="
echo
echo "The binary is at: dist/clipboard-ai"
echo "File size: $(du -h dist/clipboard-ai | cut -f1)"
echo
echo "To create daemon link:"
echo "  ln -s clipboard-ai clipboard-ai-daemon"
echo
