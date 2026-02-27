import os
import sys
import threading
import re

from config.settings import get_debug_mode


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


def _install_stdout_filter():
    """
    In non-debug mode, suppress noisy stdout lines and keep likely errors.
    """
    try:
        stdout_fd = sys.__stdout__.fileno()
        saved_stdout_fd = os.dup(stdout_fd)
        read_fd, write_fd = os.pipe()

        os.dup2(write_fd, stdout_fd)
        os.close(write_fd)

        passthrough_regex = re.compile(r"error|exception|traceback|critical|failed", re.IGNORECASE)

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
                        if passthrough_regex.search(line):
                            writer.write((line + "\n").encode("utf-8", errors="replace"))
                            writer.flush()

                if buffer and passthrough_regex.search(buffer):
                    writer.write(buffer.encode("utf-8", errors="replace"))
                    writer.flush()

        threading.Thread(target=_forward_stdout, daemon=True).start()
    except Exception:
        pass


if not get_debug_mode():
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
    os.environ.setdefault("QT_LOGGING_RULES", "qt.gui.imageio.warning=false")
    _install_stderr_filter()
    _install_stdout_filter()

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from PySide6.QtGui import QIcon

from core.main_window import MainWindow
from core.splash_screen import SplashScreen

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.ico"))
    splash = SplashScreen()  # Create and show the splash screen

    window = MainWindow(splash)  # Pass the splash screen instance to the main window
    splash.show()  # Ensure the splash screen is on top during initialization
    sys.exit(app.exec())