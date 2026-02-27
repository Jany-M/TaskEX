import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP_NAME = "TaskEnforcerX"


def _ensure_pyinstaller_available():
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "PyInstaller is not installed in the active environment. "
            "Install it with: pip install pyinstaller"
        ) from exc


def _clean_previous_builds(build_path: Path):
    if build_path.exists():
        shutil.rmtree(build_path, ignore_errors=True)


def _run_pyinstaller_build():
    _ensure_pyinstaller_available()

    from PyInstaller.__main__ import run as pyinstaller_run

    build_root = ROOT / "build"
    temp_work = build_root / "_pyi_work"

    _clean_previous_builds(temp_work)

    args = [
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--name={APP_NAME}",
        f"--distpath={build_root}",
        f"--workpath={temp_work}",
        f"--specpath={build_root}",
        f"--icon={ROOT / 'icon.ico'}",
        f"--add-data={ROOT / 'platform-tools'};platform-tools",
        f"--add-data={ROOT / 'Tesseract-OCR'};Tesseract-OCR",
        f"--add-data={ROOT / 'assets'};assets",
        f"--add-data={ROOT / 'db' / 'task_ex.db'};db",
        "--hidden-import=sqlalchemy.dialects.sqlite",
        str(ROOT / "main.py"),
    ]

    pyinstaller_run(args)


if __name__ == "__main__":
    command = sys.argv[1].lower() if len(sys.argv) > 1 else ""

    if command == "build":
        _run_pyinstaller_build()
        print("\nBuild completed. Output folder:")
        print(f"{ROOT / 'build' / APP_NAME}")
        sys.exit(0)

    print("Usage: python setup.py build")
    sys.exit(1)
