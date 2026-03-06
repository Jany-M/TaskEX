import os
import shutil
import subprocess
import re
import sys
from pathlib import Path
from typing import Optional

import adbutils
import cv2
import numpy as np


class ADBManager:
    _adb_executable_cache: Optional[str] = None

    def __init__(self, port: str):
        self.device = None
        self.port = port
        self.last_resolution_debug = ""
        self.connect_to_device()

    @classmethod
    def _resolve_adb_executable(cls) -> str:
        if cls._adb_executable_cache:
            return cls._adb_executable_cache

        executable_name = "adb.exe" if os.name == "nt" else "adb"
        candidates: list[Path] = []

        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).resolve().parent / "platform-tools" / executable_name)

        project_root = Path(__file__).resolve().parent.parent
        candidates.append(project_root / "platform-tools" / executable_name)

        for candidate in candidates:
            if candidate.exists():
                cls._adb_executable_cache = str(candidate)
                return cls._adb_executable_cache

        found = shutil.which("adb")
        cls._adb_executable_cache = found if found else "adb"
        return cls._adb_executable_cache

    @classmethod
    def _adb_command(cls, *args: str) -> list[str]:
        return [cls._resolve_adb_executable(), *args]

    @staticmethod
    def _parse_wm_size_output(output: str) -> Optional[tuple[int, int]]:
        if not output:
            return None

        physical_match = re.search(r"Physical\s+size:\s*(\d+)x(\d+)", output, flags=re.IGNORECASE)
        if physical_match:
            return int(physical_match.group(1)), int(physical_match.group(2))

        override_match = re.search(r"Override\s+size:\s*(\d+)x(\d+)", output, flags=re.IGNORECASE)
        if override_match:
            return int(override_match.group(1)), int(override_match.group(2))

        return None

    @staticmethod
    def initialize_adb() -> None:
        """
        Initialize the ADB environment: set the ADB path and start the ADB server.
        This function should be called when starting the bot.
        """
        adb_executable = ADBManager._resolve_adb_executable()
        adb_dir = os.path.dirname(adb_executable)

        if adb_dir and adb_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = adb_dir + os.pathsep + os.environ.get("PATH", "")

        try:
            # print("Starting ADB server...")
            subprocess.run(ADBManager._adb_command("start-server"), check=True)
            # print("ADB server started.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # print(f"Failed to start ADB server: {e}")
            raise RuntimeError(f"Failed to initialize ADB using '{adb_executable}': {e}") from e

    def connect_to_device(self) -> None:
        """
        Connect to an emulator using a specific port and store the device instance.
        """
        client: adbutils.AdbClient = adbutils.AdbClient()
        ip_address: str = f"127.0.0.1:{self.port}"

        try:
            # print(f"Connecting to emulator on port {self.port}...")
            result = subprocess.run(self._adb_command("connect", ip_address), capture_output=True, text=True)

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout,
                                                    stderr=result.stderr)

            # Now verify connection with adbutils
            if "connected to" in result.stdout.lower():
                # print(f"Connected to emulator on port {self.port}.")
                self.device: Optional[adbutils.AdbDevice] = client.device(serial=ip_address)
            else:
                # print(f"Failed to connect: {result.stdout}")
                self.device = None
        except subprocess.CalledProcessError as e:
            # print(f"Failed to connect to emulator on port {self.port}: {e.stderr}")

            self.device = None

    def disconnect_device(self) -> None:
        """
        Disconnect the connected device from ADB.
        """
        if self.device:
            ip_address = f"127.0.0.1:{self.port}"
            try:
                subprocess.run(self._adb_command("disconnect", ip_address), check=True)
                self.device = None
                # print(f"Disconnected device on port {self.port}.")
            except subprocess.CalledProcessError as e:
                # print(f"Failed to disconnect device on port {self.port}: {e}")
                pass
        else:
            # print("No device to disconnect.")
            pass

    def tap(self, x: int, y: int) -> None:
        """
        Perform a tap operation on the specified device at (x, y) coordinates.
        """
        if self.device:
            self.device.shell(f"input tap {x} {y}")
            # print(f"Tapped on device {self.device.serial} at ({x}, {y}).")
        else:
            # print("Device not connected or found.")
            pass

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 500) -> None:
        """
        Perform a swipe operation on the specified device from (x1, y1) to (x2, y2) over a duration (ms).
        """
        if self.device:
            self.device.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
            # print(f"Swiped on device {self.device.serial} from ({x1}, {y1}) to ({x2}, {y2}) over {duration} ms.")

    def take_screenshot(self) -> Optional[np.ndarray]:
        """
        Take a screenshot of the specified device and return the screenshot as a NumPy array.
        """
        if self.device:
            output = self.device.shell("screencap -p", encoding=None)

            if not output:
                return None

            # Convert the raw screenshot bytes into a NumPy array
            screenshot_np = np.frombuffer(output, dtype=np.uint8)

            if screenshot_np.size == 0:
                return None

            # Decode the NumPy array into an image using OpenCV
            try:
                screenshot_img = cv2.imdecode(screenshot_np, cv2.IMREAD_COLOR)
            except cv2.error:
                return None

            if screenshot_img is None:
                return None

            # Return the decoded screenshot image as a NumPy array
            return screenshot_img
        else:
            return None

    def press_back(self) -> None:
        """
        Perform a back button press operation on the specified device.
        """
        if self.device:
            self.device.shell("input keyevent KEYCODE_BACK")  # ADB command for back button
            # print(f"Back button pressed on device {self.device.serial}.")


    def launch_evony(self, start: bool = True) -> None:
        """
        Start or stop the Evony app on the connected device using adbutils.
        By default, it is configured to start the Evony app.

        :param start: True to start the app, False to stop the app.
        """
        package_name: str = "com.topgamesinc.evony"
        main_activity: str = "com.topgamesinc.androidplugin.UnityActivity"

        if self.device:
            if start:
                if main_activity:
                    # Start the app by launching the main activity
                    self.device.shell(f"am start -n {package_name}/{main_activity}")
                    # print(f"Started {package_name} with main activity {main_activity}.")
                else:
                    # print("Main activity is required to start the app.")
                    pass
            else:
                # Stop the app
                self.device.shell(f"am force-stop {package_name}")
                # print(f"Stopped {package_name}.")
        else:
            # print("Device not connected or found.")
            pass

    def get_screen_resolution(self) -> Optional[tuple[int, int]]:
        """
        Retrieve the screen resolution of the connected device.
        Returns:
            A tuple (width, height) if successful, otherwise None.
        """
        serial = f"127.0.0.1:{self.port}"
        debug_parts = []

        if not self.device:
            debug_parts.append("adbutils device handle: None")
        else:
            try:
                result = self.device.shell("wm size")
                parsed = self._parse_wm_size_output(result)
                debug_parts.append(f"adbutils wm size: {repr(result)}")
                if parsed:
                    self.last_resolution_debug = " | ".join(debug_parts)
                    return parsed
            except Exception as e:
                debug_parts.append(f"adbutils wm size error: {e}")
                if "closed" in str(e).lower():
                    self.device = None

        try:
            process = subprocess.run(
                self._adb_command("-s", serial, "shell", "wm", "size"),
                capture_output=True,
                text=True
            )
            debug_parts.append(f"adb shell wm size rc={process.returncode}")
            if process.stdout:
                debug_parts.append(f"adb shell wm size stdout: {repr(process.stdout.strip())}")
            if process.stderr:
                debug_parts.append(f"adb shell wm size stderr: {repr(process.stderr.strip())}")

            if process.returncode == 0:
                parsed = self._parse_wm_size_output(process.stdout)
                if parsed:
                    self.last_resolution_debug = " | ".join(debug_parts)
                    return parsed

            state_process = subprocess.run(
                self._adb_command("-s", serial, "get-state"),
                capture_output=True,
                text=True
            )
            debug_parts.append(
                f"adb get-state rc={state_process.returncode}, stdout={repr(state_process.stdout.strip())}, stderr={repr(state_process.stderr.strip())}"
            )

            devices_process = subprocess.run(
                self._adb_command("devices"),
                capture_output=True,
                text=True
            )
            if devices_process.stdout:
                serial_line = next(
                    (line.strip() for line in devices_process.stdout.splitlines() if serial in line),
                    "serial not listed"
                )
                debug_parts.append(f"adb devices entry: {serial_line}")
        except Exception as e:
            debug_parts.append(f"resolution diagnostics error: {e}")

        self.last_resolution_debug = " | ".join(debug_parts)
        print(f"Error retrieving screen resolution: {self.last_resolution_debug}")
        return None
