# TaskEnforcerX

TaskEnforcerX is a Python-based bot designed to automate tasks in the mobile game Evony. It provides a free alternative to paid bot applications, allowing users to automate various in-game actions effortlessly.

## Installation

### Prerequisites:

  Before running TaskEnforcerX, ensure you have the following:
  
    - Python 3.12.4 installed
    - BlueStacks emulator
    - Qt Creator 14.0.1 (Community Edition) (used for UI design)

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
  git clone https://github.com/evsahal/TaskEX.git
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

### Output

- The packaged app is generated under the `build/` folder.
- For x64 Python, output is typically in `build/TaskEnforcerX/`.
- Run the generated `.exe` from inside that output folder so bundled assets and tools are resolved correctly.

### Notes

- Keep required runtime folders/files available during build (already configured in setup): `assets/`, `platform-tools/`, `Tesseract-OCR/`, and `db/task_ex.db`.
- If you specifically need x64 output, make sure your Python interpreter is x64 before building.

## Expiry Configuration

TaskEX supports an optional expiry check controlled by the `TASKEX_EXPIRE` environment variable.

- If `TASKEX_EXPIRE` is empty or not set, expiry validation is disabled.
- If set, it must use `YYYY-MM-DD` format (example: `2026-12-31`).
- Guest login does not bypass or trigger expiry; expiry is a global runtime check when configured.

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

## Contact 

For support, questions, or discussions about TaskEnforcerX, join the official Discord server:

[TaskEnforcerX Discord Community](https://discord.gg/CPCcxRQn2B)

Feel free to ask for help, report bugs, or suggest new features! 🚀

## Support & Donations

If you find TaskEnforcerX helpful and would like to support its development, consider making a donation. Your support helps keep the project free and open-source while enabling further improvements and new features!


💵 Paypal: https://paypal.me/taskenforcerx

☕ Buy Me a Coffee: https://buymeacoffee.com/taskenforcerx

💰 Donate via Crypto: DM me on Discord



