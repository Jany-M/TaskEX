from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import DATABASE_URL


def _database_file_path() -> Optional[Path]:
    if not DATABASE_URL.startswith("sqlite:///"):
        return None

    db_value = DATABASE_URL.replace("sqlite:///", "", 1)
    if not db_value:
        return None

    return Path(db_value).resolve()


def _project_base_dir() -> Path:
    # In frozen mode sys.executable parent is the dist folder.
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _create_backup_if_needed(db_path: Path) -> Optional[Path]:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return None

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    return backup_path


def _run_alembic_upgrade() -> bool:
    try:
        from alembic import command
        from alembic.config import Config
    except Exception:
        return False

    base_dir = _project_base_dir()
    ini_path = base_dir / "alembic.ini"
    script_location = base_dir / "alembic"
    if not ini_path.exists() or not script_location.exists():
        return False

    alembic_config = Config(str(ini_path))
    alembic_config.set_main_option("script_location", str(script_location))
    alembic_config.set_main_option("sqlalchemy.url", DATABASE_URL)

    command.upgrade(alembic_config, "head")
    return True


def migrate_database_with_backup() -> Optional[Path]:
    """Run Alembic migrations to head and return backup path when created."""
    db_path = _database_file_path()
    backup_path: Optional[Path] = None

    if db_path is not None:
        backup_path = _create_backup_if_needed(db_path)

    _run_alembic_upgrade()
    return backup_path
