#!/bin/bash
set -e

# Configuration
REPO="El-Mundos/clipboard-ai" # UPDATE THIS with your GitHub username
BINARY_NAME="clipboard-ai"
INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/clipboard-ai"
SYSTEMD_DIR="$HOME/.config/systemd/user"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "==================================="
echo "Clipboard AI Remote Installer"
echo "==================================="
echo

# Check for required commands
command_exists() {
    command -v "$1" &>/dev/null
}

if ! command_exists curl && ! command_exists wget; then
    echo -e "${RED}❌ Error: Neither curl nor wget found${NC}"
    echo "Install one of them to continue"
    exit 1
fi

DOWNLOAD_CMD="curl -fsSL"
if ! command_exists curl; then
    DOWNLOAD_CMD="wget -qO-"
fi

# Check for wl-clipboard
if ! command_exists wl-paste || ! command_exists wl-copy; then
    echo -e "${YELLOW}⚠️  Warning: wl-clipboard not found${NC}"
    echo "Install it with your package manager:"
    echo "  - Arch: sudo pacman -S wl-clipboard"
    echo "  - Ubuntu: sudo apt install wl-clipboard"
    echo "  - Fedora: sudo dnf install wl-clipboard"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Detect architecture
ARCH=$(uname -m)
case "$ARCH" in
x86_64)
    ARCH="x86_64"
    ;;
aarch64 | arm64)
    ARCH="aarch64"
    ;;
*)
    echo -e "${RED}❌ Unsupported architecture: $ARCH${NC}"
    exit 1
    ;;
esac

echo "Detected architecture: $ARCH"

# Get latest release info
echo "Fetching latest release..."
RELEASE_JSON=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest")

if [ -z "$RELEASE_JSON" ]; then
    echo -e "${RED}❌ Failed to fetch release information${NC}"
    echo "Make sure the repository has releases published"
    exit 1
fi

# Extract download URL for the binary
DOWNLOAD_URL=$(echo "$RELEASE_JSON" | grep -o "https://github.com/$REPO/releases/download/[^\"]*/$BINARY_NAME" | head -1)
VERSION=$(echo "$RELEASE_JSON" | grep -o '"tag_name": "[^"]*"' | cut -d'"' -f4)

if [ -z "$DOWNLOAD_URL" ]; then
    echo -e "${RED}❌ Could not find binary in latest release${NC}"
    echo "Make sure the release contains a file named '$BINARY_NAME'"
    exit 1
fi

echo -e "${GREEN}✓ Found version: $VERSION${NC}"

# Create directories
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR/prompts"
mkdir -p "$CONFIG_DIR/state/history"
mkdir -p "$SYSTEMD_DIR"

# Download binary
echo "Downloading clipboard-ai binary..."
TMP_FILE=$(mktemp)

if command_exists curl; then
    curl -fsSL "$DOWNLOAD_URL" -o "$TMP_FILE"
else
    wget -qO "$TMP_FILE" "$DOWNLOAD_URL"
fi

if [ ! -s "$TMP_FILE" ]; then
    echo -e "${RED}❌ Download failed${NC}"
    rm -f "$TMP_FILE"
    exit 1
fi

# Install binary
echo "Installing binary..."
mv "$TMP_FILE" "$INSTALL_DIR/$BINARY_NAME"
chmod +x "$INSTALL_DIR/$BINARY_NAME"

# Create daemon symlink
ln -sf "$BINARY_NAME" "$INSTALL_DIR/${BINARY_NAME}-daemon"

echo -e "${GREEN}✓ Binary installed to $INSTALL_DIR${NC}"

# Download and install systemd service files
echo "Installing systemd service files..."

# Socket file
cat >"$SYSTEMD_DIR/clipboard-ai.socket" <<'EOF'
[Unit]
Description=Clipboard AI Socket
Documentation=https://github.com/yourusername/clipboard-ai

[Socket]
ListenStream=/tmp/clipboard-ai-%U.sock
SocketMode=0600

[Install]
WantedBy=sockets.target
EOF

# Service file
cat >"$SYSTEMD_DIR/clipboard-ai.service" <<EOF
[Unit]
Description=Clipboard AI Daemon
Documentation=https://github.com/$REPO
Requires=clipboard-ai.socket
After=clipboard-ai.socket

[Service]
Type=simple
ExecStart=$INSTALL_DIR/clipboard-ai-daemon
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

# Reload and enable systemd
echo "Enabling systemd socket..."
systemctl --user daemon-reload
systemctl --user enable clipboard-ai.socket 2>/dev/null || true
systemctl --user start clipboard-ai.socket 2>/dev/null || true

echo -e "${GREEN}✓ Systemd services configured${NC}"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo
    echo -e "${YELLOW}⚠️  Warning: $HOME/.local/bin is not in your PATH${NC}"
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
    echo "Then reload your shell:"
    echo "  source ~/.bashrc  # or source ~/.zshrc"
    echo
fi

# Success message
echo
echo "==================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "==================================="
echo
echo "Version: $VERSION"
echo "Binary size: $(du -h "$INSTALL_DIR/$BINARY_NAME" 2>/dev/null | cut -f1 || echo "unknown")"
echo
echo "Next steps:"
echo "1. Reload your shell (if needed):"
echo "     source ~/.bashrc"
echo
echo "2. Configure your API key:"
echo "     clipboard-ai --setup"
echo
echo "3. Set up a keybind in your window manager:"
echo "   Hyprland: bind = SUPER, V, exec, clipboard-ai"
echo "   Sway:     bindsym \$mod+v exec clipboard-ai"
echo "   i3:       bindsym \$mod+v exec clipboard-ai"
echo
echo "4. Copy text and press your keybind!"
echo
echo "Useful commands:"
echo "  clipboard-ai --status       # Show conversation status"
echo "  clipboard-ai --new          # Start new conversation"
echo "  clipboard-ai --list-prompts # List available prompts"
echo
echo "Documentation: https://github.com/$REPO"
echo
