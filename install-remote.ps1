# install-remote.ps1 - One-liner Windows installer for Clipboard AI
# Usage: irm https://raw.githubusercontent.com/El-Mundos/clipboard-ai/main/install-remote.ps1 | iex

$ErrorActionPreference = "Stop"

# Configuration
$REPO = "El-Mundos/clipboard-ai"
$BINARY_NAME = "clipboard-ai-windows-x86_64.exe"
$INSTALL_DIR = "$env:LOCALAPPDATA\clipboard-ai"
$CONFIG_DIR = "$env:APPDATA\clipboard-ai"

Write-Host "==================================="
Write-Host "Clipboard AI Windows Installer"
Write-Host "==================================="
Write-Host ""

# Create directories
Write-Host "Creating directories..."
New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
New-Item -ItemType Directory -Force -Path "$CONFIG_DIR\prompts" | Out-Null
New-Item -ItemType Directory -Force -Path "$CONFIG_DIR\state\history" | Out-Null

# Get latest release
Write-Host "Fetching latest release..."
try {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$REPO/releases/latest"
} catch {
    Write-Host "Error: Failed to fetch release information" -ForegroundColor Red
    Write-Host "Make sure the repository has releases published"
    exit 1
}

$version = $release.tag_name
$asset = $release.assets | Where-Object { $_.name -eq $BINARY_NAME }

if (-not $asset) {
    Write-Host "Error: Could not find Windows binary ($BINARY_NAME) in release" -ForegroundColor Red
    Write-Host "Available assets:"
    $release.assets | ForEach-Object { Write-Host "  - $($_.name)" }
    exit 1
}

Write-Host "Found version: $version" -ForegroundColor Green

# Download binary
Write-Host "Downloading binary..."
$downloadUrl = $asset.browser_download_url
try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile "$INSTALL_DIR\clipboard-ai.exe"
} catch {
    Write-Host "Error: Download failed" -ForegroundColor Red
    exit 1
}

Write-Host "Binary installed to: $INSTALL_DIR\clipboard-ai.exe" -ForegroundColor Green

# Add to PATH if not already there
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$INSTALL_DIR*") {
    Write-Host "Adding to PATH..."
    [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$INSTALL_DIR", "User")
    Write-Host "PATH updated." -ForegroundColor Yellow
    Write-Host "NOTE: Restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==================================="
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "==================================="
Write-Host ""
Write-Host "Version: $version"
$fileSize = (Get-Item "$INSTALL_DIR\clipboard-ai.exe").Length / 1MB
Write-Host ("Binary size: {0:N1} MB" -f $fileSize)
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Open a NEW terminal (to get updated PATH)"
Write-Host ""
Write-Host "2. Configure your API key:"
Write-Host "     clipboard-ai --setup"
Write-Host ""
Write-Host "3. Set up a keyboard shortcut using AutoHotkey:"
Write-Host "   Install AutoHotkey from: https://www.autohotkey.com/"
Write-Host ""
Write-Host "   Create 'clipboard-ai.ahk' with:"
Write-Host "   ----------------------------------------"
Write-Host "   ; Win+V to send to AI"
Write-Host "   #v::Run, clipboard-ai, , Hide"
Write-Host ""
Write-Host "   ; Win+Shift+V for new conversation"
Write-Host "   #+v::Run, clipboard-ai --new, , Hide"
Write-Host "   ----------------------------------------"
Write-Host ""
Write-Host "   Save to your Startup folder to run automatically:"
Write-Host "   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  clipboard-ai --status       # Show conversation status"
Write-Host "  clipboard-ai --new          # Start new conversation"
Write-Host "  clipboard-ai --list-prompts # List available prompts"
Write-Host ""
Write-Host "Documentation: https://github.com/$REPO"
Write-Host ""
