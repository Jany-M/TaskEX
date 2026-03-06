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


## Contribution

If you find TaskEnforcerX helpful and would like to support its development, consider contributing!