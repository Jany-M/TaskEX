import os
import sys
import threading
import re
import io
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from config.settings import get_debug_mode


def _is_cli_invocation(argv: list[str]) -> bool:
    cli_flags = {"--list-instances", "--start-instance", "--stop-instance"}
    return any(arg in cli_flags for arg in argv)


def _enforce_qt_imageio_suppression():
    """
    Ensure noisy Qt/libpng image warnings are always suppressed, including debug mode.
    """
    try:
        existing_rules = os.environ.get("QT_LOGGING_RULES", "").strip()
        required_rule = "qt.gui.imageio.warning=false"

        if not existing_rules:
            os.environ["QT_LOGGING_RULES"] = required_rule
            return

        tokens = [token.strip() for token in existing_rules.split(";") if token.strip()]
        has_required_rule = any(token.lower() == required_rule for token in tokens)
        if not has_required_rule:
            tokens.append(required_rule)
            os.environ["QT_LOGGING_RULES"] = ";".join(tokens)
    except Exception:
        pass


def _install_stderr_filter():
    """
    Filter noisy native stderr lines (e.g. libpng sBIT warnings) while preserving all other output.
    """
    try:
        stderr_fd = sys.__stderr__.fileno()
        saved_stderr_fd = os.dup(stderr_fd)
        read_fd, write_fd = os.pipe()

        os.dup2(write_fd, stderr_fd)
        os.close(write_fd)

        patterns = (
            "libpng warning: sBIT: invalid",
            "qt.gui.imageio: libpng warning: sBIT: invalid",
            "libpng warning: sBIT: bad length",
            "qt.gui.imageio: libpng warning: sBIT: bad length",
        )

        def _forward_stderr():
            buffer = ""
            with os.fdopen(read_fd, "rb", closefd=True) as reader, os.fdopen(saved_stderr_fd, "wb", closefd=True) as writer:
                while True:
                    chunk = reader.read(4096)
                    if not chunk:
                        break

                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if any(pattern in line for pattern in patterns):
                            continue
                        writer.write((line + "\n").encode("utf-8", errors="replace"))
                        writer.flush()

                if buffer and not any(pattern in buffer for pattern in patterns):
                    writer.write(buffer.encode("utf-8", errors="replace"))
                    writer.flush()

        threading.Thread(target=_forward_stderr, daemon=True).start()
    except Exception:
        pass


def _install_stdout_filter(aggressive: bool = False):
    """
    Filter stdout noise.
    - Always suppresses known libpng sBIT warnings.
    - In aggressive mode (non-debug), only forwards likely error lines.
    """
    try:
        stdout_fd = sys.__stdout__.fileno()
        saved_stdout_fd = os.dup(stdout_fd)
        read_fd, write_fd = os.pipe()

        os.dup2(write_fd, stdout_fd)
        os.close(write_fd)

        passthrough_regex = re.compile(r"error|exception|traceback|critical|failed", re.IGNORECASE)
        drop_patterns = (
            "libpng warning: sBIT: invalid",
            "qt.gui.imageio: libpng warning: sBIT: invalid",
            "libpng warning: sBIT: bad length",
            "qt.gui.imageio: libpng warning: sBIT: bad length",
        )

        def _forward_stdout():
            buffer = ""
            with os.fdopen(read_fd, "rb", closefd=True) as reader, os.fdopen(saved_stdout_fd, "wb", closefd=True) as writer:
                while True:
                    chunk = reader.read(4096)
                    if not chunk:
                        break

                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if any(pattern in line for pattern in drop_patterns):
                            continue

                        if not aggressive:
                            writer.write((line + "\n").encode("utf-8", errors="replace"))
                            writer.flush()
                            continue

                        if passthrough_regex.search(line):
                            writer.write((line + "\n").encode("utf-8", errors="replace"))
                            writer.flush()

                if buffer and not any(pattern in buffer for pattern in drop_patterns):
                    if not aggressive or passthrough_regex.search(buffer):
                        writer.write(buffer.encode("utf-8", errors="replace"))
                        writer.flush()

        threading.Thread(target=_forward_stdout, daemon=True).start()
    except Exception:
        pass


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class _StreamTee(io.TextIOBase):
    def __init__(self, original_stream, log_stream):
        self.original_stream = original_stream
        self.log_stream = log_stream

    def write(self, message):
        try:
            self.original_stream.write(message)
        except Exception:
            pass
        try:
            self.log_stream.write(message)
            self.log_stream.flush()
        except Exception:
            pass
        return len(message)

    def flush(self):
        try:
            self.original_stream.flush()
        except Exception:
            pass
        try:
            self.log_stream.flush()
        except Exception:
            pass


def _setup_runtime_logging():
    base_dir = _runtime_base_dir()
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"taskex_runtime_{timestamp}.log"

    logger = logging.getLogger("taskex_boot")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(file_handler)

    should_tee_streams = getattr(sys, "frozen", False) or os.environ.get("TASKEX_LIVE_LOG", "0") == "1"
    if should_tee_streams:
        log_stream = open(log_file, "a", encoding="utf-8", buffering=1)
        sys.stdout = _StreamTee(sys.stdout, log_stream)
        sys.stderr = _StreamTee(sys.stderr, log_stream)

    def _handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        try:
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        except Exception:
            pass

    sys.excepthook = _handle_uncaught_exception
    logger.info("Runtime logging initialized: %s", log_file)
    return logger, log_file


_enforce_qt_imageio_suppression()
if not _is_cli_invocation(sys.argv[1:]):
    _install_stderr_filter()
    _install_stdout_filter(aggressive=not get_debug_mode())

if not get_debug_mode():
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")

def _load_instances_from_db() -> List[dict]:
    from db.db_setup import get_session, init_db
    from db.models.instance import Instance

    init_db()
    session = get_session()
    try:
        rows = session.query(Instance).order_by(Instance.id.asc()).all()
        return [
            {
                "id": row.id,
                "name": (row.emulator_name or "").strip(),
                "port": row.emulator_port,
                "profile_id": row.profile_id,
            }
            for row in rows
        ]
    finally:
        session.close()


def _resolve_instance(identifier: str) -> Optional[dict]:
    instances = _load_instances_from_db()
    key = (identifier or "").strip()
    if not key:
        return None

    numeric_value: Optional[int] = None
    if key.isdigit():
        numeric_value = int(key)

    if numeric_value is not None:
        by_id = next((item for item in instances if item["id"] == numeric_value), None)
        if by_id:
            return by_id

        by_port = next((item for item in instances if item["port"] == numeric_value), None)
        if by_port:
            return by_port

    key_lower = key.lower()
    by_name_exact = next((item for item in instances if item["name"].lower() == key_lower), None)
    if by_name_exact:
        return by_name_exact

    by_name_partial = [item for item in instances if key_lower in item["name"].lower()]
    if len(by_name_partial) == 1:
        return by_name_partial[0]

    return None


def _cli_list_instances() -> int:
    instances = _load_instances_from_db()
    if not instances:
        print("No registered instances found in database.")
        return 0

    print("Registered TaskEX instances:")
    print("ID\tName\tPort\tProfile")
    for item in instances:
        print(f"{item['id']}\t{item['name'] or '-'}\t{item['port'] or '-'}\t{item['profile_id'] or '-'}")
    return 0


def _cli_control_instance(identifier: str, start: bool) -> int:
    from utils.adb_manager import ADBManager

    instance = _resolve_instance(identifier)
    if not instance:
        print(f"Instance not found for identifier: {identifier}")
        print("Use --list-instances to see valid names, ids, and ports.")
        return 2

    port = instance.get("port")
    if not port:
        print(f"Instance '{instance.get('name') or instance.get('id')}' has no port configured.")
        return 2

    try:
        ADBManager.initialize_adb()
        manager = ADBManager(str(port))
        if not manager.device:
            print(f"Could not connect to emulator on port {port}.")
            return 3

        manager.launch_evony(start=start)
        state = "started" if start else "stopped"
        print(f"Evony {state} on instance '{instance.get('name') or instance.get('id')}' (port {port}).")
        return 0
    except Exception as exc:
        print(f"Failed to control instance '{identifier}': {exc}")
        return 4


def _run_cli_if_requested(argv: List[str]) -> Optional[int]:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--list-instances", action="store_true", help="List registered emulator instances from DB")
    parser.add_argument("--start-instance", type=str, help="Start Evony on instance by id, name, or port")
    parser.add_argument("--stop-instance", type=str, help="Stop Evony on instance by id, name, or port")

    args, _unknown = parser.parse_known_args(argv)

    if args.list_instances:
        return _cli_list_instances()

    if args.start_instance and args.stop_instance:
        print("Use either --start-instance or --stop-instance, not both.")
        return 2

    if args.start_instance:
        return _cli_control_instance(args.start_instance, start=True)

    if args.stop_instance:
        return _cli_control_instance(args.stop_instance, start=False)

    return None

if __name__ == "__main__":
    cli_exit_code = _run_cli_if_requested(sys.argv[1:])
    if cli_exit_code is not None:
        sys.exit(cli_exit_code)

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from core.main_window import MainWindow
    from core.splash_screen import SplashScreen

    runtime_logger, runtime_log_file = _setup_runtime_logging()
    runtime_logger.info("Starting TaskEnforcerX")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.ico"))
    splash = SplashScreen()  # Create and show the splash screen

    window = MainWindow(splash)  # Pass the splash screen instance to the main window
    splash.show()  # Ensure the splash screen is on top during initialization
    runtime_logger.info("Splash shown; runtime log: %s", runtime_log_file)
    sys.exit(app.exec())