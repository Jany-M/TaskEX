import ctypes
import os
import re
import shutil
from datetime import timedelta, datetime


def _log_capture_debug(message: str) -> None:
    try:
        with open("capture_debug.log", "a", encoding="utf-8", errors="replace") as f:
            f.write(f"{message}\n")
    except Exception:
        # Avoid raising logging errors during capture flow
        pass


def extract_number_from_string(string: str) -> int:
    """
    Extracts all integers from the given string, combines them, and returns
    the result as a single integer.

    Args:
        string (str): The input string containing numbers and other characters.

    Returns:
        int: A single integer formed by combining all the numbers found in the string.
        Returns 0 if no numbers are found.
    """
    matches = re.findall(r'\d+', string)
    if matches:
        # Combine all the number matches as strings and convert to an integer
        combined_number = int(''.join(matches))
        return combined_number
    else:
        return 0  # Return 0 if no numbers are found

def crop_bottom_half(image):
    # Get the size of the image
    width, height = image.shape[:-1]
    # Define the points for cropping
    start_row, start_col = int(height * .5), int(0)
    end_row, end_col = int(height), int(width)
    # Crop the image
    cropped_img = image[start_row:end_row, start_col:end_col].copy()
    return cropped_img


def copy_image_to_preview(file, file_name):
    if not file or not file_name:
        _log_capture_debug("[WARN] copy_image_to_preview: missing file or file_name")
        return

    # Get the preview folder path
    preview_path = os.path.join('assets', 'preview')

    # Define the new destination path for the file
    destination_path = os.path.join(preview_path, file_name)
    try:
        src = os.path.abspath(str(file))
        dst = os.path.abspath(destination_path)

        _log_capture_debug(f"[DEBUG] copy_image_to_preview src={src} dst={dst}")

        if not os.path.exists(src):
            _log_capture_debug("[WARN] copy_image_to_preview: source does not exist")
            return

        if os.path.normcase(os.path.normpath(src)) == os.path.normcase(os.path.normpath(dst)):
            _log_capture_debug("[INFO] copy_image_to_preview: src and dst are the same")
            return

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        _log_capture_debug("[INFO] copy_image_to_preview: copy succeeded")
    except Exception as e:
        _log_capture_debug(f"[ERROR] copy_image_to_preview failed: {e}")

def copy_image_to_template(file, file_name):
    if not file or not file_name:
        _log_capture_debug("[WARN] copy_image_to_template: missing file or file_name")
        return

    # Get the template folder path
    template_path = os.path.join('assets', '540p', 'monsters')

    # Define the new destination path for the file
    destination_path = os.path.join(template_path, file_name)
    try:
        src = os.path.abspath(str(file))
        dst = os.path.abspath(destination_path)

        _log_capture_debug(f"[DEBUG] copy_image_to_template src={src} dst={dst}")

        if not os.path.exists(src):
            _log_capture_debug("[WARN] copy_image_to_template: source does not exist")
            return

        if os.path.normcase(os.path.normpath(src)) == os.path.normcase(os.path.normpath(dst)):
            _log_capture_debug("[INFO] copy_image_to_template: src and dst are the same")
            return

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        _log_capture_debug("[INFO] copy_image_to_template: copy succeeded")
    except Exception as e:
        _log_capture_debug(f"[ERROR] copy_image_to_template failed: {e}")

def get_screen_resolution():
    """Fetch the real screen resolution."""
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    return f"{screen_width}x{screen_height}"


def is_valid_timer_format(text):
    if not text or not isinstance(text, str):
        return False

    normalized = text.strip()

    # HH:MM:SS
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", normalized):
        hours, minutes, seconds = map(int, normalized.split(':'))
        return 0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59

    # MM:SS
    if re.fullmatch(r"\d{2}:\d{2}", normalized):
        minutes, seconds = map(int, normalized.split(':'))
        return 0 <= minutes <= 59 and 0 <= seconds <= 59

    return False


def parse_timer_to_timedelta(timer_text):
    """
    Convert timer text in the format 'HH:MM:SS' or 'MM:SS' to a timedelta object.
    Handles different cases like None, empty strings, or incorrect formats.
    """
    if not timer_text or not isinstance(timer_text, str):
        return None  # Return None if input is None or not a string

    if not is_valid_timer_format(timer_text.strip()):
        return None  # Return None if input is None or not a string

    parts = timer_text.split(":")

    try:
        # Handle different formats
        if len(parts) == 3:  # 'HH:MM:SS' format
            hours, minutes, seconds = map(int, parts)
        elif len(parts) == 2:  # 'MM:SS' format
            hours = 0
            minutes, seconds = map(int, parts)
        else:
            return None  # Return None for invalid format

        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except ValueError:
        return None  # Return None if conversion to int fails

def get_current_datetime_string():
    """
    Returns the current datetime as a formatted string.
    """
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
