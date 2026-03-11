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
VERSION = "v0.0.3"
CREDITS = "By: MwoNuZzz & TheAnt"
DEBUG_MODE = _str_to_bool(os.getenv("TASKEX_DEBUG", "0"))
STRICT_MONSTER_MATCH = _str_to_bool(os.getenv("TASKEX_STRICT_MONSTER_MATCH", "0"))


def get_debug_mode():
    return DEBUG_MODE


def get_strict_monster_match():
    return STRICT_MONSTER_MATCH

# Project base directory
# BASE_DIR = Path(__file__).resolve().parent.parent

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _get_app_data_dir() -> Path:
    """Get the application data directory (AppData/Local for built exe, project root for dev)."""
    if getattr(sys, "frozen", False):
        # For built exe: use %LOCALAPPDATA%\TaskEnforcerX
        app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        app_dir = app_data / "TaskEnforcerX"
    else:
        # For development: use project db folder
        app_dir = _get_base_dir() / "db"
    
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def _get_database_path() -> Path:
    """
    Get database path. For built exe, uses persistent AppData location.
    On first run, copies bundled database from exe directory if it exists.
    """
    db_path = _get_app_data_dir() / "task_ex.db"
    
    # If running as exe and database doesn't exist in AppData, try to copy bundled version
    if getattr(sys, "frozen", False) and not db_path.exists():
        bundled_db = _get_base_dir() / "db" / "task_ex.db"
        if bundled_db.exists():
            try:
                import shutil
                shutil.copy2(bundled_db, db_path)
            except Exception:
                # If copy fails, database will be created fresh on init_db()
                pass
    
    return db_path


# DB URL
DATABASE_URL = f"sqlite:///{_get_database_path()}"


