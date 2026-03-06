import os
import sys
import threading
import re
import io
import logging
from datetime import datetime
from pathlib import Path

from config.settings import get_debug_mode


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
_install_stderr_filter()
_install_stdout_filter(aggressive=not get_debug_mode())

if not get_debug_mode():
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from PySide6.QtGui import QIcon

from core.main_window import MainWindow
from core.splash_screen import SplashScreen

if __name__ == "__main__":
    runtime_logger, runtime_log_file = _setup_runtime_logging()
    runtime_logger.info("Starting TaskEnforcerX")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.ico"))
    splash = SplashScreen()  # Create and show the splash screen

    window = MainWindow(splash)  # Pass the splash screen instance to the main window
    splash.show()  # Ensure the splash screen is on top during initialization
    runtime_logger.info("Splash shown; runtime log: %s", runtime_log_file)
    sys.exit(app.exec())