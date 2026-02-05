# build.ps1 - Windows build script for Clipboard AI
$ErrorActionPreference = "Stop"

Write-Host "==================================="
Write-Host "Building Clipboard AI (Windows)"
Write-Host "==================================="
Write-Host ""

# Check for PyInstaller
$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host "Installing PyInstaller..."
    pip install pyinstaller
}

# Check for pyperclip (required for Windows clipboard)
Write-Host "Ensuring pyperclip is installed..."
pip install pyperclip

# Create unified entry point
Write-Host "Creating unified entry point..."
$entryPoint = @'
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
'@
$entryPoint | Out-File -FilePath "src/clipboard_ai.py" -Encoding utf8

# Build the binary
Write-Host ""
Write-Host "Building binary with PyInstaller..."
pyinstaller `
    --onefile `
    --name clipboard-ai-windows-x86_64 `
    --hidden-import=google.genai `
    --hidden-import=google.genai.types `
    --hidden-import=google.genai.errors `
    --hidden-import=pyperclip `
    --add-data "src/config.py;." `
    --add-data "src/state.py;." `
    --add-data "src/daemon.py;." `
    --add-data "src/client.py;." `
    --add-data "src/platform;platform" `
    --clean `
    src/clipboard_ai.py

Write-Host ""
Write-Host "Binary built successfully!" -ForegroundColor Green
Write-Host "  Location: dist/clipboard-ai-windows-x86_64.exe"
Write-Host ""
Write-Host "Testing binary..."
& ".\dist\clipboard-ai-windows-x86_64.exe" --help

$fileSize = (Get-Item "dist/clipboard-ai-windows-x86_64.exe").Length / 1MB
Write-Host ""
Write-Host "==================================="
Write-Host "Build Complete!"
Write-Host "==================================="
Write-Host ""
Write-Host "The binary is at: dist/clipboard-ai-windows-x86_64.exe"
Write-Host ("File size: {0:N1} MB" -f $fileSize)
Write-Host ""
