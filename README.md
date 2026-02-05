# Clipboard AI

Your AI assistant that lives in your clipboard. Copy text, press a keybind, paste the response. That's it.

Works on **Linux (Wayland)** and **Windows**.

## What is this?

Clipboard AI is an invisible AI assistant that works entirely through your clipboard. There's no window to open, no app to launch—just copy text and press a keybind. The AI response appears in your clipboard, ready to paste anywhere.

Perfect for:

- Quick questions while coding
- Writing assistance without context switching
- Translating text on the fly
- Getting explanations without opening a browser

## How it works

1. Copy any text
2. Press your keybind (you configure this)
3. AI processes it
4. Response appears in your clipboard
5. Paste anywhere

The conversation continues for 12 hours, so follow-up questions just work.

## Quick Install

### Linux (Wayland)

```bash
curl -fsSL https://raw.githubusercontent.com/El-Mundos/clipboard-ai/main/install-remote.sh | bash
```

### Windows

```powershell
irm https://raw.githubusercontent.com/El-Mundos/clipboard-ai/main/install-remote.ps1 | iex
```

Then configure your API key:

```bash
clipboard-ai --setup
```

## Requirements

### Linux
- Wayland compositor (Hyprland, Sway, etc.)
- `wl-clipboard` package
- A Google Gemini API key ([free here](https://aistudio.google.com/apikey))

Install wl-clipboard if needed:

```bash
# Arch Linux
sudo pacman -S wl-clipboard

# Ubuntu/Debian
sudo apt install wl-clipboard

# Fedora
sudo dnf install wl-clipboard
```

### Windows
- Windows 10 or 11
- A Google Gemini API key ([free here](https://aistudio.google.com/apikey))
- AutoHotkey (optional, for keybinds)

## Setting up your keybind

### Linux (Hyprland, Sway, i3)

Pick a key combo and add it to your window manager config:

**Hyprland**

```conf
# ~/.config/hypr/hyprland.conf
bind = SUPER, V, exec, clipboard-ai
bind = SUPER_SHIFT, V, exec, clipboard-ai --new
```

**Sway**

```conf
# ~/.config/sway/config
bindsym $mod+v exec clipboard-ai
bindsym $mod+Shift+v exec clipboard-ai --new
```

**i3**

```conf
# ~/.config/i3/config
bindsym $mod+v exec clipboard-ai
bindsym $mod+Shift+v exec clipboard-ai --new
```

I like `Super+V` because it's close to `Ctrl+V` for pasting, but pick whatever feels natural.

### Windows (AutoHotkey)

1. Install [AutoHotkey](https://www.autohotkey.com/)
2. Create a file called `clipboard-ai.ahk`:

```autohotkey
; Win+V to send to AI
#v::Run, clipboard-ai, , Hide

; Win+Shift+V for new conversation
#+v::Run, clipboard-ai --new, , Hide
```

3. Double-click the file to run it
4. (Optional) Put it in your Startup folder for auto-run:
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

## Using it

The basic flow:

1. Copy text (like you normally would)
2. Press your keybind
3. Paste the response

Want to continue the conversation? Just copy your follow-up and press the keybind again. It remembers context for 12 hours.

### Starting fresh

Press `Shift+keybind` (or whatever you mapped `--new` to) to start a new conversation.

Or copy the name of a prompt (like `writer` or `coder`) and press the keybind. More on prompts below.

### Useful commands

```bash
# See what's happening
clipboard-ai --status

# List available prompts
clipboard-ai --list-prompts

# Start over completely
clipboard-ai --new

# Nuclear option (clears everything)
clipboard-ai --reset
```

## Custom prompts

You can create different AI personalities for different tasks. Create files in your config directory:
- **Linux**: `~/.config/clipboard-ai/prompts/`
- **Windows**: `%APPDATA%\clipboard-ai\prompts\`

**writer.json** - for creative writing

```json
{
  "name": "writer",
  "first_message": "You are a creative writing assistant. Help improve prose, suggest better phrasing, and make writing more vivid. Be encouraging but honest. Respond with ONLY: 'Writer mode active. Paste your text.'",
  "model": "gemini-2.5-flash",
  "temperature": 0.9,
  "thinking_enabled": false
}
```

**coder.json** - for code review

```json
{
  "name": "coder",
  "first_message": "You are a code review assistant. Focus on bugs, performance, and best practices. Be concise and actionable. Respond with ONLY: 'Code review mode active. Paste your code.'",
  "model": "gemini-2.5-flash",
  "temperature": 0.3,
  "thinking_enabled": false
}
```

To use a prompt, just copy its name (like `writer`) and press your keybind. The next message will use that prompt's personality.

**Available models:**

- `gemini-2.5-flash` - Default, fast and smart
- `gemini-2.5-flash-lite` - Faster, simpler tasks
- `gemini-2.5-pro` - Slower but smarter

**Temperature:** Controls randomness

- `0.3` - Focused and consistent (good for code)
- `0.7` - Balanced (default)
- `0.9` - Creative and varied (good for writing)

## Building from source

Want to modify it or don't trust pre-built binaries?

```bash
git clone https://github.com/El-Mundos/clipboard-ai.git
cd clipboard-ai

# Install dependencies
pip install pyinstaller google-genai

# Build (Linux)
./build.sh

# Build (Windows - run in PowerShell)
./build.ps1

# Install (Linux only)
./install.sh
```

## How it actually works

### Linux

When you press your keybind:

1. The client reads your clipboard via `wl-paste`
2. Sends it to a daemon via Unix socket
3. Systemd starts the daemon if it's not running (socket activation)
4. Daemon keeps a Gemini chat session in memory
5. Response comes back, client puts it in clipboard via `wl-copy`
6. After 12 hours idle, daemon archives the conversation and exits

### Windows

When you press your keybind:

1. The client reads your clipboard via `pyperclip`
2. Sends it to a daemon via localhost TCP (port 61472)
3. Client starts the daemon if it's not running
4. Daemon keeps a Gemini chat session in memory
5. Response comes back, client puts it in clipboard
6. After 12 hours idle, daemon archives the conversation and exits

This means it's fast (no startup time) but doesn't waste resources when you're not using it.

## Configuration

Everything lives in your config directory:
- **Linux**: `~/.config/clipboard-ai/`
- **Windows**: `%APPDATA%\clipboard-ai\`

```
config.json          # Main settings
prompts/             # Your custom prompts
  default.json
  writer.json
  ...
state/
  current.json       # Active conversation
  history/           # Old conversations
```

Edit `config.json` to change defaults:

```json
{
  "api_key": "your-key-here",
  "default_prompt": "default",
  "default_model": "gemini-2.5-flash",
  "conversation_timeout_hours": 12,
  "thinking_enabled": false,
  "debug": false,
  "max_retries": 3,
  "retry_delay_seconds": 2
}
```

## Troubleshooting

### Linux

**Nothing happens when I press the keybind**

Check if the socket is active:

```bash
systemctl --user status clipboard-ai.socket
```

If it's not running:

```bash
systemctl --user start clipboard-ai.socket
```

**Daemon won't start**

Check the logs:

```bash
journalctl --user -u clipboard-ai.service -n 50
```

### Windows

**Nothing happens when I press the keybind**

Make sure AutoHotkey is running (check system tray).

Try running clipboard-ai directly:

```powershell
clipboard-ai --status
```

**Daemon port conflict**

If port 61472 is in use, the daemon will fail to start. Check with:

```powershell
netstat -an | findstr 61472
```

### Both platforms

**"API key not configured"**

Run the setup:

```bash
clipboard-ai --setup
```

**Want to see what's happening**

Enable debug mode:

```bash
# Edit config.json and set "debug": true

# Watch logs
# Linux: tail -f ~/.config/clipboard-ai/debug.log
# Windows: Get-Content "$env:APPDATA\clipboard-ai\debug.log" -Wait
```

**Everything's broken**

Nuclear option:

```bash
clipboard-ai --reset
# Then on Linux: systemctl --user restart clipboard-ai.socket
```

## API limits

Gemini's free tier is generous:

- 15 requests per minute
- 1 million tokens per day

You'll likely never hit these with normal use. If you do, the tool will retry automatically after a short delay.

## Why I built this

I wanted AI assistance without leaving my keyboard. Opening ChatGPT in a browser, copying text, pasting results—too much friction. This tool makes AI feel like a natural part of the workflow, not a separate app you have to visit.

## Contributing

Found a bug? Have an idea? Open an issue or PR on [GitHub](https://github.com/El-Mundos/clipboard-ai).

## TODO

Some things I'd like to add:

- More default prompts (translator, summarizer, etc.)
- X11 clipboard support (currently Wayland only on Linux)
- Token usage tracking
- Conversation export/import
- Maybe a TUI for browsing history?
- ARM64 builds

## Acknowledgments

- Built with [Google Gemini API](https://ai.google.dev/)
- Uses `wl-clipboard` for Wayland clipboard access (Linux)
- Uses `pyperclip` for clipboard access (Windows)
- Systemd socket activation makes the daemon lifecycle elegant (Linux)

---

Made for people who live in terminals and hate context switching.
