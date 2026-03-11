"""
Auto-Bubble Logic
=================
Runs one protection-bubble check pass per orchestrator cycle.
Opens the top-left City Buff screen, reads the Truce Agreement timer there,
compares it against the configured threshold, and uses navigation helpers
to activate the chosen bubble if needed.

Preferred navigation assets:
    assets/540p/bubbles/use_btn.png               - row action "Use" button
    assets/540p/dialogs/use_btn.png               - generic dialog confirm button
    assets/540p/dialogs/cancel_btn.png            - generic dialog cancel button

Bubble row selection does not require per-bubble DB templates on 540p.
The Use Item screen order is treated as fixed:
    row 1 = 8h, row 2 = 24h, row 3 = 3d, row 4 = 7d

Legacy fallback templates still supported:
    assets/540p/bubbles/items_btn.png
    assets/540p/bubbles/protection_tab.png
"""

import re
import time
import traceback
from datetime import datetime, timedelta

import cv2

from utils.navigate_utils import navigate_to_bubble_use, open_bubble_status_panel
from utils.get_controls_info import get_auto_bubble_controls


def _parse_remaining_minutes(text):
    text = (text or "").lower().strip()
    if not text:
        return None

    compact = re.sub(r'\s+', ' ', text)

    day_match = re.search(r'(\d+)\s*d[a-z]*\s*(\d{1,2})[:h]\s*(\d{1,2})', compact)
    if day_match:
        days = int(day_match.group(1))
        hours = int(day_match.group(2))
        minutes = int(day_match.group(3))
        return days * 1440 + hours * 60 + minutes

    hms_match = re.search(r'(\d{1,3})\s*[:h]\s*(\d{1,2})(?:\s*[:m]\s*(\d{1,2}))?', compact)
    if hms_match:
        hours = int(hms_match.group(1))
        minutes = int(hms_match.group(2))
        return hours * 60 + minutes

    nums = [int(n) for n in re.findall(r'\d+', compact)]
    if len(nums) >= 3:
        return nums[0] * 1440 + nums[1] * 60 + nums[2]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 1:
        return nums[0]
    return None


def _normalize_ocr_text(text):
    return re.sub(r'[^a-z0-9: ]+', ' ', (text or '').lower())


def _read_truce_agreement_status(panel_img):
    """
    Read the Truce Agreement card from the City Buff screen.

    Returns a dict with:
      - found: whether the Truce Agreement section was detected
      - active: whether a timer is visible on that section
      - remaining_minutes: parsed timer in minutes, when active
      - ocr_text: OCR text used for debugging
    """
    img_h, img_w = panel_img.shape[:2]

    # City Buff puts Truce Agreement in the first card under the title bar.
    x1 = int(img_w * 0.02)
    y1 = int(img_h * 0.07)
    x2 = int(img_w * 0.97)
    y2 = int(img_h * 0.23)
    roi = panel_img[y1:y2, x1:x2]

    if roi is None or roi.size == 0:
        return {
            'found': False,
            'active': False,
            'remaining_minutes': None,
            'ocr_text': '',
        }

    from pytesseract import pytesseract

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    enlarged = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    text = pytesseract.image_to_string(enlarged, config='--psm 6').strip()
    normalized = _normalize_ocr_text(text)

    found = 'truce agreement' in normalized or ('truce' in normalized and 'agreement' in normalized)
    remaining_minutes = _parse_remaining_minutes(text)

    return {
        'found': found,
        'active': remaining_minutes is not None,
        'remaining_minutes': remaining_minutes,
        'ocr_text': text,
    }


def _refresh_bubble_expiration_state(thread):
    """Open City Buff, read Truce Agreement, and cache absolute expiry state."""
    panel_img = open_bubble_status_panel(thread)
    if panel_img is None:
        return None

    status = _read_truce_agreement_status(panel_img)
    thread.adb_manager.press_back()
    time.sleep(0.3)

    state = thread.cache.setdefault('auto_bubble_state', {})
    now = datetime.now()

    state['last_check_at'] = now.isoformat()
    state['truce_found'] = bool(status.get('found'))
    state['ocr_text'] = status.get('ocr_text', '')

    if status.get('active'):
        remaining_minutes = int(status['remaining_minutes'])
        expires_at = now + timedelta(minutes=remaining_minutes)
        state['active'] = True
        state['remaining_minutes'] = remaining_minutes
        state['expires_at'] = expires_at.isoformat()
        state['expires_at_ts'] = expires_at.timestamp()
    else:
        state['active'] = False
        state['remaining_minutes'] = 0
        state['expires_at'] = None
        state['expires_at_ts'] = None

    return state


def _get_cached_remaining_minutes(thread, controls):
    state = thread.cache.setdefault('auto_bubble_state', {})
    expires_at_ts = state.get('expires_at_ts')
    trigger_mins = int(controls.get('trigger_minutes', 60))

    if not expires_at_ts:
        return None

    remaining_seconds = max(0, expires_at_ts - time.time())
    remaining_minutes = int(remaining_seconds // 60)

    # Re-read from the screen when close to threshold so the bot does not drift.
    if remaining_minutes <= trigger_mins + 5:
        return None

    state['remaining_minutes'] = remaining_minutes
    return remaining_minutes


def _read_bubble_timer(thread):
    """
    Read and cache the Truce Agreement expiry from the City Buff screen.

    Returns remaining time in minutes (int), or None when:
      - the screen cannot be read
      - Truce Agreement cannot be interpreted reliably
    """
    try:
        state = _refresh_bubble_expiration_state(thread)
        if state is None:
            return None

        if not state.get('truce_found'):
            thread.log_message(
                f"[Auto-Bubble] Truce Agreement section not detected. OCR: {state.get('ocr_text', '')}",
                "debug", force_console=False,
            )
        elif not state.get('active'):
            thread.log_message(
                "[Auto-Bubble] Truce Agreement found with no visible timer; treating bubble as inactive.",
                "debug", force_console=False,
            )

        return int(state.get('remaining_minutes', 0))

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

        remaining_mins = _get_cached_remaining_minutes(thread, controls)
        if remaining_mins is None:
            remaining_mins = _read_bubble_timer(thread)
        if remaining_mins is None:
            remaining_mins = 0

        trigger_mins = controls.get('trigger_minutes', 60)
        state = thread.cache.get('auto_bubble_state', {})
        expires_at = state.get('expires_at')
        thread.log_message(
            f"[Auto-Bubble] Remaining: {remaining_mins} min  "
            f"| Trigger threshold: {trigger_mins} min"
            f" | Expires at: {expires_at or 'not active'}",
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
            # Force a fresh Truce Agreement timer read next cycle after using a bubble.
            thread.cache['auto_bubble_state'] = {}
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
