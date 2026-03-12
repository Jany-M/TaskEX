"""
Auto-Bubble Logic
=================
Two separate workflows:

1. TIMER CHECK (periodic / startup):
   - Opens City Buff screen
   - Reads Truce Agreement timer from green bar region
   - Closes back to HUD
   - Returns: remaining minutes or None

2. BUBBLE USE (when threshold met):
   - Opens City Buff screen
   - Opens Use Item screen (bubble list)
   - Selects configured bubble type
   - Activates it
   - Closes back to HUD

These workflows are independent. Timer check NEVER navigates to Use Item.
Bubble use ONLY activates if timer check confirms threshold is met.

Preferred navigation assets:
    assets/540p/bubbles/use_btn.png               - row action "Use" button
    assets/540p/dialogs/use_btn.png               - generic dialog confirm button
    assets/540p/dialogs/cancel_btn.png            - generic dialog cancel button

The Use Item screen bubble order (when needed) is fixed:
    row 1 = 8h, row 2 = 24h, row 3 = 3d, row 4 = 7d
"""

import re
import time
import traceback
from datetime import datetime, timedelta

import cv2

from utils.navigate_utils import (
    navigate_to_bubble_use,
    open_bubble_status_panel,
    press_back_with_exit_guard,
    tap_back_button_full_screen,
)
from utils.get_controls_info import get_auto_bubble_controls


CITY_BUFF_BACK_ICON_COORDS = (35, 30)


def reset_auto_bubble_state(thread, reason=""):
    """Clear cached bubble-expiration state so next check re-reads timer from screen."""
    thread.cache['auto_bubble_state'] = {}
    if reason:
        thread.log_message(
            f"[Auto-Bubble] Cached timer state reset ({reason}).",
            "debug",
            force_console=False,
        )


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

    # Avoid permissive number-only parsing; OCR noise from non-bubble screens
    # can contain random digits and produce false large timers.
    return None


def _normalize_ocr_text(text):
    return re.sub(r'[^a-z0-9: ]+', ' ', (text or '').lower())


def _extract_top_title_text(panel_img):
    if panel_img is None or panel_img.size == 0:
        return ""

    try:
        from pytesseract import pytesseract

        img_h, img_w = panel_img.shape[:2]
        x1 = int(img_w * 0.0)
        y1 = int(img_h * 0.0)
        x2 = int(img_w * 1.0)
        y2 = int(img_h * 0.08)
        title_roi = panel_img[y1:y2, x1:x2]

        if title_roi is None or title_roi.size == 0:
            return ""

        gray = cv2.cvtColor(title_roi, cv2.COLOR_BGR2GRAY)
        enlarged = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        text = pytesseract.image_to_string(enlarged, config='--psm 6').strip().lower()
        return text
    except Exception:
        return ""


def _is_city_buff_screen(panel_img):
    """
    Validate that the panel image is actually the City Buff screen, not Use Item or other screen.
    
    Checks for:
    - Presence of "City Buff" text OR
    - Absence of "Use Item" text (to catch when we accidentally opened bubble selection list)
    
    Returns True if City Buff is detected, False if Use Item is detected.
    """
    if panel_img is None or panel_img.size == 0:
        return False

    try:
        text = _extract_top_title_text(panel_img)

        # If we see "Use Item", we're on the WRONG screen (bubble selection, not City Buff)
        if 'use item' in text or ('use' in text and 'item' in text):
            return False

        # If we see "City Buff", we're on the RIGHT screen
        if 'city buff' in text or ('city' in text and 'buff' in text):
            return True

        # If we see neither, it might be some other screen -- be cautious
        return False

    except Exception:
        # On OCR error, fail conservative
        return False


def _is_use_item_screen(panel_img):
    text = _extract_top_title_text(panel_img)
    return 'use item' in text or ('use' in text and 'item' in text)


def _capture_screen_for_retreat_check(thread):
    try:
        return thread.capture_and_validate_screen(ads=False)
    except TypeError:
        try:
            return thread.capture_and_validate_screen()
        except Exception:
            return None
    except Exception:
        return None


def _retreat_from_city_buff_timer_check(thread):
    """
    Leave City Buff/Use Item panels after timer check.
    Always target the top-left circular back icon; if still on panel, retry.
    """
    for attempt in range(2):
        tapped = tap_back_button_full_screen(thread, back_icon_coords=CITY_BUFF_BACK_ICON_COORDS)
        if not tapped:
            break

        time.sleep(0.35)
        screen = _capture_screen_for_retreat_check(thread)
        if screen is None:
            return True

        if not _is_city_buff_screen(screen) and not _is_use_item_screen(screen):
            return True

        thread.log_message(
            f"[Auto-Bubble] Retreat check: still on City Buff/Use Item after back tap (attempt {attempt + 1}).",
            "warning",
            force_console=True,
        )

    return press_back_with_exit_guard(thread)


def _read_truce_agreement_status(panel_img):
    """
    Read the Truce Agreement card from the City Buff screen.

    Returns a dict with:
      - found: whether the Truce Agreement section was detected
      - active: whether a timer is visible on that section
      - remaining_minutes: parsed timer in minutes, when active
      - ocr_text: OCR text used for debugging
    """
    if panel_img is None or panel_img.size == 0:
        return {
            'found': False,
            'active': False,
            'remaining_minutes': None,
            'ocr_text': 'ERROR: panel_img is None',
        }

    try:
        img_h, img_w = panel_img.shape[:2]
    except Exception:
        return {
            'found': False,
            'active': False,
            'remaining_minutes': None,
            'ocr_text': 'ERROR: Cannot get image dimensions',
        }

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
            'ocr_text': 'ERROR: ROI extraction failed',
        }

    try:
        from pytesseract import pytesseract

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        enlarged = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        text = pytesseract.image_to_string(enlarged, config='--psm 6').strip()
        normalized = _normalize_ocr_text(text)

        found = 'truce agreement' in normalized or ('truce' in normalized and 'agreement' in normalized)
    except Exception:
        found = False
        text = ''

    # Read the green timer bar region directly.
    # Coordinates confirmed from City Buff screen (540x960): x=140-460, y=168-205
    tx1 = int(img_w * 0.259)
    ty1 = int(img_h * 0.175)
    tx2 = int(img_w * 0.852)
    ty2 = int(img_h * 0.214)
    timer_roi = panel_img[ty1:ty2, tx1:tx2]

    timer_text = ""
    remaining_minutes = None
    if timer_roi is not None and timer_roi.size > 0:
        try:
            from pytesseract import pytesseract

            timer_gray = cv2.cvtColor(timer_roi, cv2.COLOR_BGR2GRAY)
            timer_up = cv2.resize(timer_gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            # Simple threshold works best: white text on green background
            _, timer_bin = cv2.threshold(timer_up, 160, 255, cv2.THRESH_BINARY)

            # Save debug image of timer bar for analysis
            try:
                cv2.imwrite(f"_dev/debug_timer_bar_{int(time.time())}.png", timer_roi)
                cv2.imwrite(f"_dev/debug_timer_bar_thresh_{int(time.time())}.png", timer_bin)
            except Exception:
                pass

            configs = [
                '--psm 7 -c tessedit_char_whitelist=0123456789:',
                '--psm 6 -c tessedit_char_whitelist=0123456789:',
            ]
            candidates = []
            for cfg in configs:
                try:
                    candidates.append(pytesseract.image_to_string(timer_bin, config=cfg).strip())
                    candidates.append(pytesseract.image_to_string(timer_up, config=cfg).strip())
                except Exception:
                    pass

            for candidate in candidates:
                parsed = _parse_remaining_minutes(candidate)
                if parsed is not None:
                    timer_text = candidate
                    remaining_minutes = parsed
                    break
        except Exception:
            pass

    # Fallback to card-wide OCR parse only if timer bar read failed.
    if remaining_minutes is None and found:
        remaining_minutes = _parse_remaining_minutes(text)

    return {
        'found': found,
        'active': found and remaining_minutes is not None,
        'remaining_minutes': remaining_minutes,
        'ocr_text': timer_text or text,
    }


def _refresh_bubble_expiration_state(thread, conservative=False):
    """
    TIMER CHECK workflow: Read Truce Agreement expiry from City Buff ONLY.
    
    This function is for READING the timer, not for using/activating bubbles.
    It must NEVER navigate to the Use Item screen.
    
    Steps:
      1. Open City Buff panel from HUD
      2. Validate we're on City Buff, not Use Item
      3. Read Truce Agreement timer from green bar region
      4. Close back to HUD
      5. Cache the expiry timestamp
      
    If any step fails or wrong screen detected, retreat immediately.
    
    Returns the cached state dict or None on failure.
    """
    panel_img = open_bubble_status_panel(thread, conservative=conservative)
    if panel_img is None:
        thread.log_message(
            "[Auto-Bubble] open_bubble_status_panel returned None; panel is inaccessible.",
            "warning",
            force_console=True,
        )
        return None

    # **CRITICAL**: Validate we're on City Buff, not Use Item or other screen.
    # If we somehow ended up on the wrong screen, retreat immediately WITHOUT reading.
    is_valid_city_buff = _is_city_buff_screen(panel_img)
    thread.log_message(
        f"[Auto-Bubble] Screen validation: City Buff={is_valid_city_buff}",
        "info",
        force_console=True,
    )
    if not is_valid_city_buff:
        # Save debug screenshot for analysis
        try:
            debug_path = f"_dev/debug_bubble_wrong_screen_{int(time.time())}.png"
            cv2.imwrite(debug_path, panel_img)
            thread.log_message(
                f"[Auto-Bubble] **ALERT**: Wrong screen detected. Debug screenshot saved to {debug_path}",
                "warning",
                force_console=True,
            )
        except Exception as e:
            thread.log_message(
                f"[Auto-Bubble] Failed to save debug screenshot: {e}",
                "warning",
                force_console=False,
            )
        thread.log_message(
            "[Auto-Bubble] **ALERT**: Failed to validate City Buff screen. Retreating immediately WITHOUT reading timer.",
            "warning",
            force_console=True,
        )
        _retreat_from_city_buff_timer_check(thread)
        time.sleep(0.3)
        return None

    # Read Truce Agreement timer from City Buff screen only.
    status = _read_truce_agreement_status(panel_img)
    
    thread.log_message(
        f"[Auto-Bubble] [City Buff] Truce Agreement found={status.get('found')} | Timer active={status.get('active')} | Remaining={status.get('remaining_minutes', 'N/A')} min",
        "debug",
        force_console=False,
    )

    # Retreat from City Buff; prefer the in-game top-left back icon to avoid triggering Android exit prompt.
    _retreat_from_city_buff_timer_check(thread)
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


def _read_bubble_timer(thread, conservative=False):
    """
    TIMER CHECK ONLY: Read remaining Truce Agreement time from City Buff green bar.
    
    This is strictly for determining if the bubble timer needs renewal.
    Does NOT interact with the Use Item screen or perform any activation.
    
    Returns remaining time in minutes (int), or None when:
      - the screen cannot be read
      - Truce Agreement cannot be interpreted reliably
    """
    try:
        state = _refresh_bubble_expiration_state(thread, conservative=conservative)
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
            return None

        if not state.get('truce_found'):
            return None

        return int(state.get('remaining_minutes')) if state.get('remaining_minutes') is not None else None

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        thread.log_message(
            f"[Auto-Bubble] Timer read error: {e}\n{error_trace}", "debug", force_console=False
        )
        return None


def _run_timer_check_path(thread, controls, force_refresh=False):
    """
    TIMER CHECK PATH (read-only):
      - open City Buff
      - read timer
      - back out from City Buff
    Never enters Use Item.
    """
    state = thread.cache.setdefault('auto_bubble_state', {})

    remaining_mins = None if force_refresh else _get_cached_remaining_minutes(thread, controls)
    if remaining_mins is not None:
        state['last_check_source'] = 'cache'
    else:
        remaining_mins = _read_bubble_timer(thread, conservative=force_refresh)
        state['last_check_source'] = 'screen' if remaining_mins is not None else 'unavailable'

    if remaining_mins is None:
        # Timer could not be read reliably. Back off to avoid rapid City Buff open/close loops.
        state['next_retry_ts'] = time.time() + 45
        thread.log_message(
            "[Auto-Bubble] [Timer Check Path] Remaining timer unavailable; retrying in ~45s.",
            "warning", force_console=True,
        )
        return None

    # Successful read: clear retry backoff.
    state.pop('next_retry_ts', None)
    return remaining_mins


def _run_renewal_path_if_needed(thread, controls, remaining_mins):
    """
    RENEWAL PATH (write/action):
      - threshold check
      - if due, enter Use Item and activate configured bubble
    """
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
        thread.log_message(
            "[Auto-Bubble] [Renewal Path] Threshold not met; skip Use Item navigation.",
            "debug", force_console=False,
        )
        return False

    thread.log_message(
        f"[Auto-Bubble] [Renewal Path] Threshold met "
        f"({remaining_mins} ≤ {trigger_mins} min). Entering Use Item to activate bubble…",
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


def run_auto_bubble_check(thread, force_refresh=False):
    """
    One auto-bubble check pass (called by the multi-feature orchestrator).

    STEP 1 (TIMER CHECK PATH): Read-only flow in City Buff (never enters Use Item).
    STEP 2 (RENEWAL PATH IF NEEDED): Only when threshold is met, enter Use Item and activate.

    Returns True if a bubble activation was attempted, False otherwise.
    """
    try:
        controls = get_auto_bubble_controls(thread.main_window, thread.index)
        if not controls.get('enabled', False):
            return False

        state = thread.cache.setdefault('auto_bubble_state', {})

        # Skip until the next scheduled check window (idle when timer is far from threshold)
        if not force_refresh:
            next_sched = state.get('next_scheduled_check_ts')
            if next_sched and time.time() < next_sched:
                return False

        next_retry_ts = state.get('next_retry_ts')
        if next_retry_ts and time.time() < next_retry_ts and not force_refresh:
            return False

        remaining_mins = _run_timer_check_path(thread, controls, force_refresh=force_refresh)
        if remaining_mins is None:
            return False

        trigger_mins = int(controls.get('trigger_minutes', 60))
        expires_at_ts = state.get('expires_at_ts')

        # If bubble is active and not yet at threshold, sleep exactly until the
        # threshold time (expires_at minus trigger window, with 60s safety buffer).
        if remaining_mins > trigger_mins and expires_at_ts:
            wakeup_ts = expires_at_ts - (trigger_mins * 60) - 60
            if wakeup_ts > time.time():
                state['next_scheduled_check_ts'] = wakeup_ts
                wakeup_str = datetime.fromtimestamp(wakeup_ts).strftime('%H:%M:%S')
                thread.log_message(
                    f"[Auto-Bubble] Bubble active ({remaining_mins} min left, "
                    f"threshold {trigger_mins} min). Next check at {wakeup_str}.",
                    "info", force_console=True,
                )
                return False
        else:
            state.pop('next_scheduled_check_ts', None)

        source = state.get('last_check_source', 'unknown')
        if source == 'screen':
            thread.log_message("[Auto-Bubble] Check started", "info", force_console=True)
        thread.log_message(
            f"[Auto-Bubble] Checked - Time until renewal: {remaining_mins} min",
            "info", force_console=True,
        )

        return _run_renewal_path_if_needed(thread, controls, remaining_mins)

    except Exception as e:
        thread.log_message(
            f"[Auto-Bubble] Unexpected error: {e}", "warning", force_console=True
        )
        thread.log_message(traceback.format_exc(), "debug", force_console=False)
        return False
