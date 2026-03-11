# TaskEnforcerX

TaskEnforcerX is a Python-based bot designed to automate tasks in the mobile game Evony. It provides a free alternative to paid bot applications, allowing users to automate various in-game actions effortlessly.

## Installation

### Prerequisites:

  Before running TaskEnforcerX, ensure you have the following:
  
    - Python 3.12.4 installed
    - BlueStacks emulator
    - Qt Creator 14.0.1 (Community Edition)  for UI design

### Emulator Settings:

  For optimal performance, configure your BlueStacks emulator with these settings:
  
  📺 Display Settings
  
    - Resolution: 540x960
    - Pixel Density: 320 DPI
  
  🎮 Graphics Settings
  
    - Graphics Renderer: DirectX

### Installation Steps:

  1: Clone the repository:
  ```
  git clone https://github.com/Jany-M/TaskEX.git
  cd TaskEX
  ```
  2: Install dependencies:
  ```
  pip install -r requirements.txt
  ```
  3: Run the bot:
  ```
  python main.py
  ```

## Build for Windows (x64)

TaskEnforcerX can be packaged as a Windows executable using the included PyInstaller build config (via `setup.py`).

### Requirements

- Windows 64-bit
- Python 3.12 x64 (recommended to match runtime dependencies)
- Virtual environment with project dependencies installed

### Build Steps

1: Open PowerShell in the project root.

2: Activate your virtual environment:
```
.\.venv\Scripts\Activate.ps1
```

3: Install build dependency if needed:
```
pip install pyinstaller
```

4: Build the executable:
```
python setup.py build
```

Optional: build a debug executable (with console + debug splash controls):
```
python setup.py build-debug
```

### Output

- The packaged app is generated under the `build/` folder.
- Release build output: `build/TaskEnforcerX/`.
- Debug build output: `build/TaskEnforcerX-Debug/`.
- Run the generated `.exe` from inside that output folder so bundled assets and tools are resolved correctly.

### Notes

- Keep required runtime folders/files available during build (already configured in setup): `assets/`, `platform-tools/`, `Tesseract-OCR/`, and `db/task_ex.db`.
- If you specifically need x64 output, make sure your Python interpreter is x64 before building.

## Regenerate UI and Resources

Generated files should not be edited directly. Update source files first, then regenerate.

1: Open PowerShell in the project root.

2: Activate your virtual environment:
```
.\.venv\Scripts\Activate.ps1
```

3: Regenerate UI Python files from `.ui` sources:
```
pyside6-uic gui/ui_files/main.ui -o gui/generated/ui_main.py
pyside6-uic gui/ui_files/instance_page.ui -o gui/generated/instance_page.py
pyside6-uic gui/ui_files/general_profile.ui -o gui/generated/general_profile.py
pyside6-uic gui/ui_files/monster_profile.ui -o gui/generated/monster_profile.py
pyside6-uic gui/ui_files/monster_edit_dialog.ui -o gui/generated/monster_edit_dialog.py
pyside6-uic gui/ui_files/monster_upload_dialog.ui -o gui/generated/monster_upload_dialog.py
pyside6-uic gui/ui_files/black_market_profile.ui -o gui/generated/black_market_profile.py
pyside6-uic gui/ui_files/champion_profile.ui -o gui/generated/champion_profile.py
pyside6-uic gui/ui_files/generals_selection.ui -o gui/generated/generals_selection.py
pyside6-uic gui/ui_files/preset_configuration.ui -o gui/generated/preset_configuration.py
pyside6-uic gui/ui_files/march_speed_selection.ui -o gui/generated/march_speed_selection.py
pyside6-uic gui/ui_files/splash_screen.ui -o gui/generated/splash_screen.py
```

4: Regenerate Qt resources from `.qrc`:
```
pyside6-rcc resources/resources.qrc -o resources/resources_rc.py
```

## CLI Instance Control

TaskEX now supports command-line control of DB-registered emulator instances without opening the UI.

### List registered instances

```powershell
python main.py --list-instances
```

Example output:

```text
Registered TaskEX instances:
ID      Name    Port    Profile
3       Ant     5555    1
4       Kari    5585    1
5       Ant Alt 5575    2
```

### Start Evony for an existing instance

You can target by name, id, or port:

```powershell
python main.py --start-instance "Ant Alt"
python main.py --start-instance 5
python main.py --start-instance 5575
```

### Stop Evony for an existing instance

```powershell
python main.py --stop-instance "Ant Alt"
python main.py --stop-instance 5
python main.py --stop-instance 5575
```

## Feature Runtime Modes (Per Instance)

The run orchestrator supports three runtime modes per feature, per instance:

- `Auto-run always`: feature runs continuously while the instance thread is running
- `Manual start/stop`: feature runs only after clicking `Start` (button toggles to `Stop`)
- `Auto-run off`: feature is disabled at runtime

Supported features:

- Join Rally
- Auto Gather
- Auto Bubble

Default behavior:

- Auto Bubble: enabled + `Auto-run always`
- Join Rally: enabled + `Manual start/stop`
- Auto Gather: enabled + `Manual start/stop`

These values are saved in profile settings per instance.

## Global Template Manager Shortcuts

You can open template configuration dialogs from anywhere in the app:

- `Ctrl+Shift+B`: open Bubble Template Configuration
- `Ctrl+Shift+G`: open Resource Tile Template Configuration

Required template placeholders are documented in:

- [assets/540p/bubbles/README.md](assets/540p/bubbles/README.md)
- [assets/540p/gather/README.md](assets/540p/gather/README.md)

## MCP Development Setup (AI-Assisted Development)

TaskEnforcerX includes an MCP (Model Context Protocol) extension package that lets AI assistants like GitHub Copilot, Cursor or Claude interact directly with connected Android devices during development. This enables you to collaboratively develop new bot features with an AI that can see screenshots, tap the screen, read logs, and inspect the UI hierarchy in real time.

The setup uses [adb-mcp](https://github.com/Jany-M/adb-mcp) — a standalone MCP server for Android device control — extended with TaskEX-specific tools that live in this project under `mcp-extensions/`.

### Architecture

```
adb-mcp/                          ← standalone MCP server (separate repo)
  ↑ loads at startup via EXTENSIONS_DIR env var

TaskEX_Ant/
  mcp-extensions/                 ← TaskEX MCP tools (this project)
    src/taskex/                   ← TypeScript source
    dist/taskex/                  ← compiled output (what adb-mcp loads)
    taskex.config.json            ← your local config (not committed)
    taskex.config.example.json    ← config template
```

### Prerequisites

- [Node.js](https://nodejs.org/) v16 or higher
- [adb-mcp](https://github.com/Jany-M/adb-mcp) cloned and built (see its README)
- ADB in your PATH (comes with BlueStacks via `platform-tools/`)

### Setup

**1. Build the MCP extension:**

```powershell
cd mcp-extensions
npm install
npm run build
```

**2. Create your config file** (copy the example and edit):

```powershell
cp mcp-extensions\taskex.config.example.json mcp-extensions\taskex.config.json
```

Edit `taskex.config.json` to match your BlueStacks port(s) and settings. The full list of options is documented in [taskex.config.example.json](mcp-extensions/taskex.config.example.json).

**3. Configure your MCP client** — see sections below for VS Code and Claude Desktop.

### VS Code Configuration

Add to your VS Code `settings.json` (User or Workspace):

```json
{
  "mcp": {
    "servers": {
      "adb-mcp": {
        "type": "stdio",
        "command": "node",
        "args": ["C:/adb-mcp/dist/index.js"],
        "env": {
          "ADB_PATH": "C:/TaskEX_Ant/platform-tools/adb.exe",
          "EXTENSIONS_DIR": "C:/TaskEX_Ant/mcp-extensions/dist",
          "TASKEX_CONFIG_PATH": "C:/TaskEX_Ant/mcp-extensions/taskex.config.json"
        }
      }
    }
  }
}
```

> Adjust the paths to match your actual folder locations. `ADB_PATH` is required if `adb` is not on your system PATH (it usually isn't when launched via MCP).

### Claude Desktop Configuration

Add to your `claude_desktop_config.json` (usually at `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "adb-mcp": {
      "command": "node",
      "args": ["C:/adb-mcp/dist/index.js"],
      "env": {
        "ADB_PATH": "C:/TaskEX_Ant/platform-tools/adb.exe",
        "EXTENSIONS_DIR": "C:/TaskEX_Ant/mcp-extensions/dist",
        "TASKEX_CONFIG_PATH": "C:/TaskEX_Ant/mcp-extensions/taskex.config.json"
      }
    }
  }
}
```

### Available TaskEX MCP Tools

Once loaded, the following tools are available to the AI assistant:

| Tool | Description |
|------|-------------|
| `taskex_select_device_by_port` | Map a BlueStacks port (e.g. 5555) to an ADB device serial |
| `taskex_screenshot` | Capture the current screen; optionally return as base64 |
| `taskex_tap` | Tap at screen coordinates with retry logic |
| `taskex_swipe` | Swipe between two points with configurable speed |
| `taskex_keyevent` | Send key events: BACK, HOME, ENTER, POWER, VOLUME, digits |
| `taskex_wait_for_screen` | Wait for text to appear or disappear on screen |
| `taskex_evony_control` | Start/stop the Evony app |
| `taskex_debug_bundle` | Collect device info, logcat, UI hierarchy in one JSON bundle |
| `taskex_list_instances` | List DB-registered TaskEX instances (ID, name, port, profile) |
| `taskex_instance_control` | Start/stop instance by identifier, id, port, or name |
| `taskex_template_match` | Run OpenCV template match on the latest screenshot |
| `taskex_screen_region` | Crop a screen region and return metadata/image payload |
| `taskex_find_and_tap` | Find a template on-screen and tap matched coordinates |

### Instance MCP Examples

List instances from DB:

```json
{
  "tool": "taskex_list_instances",
  "args": {}
}
```

Start by name:

```json
{
  "tool": "taskex_instance_control",
  "args": {
    "action": "start",
    "name": "Ant Alt"
  }
}
```

Stop by port:

```json
{
  "tool": "taskex_instance_control",
  "args": {
    "action": "stop",
    "port": 5575
  }
}
```

### Configuration Reference

All settings can be set in `taskex.config.json` or overridden via environment variables.

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| *(adb binary)* | `ADB_PATH` | `adb` (from PATH) | Full path to `adb.exe` — **required** if adb is not in your system PATH |
| `blueStacksPorts` | `TASKEX_BLUESTACKS_PORTS` | `[5555, 5556]` | BlueStacks ADB ports |
| `evonyPackage` | `TASKEX_EVONY_PACKAGE` | `com.topgamesinc.evony` | App package name |
| `evonyActivity` | `TASKEX_EVONY_ACTIVITY` | `...UnityActivity` | Main activity |
| `screenStateTimeout` | — | `10000` | ms to wait in wait_for_screen |
| `logRetentionLines` | — | `100` | Logcat lines in debug bundle |
| `coordinateScaleX/Y` | — | `1.0` | Coordinate scaling factors |
| `taskexRootPath` | `TASKEX_ROOT_PATH` | auto | Optional absolute TaskEX root for instance MCP tools |
| `taskexPythonPath` | `TASKEX_PYTHON_PATH` | `<taskexRootPath>/.venv/Scripts/python.exe` | Optional Python path used by instance MCP tools |

Config file path: `TASKEX_CONFIG_PATH` env var (defaults to `./taskex.config.json` relative to where adb-mcp is launched).

The new instance tools call TaskEX CLI under the hood (`main.py --list-instances`, `--start-instance`, `--stop-instance`), so they work with DB-registered instances by name, id, or port without opening the TaskEX UI.

### Development Workflow

After changing any tool source file:

```powershell
cd mcp-extensions
npm run build
```

Then restart the MCP server in your editor (VS Code: Cmd/Ctrl+Shift+P → "MCP: Restart Server").

adb-mcp itself never needs to be modified or rebuilt for TaskEX tool changes.

## Screenshots / Demo

Here’s a preview of TaskEnforcerX in action:
![TaskEnforcerX Demo](https://github.com/evsahal/TaskEX/blob/master/demo.gif)


## License

TaskEnforcerX is licensed under the GNU General Public License v3.0 (GPL-3.0).

This means:

✅ You are free to use, modify, and distribute this software.

❌ You CANNOT copy, modify, or redistribute this software as a closed-source.

❌ Any modifications or derived works must also be released under GPL-3.0.


📜 You can read the full license details [here](https://github.com/evsahal/TaskEX/blob/master/LICENSE).

## Android - SDK Platform Tools (latest ADB.exe) 

[Official Google Download](https://developer.android.com/tools/releases/platform-tools)

## Contribution

If you find TaskEnforcerX helpful and would like to support its development, consider contributing!