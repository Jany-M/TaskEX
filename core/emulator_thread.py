import time
import os
import traceback

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from config.settings import get_debug_mode
from core.services.bm_monsters_service import start_simulate_monster_click, \
    generate_template_image, capture_template_ss
from core.services.bm_scan_generals_service import start_scan_generals
from db.models import General
from features.logic.join_rally import run_join_rally_scan_pass
from features.logic.auto_bubble import run_auto_bubble_check
from features.logic.auto_gather import run_auto_gather_cycle
from utils.adb_manager import ADBManager
import logging

from utils.get_controls_info import get_game_settings_controls, get_all_feature_controls
from utils.image_recognition_utils import is_template_match, template_match_coordinates


class EmulatorThread(QThread):
    # Define signals to communicate with the main thread
    finished = Signal(int, bool)  # Emits when the thread is finished (index, success flag)
    error = Signal(int, str)  # Emits when an error occurs (index, error message)
    add_general_signal = Signal(General)
    scan_general_finished = Signal()
    scan_general_console = Signal(str)
    scan_general_error = Signal()

    def __init__(self, main_window, port: str, index: int, operation_type: str, parent=None, ref=None):
        super().__init__(parent)
        self.main_window = main_window
        self.port = port
        self.index = index
        self.operation_type = operation_type
        self.ref = ref
        self._running = True
        self.adb_manager = ADBManager(port)
        self.logger = self.configure_logger()
        self.game_settings = {}
        self.cache = {}

    def configure_logger(self):
        """
        Configures and returns a logger with separate file and console handlers.
        """
        logger_name = self.operation_type if self.operation_type != "emu" else getattr(self.main_window.widgets,
                                                                                       f"emu_name_{self.index}").text()
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

        # Ensure handlers are not duplicated
        if not logger.handlers:
            # File handler setup
            logs_dir = "logs"
            os.makedirs(logs_dir, exist_ok=True)
            log_file_path = os.path.join(logs_dir, "logs.log")
            if not os.path.exists(log_file_path):
                with open(log_file_path, "w") as f:
                    pass  # Create an empty log file
            file_handler = logging.FileHandler(log_file_path, mode="a")
            file_formatter = logging.Formatter('[%(name)s] [%(asctime)s] [%(levelname)s]: %(message)s')
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG if get_debug_mode() else logging.ERROR)
            logger.addHandler(file_handler)

            # QTextEdit handler setup
            console_widget = getattr(self.main_window.widgets, f"console_{self.index}", None)
            if console_widget:
                class QTextEditHandler(logging.Handler):
                    def emit(self, record):
                        msg = self.format(record)
                        console_widget.append(msg)

                self.console_handler = QTextEditHandler()
                self.console_handler.setFormatter(file_formatter)
                self.console_handler.setLevel(logging.DEBUG if get_debug_mode() else logging.ERROR)
                logger.addHandler(self.console_handler)

        return logger

    def log_message(self, message: str, level: str = "info", console: bool = True, force_console: bool = False):
        """
        Logs a message at the specified level and optionally to the console.

        :param message: The log message.
        :param level: Log level ("info", "debug", "warning", "error", "critical").
        :param console: Whether to log to the QTextEdit console.
        :param force_console: Force the message to appear in instance console even when handler level is restrictive.
        """
        if force_console:
            console = True

        # Temporarily detach the console handler if console logging is disabled
        if not console and hasattr(self, 'console_handler'):
            self.logger.removeHandler(self.console_handler)

        previous_console_level = None
        if force_console and hasattr(self, 'console_handler'):
            previous_console_level = self.console_handler.level
            self.console_handler.setLevel(logging.INFO)

        # Dynamically get the log method based on the level
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message)  # Perform the logging

        # Reattach the console handler if it was temporarily removed
        if not console and hasattr(self, 'console_handler'):
            self.logger.addHandler(self.console_handler)

        if previous_console_level is not None and hasattr(self, 'console_handler'):
            self.console_handler.setLevel(previous_console_level)


    def validate_run(self):
        """
        Validates the emulator environment before running operations.
        Checks device connection and screen resolution.
        """
        # Check if the device is connected
        if not self.adb_manager.device:
            error_message = f"No device found on port {self.port}"
            self.log_message(error_message,"error")
            if self.index == 999:
                self.scan_general_console.emit(error_message)
                self.scan_general_error.emit()
            elif self.index == 998:
                # For template operations, show error in dialog
                self.error.emit(self.index, error_message)
            else:
                self.error.emit(self.index, error_message)
            return False

        # Validate screen resolution
        resolution = self.adb_manager.get_screen_resolution()
        if resolution is None:
            self.adb_manager.connect_to_device()
            resolution = self.adb_manager.get_screen_resolution()

        if resolution is None:
            error_message = f"Unable to read screen resolution from device on port {self.port}. Please ensure emulator is running and ADB is connected."
            self.log_message(error_message, "error")
            if self.adb_manager.last_resolution_debug:
                self.log_message(f"Resolution diagnostics: {self.adb_manager.last_resolution_debug}", "error")
            if self.index == 999:
                self.scan_general_console.emit(error_message)
                self.scan_general_error.emit()
            elif self.index == 998:
                # For template operations, show error in dialog
                self.error.emit(self.index, error_message)
            else:
                self.error.emit(self.index, error_message)
            return False

        self.log_message(
            f"Detected screen resolution on port {self.port}: {resolution[0]}x{resolution[1]}",
            "info"
        )

        # print(resolution)
        if resolution != (540, 960) and resolution != (960, 540):
            error_message = (
                f"Unsupported screen resolution: {resolution[0]}x{resolution[1]}. "
                f"Expected: 540x960 (or 960x540). "
                f"Changing emulator window size on desktop does not change device resolution; set it in emulator display settings."
            )
            self.logger.error(error_message)
            self.error.emit(self.index, error_message)
            return False

        self.log_message("Validation passed. Device is now connected.", "info", force_console=True)
        return True

    def run(self):
        """
        Code to be executed when the thread starts. Runs in a separate thread.
        """
        try:
            if not self.validate_run():
                self._running = False
                return

            # Perform the operation based on the type
            if self.operation_type == "emu":
                self.game_settings = get_game_settings_controls(self.main_window,self.index)
                self.run_emulator_instance()
            elif self.operation_type == "scan_general":
                start_scan_generals(self)
            elif self.operation_type == "capture_template_ss":
                capture_template_ss(self)
            elif self.operation_type == "generate_template_image":
                generate_template_image(self)
            elif self.operation_type == "simulate_monster_click":
                start_simulate_monster_click(self)

        except Exception as e:
            tb = traceback.format_exc()
            self.log_message(f"Thread Run : {e}", level="error", console=False)
            self.log_message(f"Thread Run Traceback:\n{tb}", level="error", force_console=True)
            self.error.emit(self.index, str(e))
        finally:
            self.finished.emit(self.index, self._running)
            self.stop()

    def stop(self):
        """
        Stops the thread safely.
        """
        if self._running:
            self._running = False
            self.adb_manager.disconnect_device()
            self.cache = {}
            self.logger.info("Thread stopped and disconnected.")

    def thread_status(self):
        return self._running

    def run_emulator_instance(self):
        """
        Runs all enabled features in a single orchestrator loop.
        """
        while self.thread_status():
            try:
                feature_controls = get_all_feature_controls(self.main_window, self.index)

                auto_bubble = feature_controls.get('auto_bubble', {})
                auto_gather = feature_controls.get('auto_gather', {})
                join_rally = feature_controls.get('join_rally', {})

                if auto_bubble.get('enabled', False):
                    run_auto_bubble_check(self)

                if auto_gather.get('enabled', False):
                    run_auto_gather_cycle(self)

                # Join Rally has no explicit enabled toggle yet; run only when any data exists.
                if join_rally.get('data'):
                    run_join_rally_scan_pass(self)

                time.sleep(1)
            except Exception as e:
                tb = traceback.format_exc()
                self.log_message(f"Orchestrator loop error: {e}", level="warning", force_console=True)
                self.log_message(f"Orchestrator loop traceback:\n{tb}", level="debug", force_console=False)
                time.sleep(1)

    def capture_and_validate_screen(self,kick_timer=True, ads=True):
        try:
            src_img = self.adb_manager.take_screenshot()
            restart_img = cv2.imread("assets/540p/other/restart_btn.png")
            world_map_btn = cv2.imread("assets/540p/other/explore_world_map_btn.png")
            if kick_timer and is_template_match(src_img, restart_img):
                # print("kick timer activated")
                self.logger.info(f"Kick & Reload activated for {self.game_settings['kick_reload']} min(s)")
                time.sleep(self.game_settings['kick_reload'] * 60)
                # print("kick timer done")
                self.logger.info("Kick timer done. Restart initiated")
                # Restart the game
                src_img = self.adb_manager.take_screenshot()
                restart = template_match_coordinates(src_img, restart_img)
                if restart:
                    self.adb_manager.tap(restart[0], restart[1])
                    time.sleep(7)
                    src_img = self.adb_manager.take_screenshot()
                else:
                    # When restart button is gone, restart the game by starting it again
                    self.adb_manager.launch_evony(False)
                    time.sleep(1)
                    self.adb_manager.launch_evony(True)
                start_time = time.time()
                timeout = 60
                while not is_template_match(src_img, world_map_btn):
                    # Wait a bit before the next screenshot to reduce CPU usage
                    time.sleep(1)
                    # Check if the timeout has been reached
                    elapsed_time = time.time() - start_time
                    if elapsed_time > timeout:
                        # print("Game stuck in loading screen. Restarting...")
                        self.logger.info("Game stuck in loading screen. Restarting...")
                        self.adb_manager.launch_evony(False)  # Close the game
                        time.sleep(1)  # Wait for a few seconds before relaunching
                        self.adb_manager.launch_evony(True)  # Relaunch the game
                        start_time = time.time()  # Reset the start time after relaunching

                    # print("Still loading")
                    # Capture the new image
                    src_img = self.adb_manager.take_screenshot()

            if ads:
                for i in range(1, 7):
                    ads_img = cv2.imread(f"assets/540p/other/x{i}.png")
                    if is_template_match(src_img, ads_img):
                        if i == 6:
                            pair_image = cv2.imread(f"assets/540p/other/x{i}_pair.png")
                            if not is_template_match(src_img, pair_image):
                                continue
                        # print("Ads found")
                        self.logger.info("Closing the ads/pop-ups")
                        ads_match = template_match_coordinates(src_img, ads_img)
                        if not ads_match:
                            self.logger.debug(f"Ad close template x{i} matched but tap coordinates were not found.")
                            continue

                        self.adb_manager.tap(ads_match[0], ads_match[1])
                        time.sleep(1)
                        src_img = self.adb_manager.take_screenshot()
                        break
            return src_img
        except Exception as e:
            try:
                self.logger.warning(f"capture_and_validate_screen error: {e}")
            except Exception:
                pass
            return None



