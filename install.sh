#!/bin/bash
set -e

echo "==================================="
echo "Clipboard AI Installation"
echo "==================================="
echo

# Check if binary exists
if [ ! -f "dist/clipboard-ai" ]; then
    echo "❌ Error: Binary not found at dist/clipboard-ai"
    echo "   Run ./build.sh first to create the binary"
    exit 1
fi

# Check for wl-clipboard
if ! command -v wl-paste &>/dev/null || ! command -v wl-copy &>/dev/null; then
    echo "⚠️  Warning: wl-clipboard not found"
    echo "   Install it with your package manager:"
    echo "   - Arch: sudo pacman -S wl-clipboard"
    echo "   - Ubuntu: sudo apt install wl-clipboard"
    echo "   - Fedora: sudo dnf install wl-clipboard"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create local bin directory
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"

# Copy binary
echo "Installing clipboard-ai binary..."
cp dist/clipboard-ai "$LOCAL_BIN/clipboard-ai"
chmod +x "$LOCAL_BIN/clipboard-ai"

# Create symlink for daemon
ln -sf clipboard-ai "$LOCAL_BIN/clipboard-ai-daemon"

echo "✓ Binary installed to $LOCAL_BIN"

# Install systemd service files
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

# Update service file to use the binary from ~/.local/bin
cat >"$SYSTEMD_USER_DIR/clipboard-ai.service" <<EOF
[Unit]
Description=Clipboard AI Daemon
Documentation=https://github.com/yourusername/clipboard-ai
Requires=clipboard-ai.socket
After=clipboard-ai.socket

[Service]
Type=simple
ExecStart=$LOCAL_BIN/clipboard-ai-daemon
Restart=no
StandardOutput=null
StandardError=journal

# Security hardening
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=%h/.config/clipboard-ai

[Install]
WantedBy=default.target
EOF

cp clipboard-ai.socket "$SYSTEMD_USER_DIR/"

echo "✓ Systemd service files installed"

# Reload systemd
echo
echo "Enabling systemd socket..."
systemctl --user daemon-reload
systemctl --user enable clipboard-ai.socket
systemctl --user start clipboard-ai.socket

echo "✓ Socket activated"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo
    echo "⚠️  Warning: $HOME/.local/bin is not in your PATH"
    echo "   Add this to your ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
fi

echo
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo
echo "Binary size: $(du -h $LOCAL_BIN/clipboard-ai | cut -f1)"
echo
echo "Next steps:"
echo "1. Run: clipboard-ai --setup"
echo "   (To configure your API key)"
echo
echo "2. Set up a keybind in your window manager:"
echo "   Command: clipboard-ai"
echo
echo "Example keybinds:"
echo "  Hyprland: bind = SUPER, V, exec, clipboard-ai"
echo "  Sway:     bindsym \$mod+v exec clipboard-ai"
echo "  i3:       bindsym \$mod+v exec clipboard-ai"
echo
echo "3. Copy text and press your keybind!"
echo
echo "Useful commands:"
echo "  clipboard-ai --status       # Show conversation status"
echo "  clipboard-ai --new          # Start new conversation"
echo "  clipboard-ai --list-prompts # List available prompts"
echo
