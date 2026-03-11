"""
Auto-Bubble Logic
=================
Runs one protection-bubble check pass per orchestrator cycle.
Reads the HUD timer, compares against the configured threshold, and
uses navigation helpers to activate the chosen bubble if needed.

Navigation templates required (upload via "Configure Bubble Templates"):
  assets/540p/bubbles/bubble_timer_icon.png  - HUD bubble timer icon
  assets/540p/bubbles/items_btn.png          - in-city Items / Inventory button
  assets/540p/bubbles/protection_tab.png     - Protection category tab
  assets/540p/bubbles/use_btn.png            - "Use" confirm button
  + per-BubbleType template configured in the DB via BubbleConfigDialog
"""

import re
import time
import traceback

import cv2

from utils.navigate_utils import navigate_to_bubble_use
from utils.get_controls_info import get_auto_bubble_controls


def _read_bubble_timer(thread):
    """
    Attempt to read the remaining bubble protection time from the HUD.

    Returns remaining time in minutes (int), or None when:
      - the timer icon template is missing
      - the icon is not visible on screen (no bubble active)
      - OCR fails to parse a numeric value
    """
    try:
        from utils.image_recognition_utils import template_match_coordinates

        timer_icon_img = cv2.imread('assets/540p/bubbles/bubble_timer_icon.png')
        if timer_icon_img is None:
            thread.log_message(
                "[Auto-Bubble] Timer icon template missing "
                "('assets/540p/bubbles/bubble_timer_icon.png'). "
                "Upload via 'Configure Bubble Templates'.",
                "debug", force_console=False,
            )
            return None

        src_img = thread.capture_and_validate_screen(ads=False)
        if src_img is None:
            return None

        match = template_match_coordinates(src_img, timer_icon_img, threshold=0.80)
        if not match:
            return None  # no bubble timer visible → treat as 0

        # Crop the number region to the right of the icon
        icon_h, icon_w = timer_icon_img.shape[:2]
        img_h, img_w = src_img.shape[:2]
        x1 = min(match[0] + icon_w // 2, img_w - 1)
        y1 = max(match[1] - icon_h, 0)
        x2 = min(match[0] + icon_w * 6, img_w)
        y2 = min(match[1] + icon_h, img_h)
        roi = src_img[y1:y2, x1:x2]

        if roi is None or roi.size == 0:
            return None

        from pytesseract import pytesseract
        import numpy as np

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, config='--psm 7').strip()

        # Handles "3d 02:15:30", "25:30", "1:55" etc.
        # Extract all digit groups and interpret as d h m s
        nums = re.findall(r'\d+', text)
        if not nums:
            return None

        nums = [int(n) for n in nums]
        if len(nums) == 1:
            return nums[0]          # bare minutes
        if len(nums) == 2:
            return nums[0] * 60 + nums[1]   # h:mm
        if len(nums) == 3:
            return nums[0] * 60 + nums[1]   # h:mm:ss – ignore seconds
        if len(nums) >= 4:
            return nums[0] * 1440 + nums[1] * 60 + nums[2]   # d h:mm:ss

        return None

    except Exception as e:
        thread.log_message(
            f"[Auto-Bubble] Timer read error: {e}", "debug", force_console=False
        )
        return None


def run_auto_bubble_check(thread):
    """
    One auto-bubble check pass (called by the multi-feature orchestrator).

    Reads the remaining protection time; if it falls below the configured
    threshold, navigates the UI to activate the selected bubble.

    Returns True if a bubble activation was attempted, False otherwise.
    """
    try:
        controls = get_auto_bubble_controls(thread.main_window, thread.index)
        if not controls.get('enabled', False):
            return False

        remaining_mins = _read_bubble_timer(thread)
        if remaining_mins is None:
            remaining_mins = 0  # treat unreadable / missing as expired

        trigger_mins = controls.get('trigger_minutes', 60)
        thread.log_message(
            f"[Auto-Bubble] Remaining: {remaining_mins} min  "
            f"| Trigger threshold: {trigger_mins} min",
            "debug", force_console=False,
        )

        if remaining_mins > trigger_mins:
            return False  # still covered — skip

        thread.log_message(
            f"[Auto-Bubble] Threshold met "
            f"({remaining_mins} ≤ {trigger_mins} min). Activating bubble…",
            "info", force_console=True,
        )

        activated = navigate_to_bubble_use(thread, controls)
        if activated:
            thread.log_message(
                "[Auto-Bubble] Bubble activated successfully.",
                "info", force_console=True,
            )
        else:
            thread.log_message(
                "[Auto-Bubble] Bubble activation failed or templates not configured.",
                "warning", force_console=True,
            )
        return activated

    except Exception as e:
        thread.log_message(
            f"[Auto-Bubble] Unexpected error: {e}", "warning", force_console=True
        )
        thread.log_message(traceback.format_exc(), "debug", force_console=False)
        return False
