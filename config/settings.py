import os
import sys
from pathlib import Path


def _load_dotenv_file() -> None:
    """
    Load key/value pairs from project .env into process environment.
    Existing OS environment variables always win.
    """
    try:
        project_root = Path(__file__).resolve().parent.parent
        dotenv_path = project_root / ".env"
        if not dotenv_path.exists() or not dotenv_path.is_file():
            return

        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.lower().startswith("export "):
                line = line[7:].strip()

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key or key in os.environ:
                continue

            if value and ((value[0] == value[-1]) and value[0] in {"\"", "'"}):
                value = value[1:-1]
            else:
                if " #" in value:
                    value = value.split(" #", 1)[0].strip()

            os.environ[key] = value
    except Exception:
        # Do not block app startup if .env has malformed lines.
        pass


_load_dotenv_file()


def _str_to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

# APP TEXTS
TITLE = "TaskEX"
TITLE_DESCRIPTION = "Ultimate Edition"
VERSION = "v0.0.0"
CREDITS = "By: MwoNuZzz"
DEBUG_MODE = _str_to_bool(os.getenv("TASKEX_DEBUG", "0"))
STRICT_MONSTER_MATCH = _str_to_bool(os.getenv("TASKEX_STRICT_MONSTER_MATCH", "0"))
# Private variable (not directly accessible)
__EXPIRE = os.getenv("TASKEX_EXPIRE", "")  # YYYY-MM-DD format; empty disables expiry check

# Public getter to access the expiry date
def get_expire():
    return __EXPIRE


def get_debug_mode():
    return DEBUG_MODE


def get_strict_monster_match():
    return STRICT_MONSTER_MATCH

# Project base directory
# BASE_DIR = Path(__file__).resolve().parent.parent

# DB URL
DATABASE_URL = f"sqlite:///{os.path.join(Path(__file__).resolve().parent.parent, 'db', 'task_ex.db')}"


