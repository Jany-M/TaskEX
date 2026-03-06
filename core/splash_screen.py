import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer, QSettings
from PySide6.QtWidgets import QMainWindow, QPushButton

from config.settings import VERSION
from gui.generated.splash_screen import Ui_SplashScreen


class SplashScreen(QMainWindow):

    # Define a signal to continue loading the splash screen
    load_signal = Signal()

    def __init__(self, parent=None):
        super(SplashScreen, self).__init__(parent)
        self.ui = Ui_SplashScreen()  # Create an instance of the UI class
        self.ui.setupUi(self)  # Initialize the UI on this QMainWindow

        # Set up the central widget using the generated UI setup
        self.setCentralWidget(self.ui.centralwidget)

        # Hide the window frame for a splash effect
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Set Splash Screen Version
        self.ui.label_title_version.setText(
            f'<html><head/><body><p>TaskEnforcerX <span style=" font-size:16pt;">{VERSION}</span></p></body></html>')

        # Always skip login and continue directly to loading.
        self.hide_login_frame()
        self.setup_debug_controls()
        QTimer.singleShot(0, self.load_signal.emit)

        self.show()  # Display the splash screen

    def check_previous_login(self):
        settings = QSettings("TaskEnforceX", "TaskEX")
        return settings.value("logged_in", False, type=bool)

    def save_login_state(self, state):
        settings = QSettings("TaskEnforceX", "TaskEX")
        settings.setValue("logged_in", state)

    def hide_login_frame(self):
        # Hide the login frame
        self.ui.login_frame.setMaximumHeight(0)

        # Unhide the progress frame
        self.ui.progress_frame.setMaximumHeight(16777215)

        # Set Splash screen window height
        self.setFixedHeight(380)

        # Adjust the layout margin
        layout = self.ui.header_frame.parentWidget().layout()

        # Retrieve the current margins
        left, top, right, bottom = layout.getContentsMargins()

        # Update only the top margin
        new_top = top + 50

        layout.setContentsMargins(left, new_top, right, bottom)

    def setup_debug_controls(self):
        if os.environ.get("TASKEX_DEBUG_BUILD") != "1":
            return

        self.ui.label_loading.setText("Debug build mode: startup logs enabled")

        self.debug_logs_btn = QPushButton("Open Logs", self.ui.progress_frame)
        self.debug_logs_btn.setMinimumHeight(32)
        self.debug_logs_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(98, 114, 164);
                color: white;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: rgb(120, 135, 190);
            }
        """)
        self.debug_logs_btn.clicked.connect(self.open_logs_folder)
        self.ui.verticalLayout_5.addWidget(self.debug_logs_btn)

    def open_logs_folder(self):
        logs_dir = self.get_logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)

        try:
            if sys.platform == "win32":
                os.startfile(str(logs_dir))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(logs_dir)])
            else:
                subprocess.Popen(["xdg-open", str(logs_dir)])
        except Exception:
            pass

    def get_logs_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path(__file__).resolve().parent.parent
        return base_dir / "logs"


    def login_as_guest(self):
        # print("Logged in as Guest")

        self.hide_login_frame()

        # Update the login state in persistent storage
        self.save_login_state(True)

        # Emit the signal to indicate guest login
        self.load_signal.emit()

        # # Start animations
        # self.animate_login_frame_hide()
        # self.animate_header_frame_move()


    # def animate_login_frame_hide(self):
    #     """ Animate hiding of the login frame by shrinking its height. """
    #     login_frame = self.ui.login_frame
    #     height = login_frame.height()
    #
    #     # Create an animation that changes the maximum height from current to 0
    #     animation = QPropertyAnimation(login_frame, b"maximumHeight")
    #     animation.setDuration(500)  # Animation duration in milliseconds
    #     animation.setStartValue(height)
    #     animation.setEndValue(0)
    #     animation.setEasingCurve(QEasingCurve.InOutQuad)  # easing for smooth animation
    #     animation.start()
    #
    #     # Adjust the main window height after animation completes
    #     animation.finished.connect(self.adjust_window_height(-height))
    #
    #     # Hide the login_frame completely after the animation
    #     animation.finished.connect( self.ui.login_frame.setMaximumHeight(0))
    #
    #
    # def animate_header_frame_move(self):
    #     """ Animate the header frame to move down slightly. """
    #     header_frame = self.ui.header_frame
    #     y_position = header_frame.pos().y()
    #
    #     # Create an animation to move the header_frame downwards
    #     animation = QPropertyAnimation(header_frame, b"pos")
    #     animation.setDuration(500)  # Animation duration in milliseconds
    #     animation.setStartValue(header_frame.pos())
    #     animation.setEndValue(header_frame.pos() + QPoint(0, 20))
    #     animation.start()
    #
    # def adjust_window_height(self, delta_height):
    #     """ Adjust the height of the QMainWindow. """
    #     # Set Splash screen window height
    #     self.setFixedHeight(350)