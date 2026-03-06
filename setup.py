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


def _run_pyinstaller_build(debug_console: bool = False):
    _ensure_pyinstaller_available()

    from PyInstaller.__main__ import run as pyinstaller_run

    build_root = ROOT / "build"
    temp_work = build_root / "_pyi_work"

    _clean_previous_builds(temp_work)

    build_name = f"{APP_NAME}-Debug" if debug_console else APP_NAME

    args = [
        "--noconfirm",
        "--clean",
        f"--name={build_name}",
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

    if debug_console:
        args.insert(2, "--console")
        args.append(f"--runtime-hook={ROOT / 'debug' / 'pyi_runtime_debug.py'}")
    else:
        args.insert(2, "--windowed")

    pyinstaller_run(args)
    return build_name


if __name__ == "__main__":
    command = sys.argv[1].lower() if len(sys.argv) > 1 else ""

    if command == "build":
        build_name = _run_pyinstaller_build(debug_console=False)
        print("\nBuild completed. Output folder:")
        print(f"{ROOT / 'build' / build_name}")
        sys.exit(0)

    if command == "build-debug":
        build_name = _run_pyinstaller_build(debug_console=True)
        print("\nBuild completed. Output folder:")
        print(f"{ROOT / 'build' / build_name}")
        sys.exit(0)

    print("Usage: python setup.py build | python setup.py build-debug")
    sys.exit(1)
