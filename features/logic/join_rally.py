
import time
import os
import re
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import timedelta

import cv2
import numpy as np
from pytesseract import pytesseract
from config.settings import get_strict_monster_match, get_debug_mode, get_assets_dir
from features.utils.join_rally_helper_utils import extract_monster_name_from_image, lookup_boss_by_name, normalize_boss_text
from utils.get_controls_info import get_join_rally_controls
from utils.helper_utils import parse_timer_to_timedelta, get_current_datetime_string
from utils.image_recognition_utils import is_template_match, draw_template_match, template_match_coordinates_all, \
    template_match_coordinates, detect_red_color
from utils.navigate_utils import navigate_join_rally_window, ensure_and_setup_pvp_war_window_screen, press_back_with_exit_guard
from utils.text_extraction_util import extract_remaining_rally_time_from_image, extract_join_rally_time_from_image, \
    extract_monster_power_from_image, extract_remaining_rally_time_text


AREA_PROFILES = {
    "join_war_button_fallback": (0.43, 0.88, 0.60, 0.98),
    "monster_text_ocr": (0.60, 0.15, 0.95, 0.29),
    "monster_text_ocr_fallback": (0.56, 0.13, 0.97, 0.33),
    # Tight timer-bar focused crop (Alliance War rally detail) to avoid power/coords noise.
    "remaining_time_ocr_timer_bar": (0.06, 0.28, 0.66, 0.44),
    "remaining_time_ocr_primary": (0.44, 0.12, 0.98, 0.40),
    "remaining_time_ocr_fallback": (0.34, 0.08, 0.99, 0.46),
    "march_confirm_search": (0.58, 0.84, 0.98, 0.985),
    "march_confirm_fallback": (0.72, 0.90, 0.96, 0.98),
    "stamina_prompt_text_ocr": (0.12, 0.24, 0.88, 0.72),
    "stamina_prompt_confirm_search": (0.48, 0.54, 0.95, 0.90),
    "stamina_use_button_search": (0.20, 0.78, 0.80, 0.98),
    "stamina_option_min": (0.22, 0.47, 0.38, 0.58),
    "stamina_option_max": (0.62, 0.47, 0.78, 0.58),
    "stamina_item_use_button_search": (0.62, 0.30, 0.98, 0.97),
    "stamina_item_use_min_fallback": (0.70, 0.40, 0.93, 0.50),
    "stamina_item_use_max_fallback": (0.70, 0.85, 0.93, 0.95),
    "no_marches_banner_ocr": (0.08, 0.28, 0.92, 0.48),
    "no_marches_banner_ocr_fallback": (0.05, 0.20, 0.95, 0.60),
}


NO_MARCHES_RETRY_COOLDOWN_SECONDS = 10
NO_RALLIES_RETRY_COOLDOWN_SECONDS = 20
NO_RALLIES_EMPTY_SWEEP_VIEWS = 5


def _resolve_asset_path(asset_path: str) -> str:
    normalized = str(asset_path).replace("\\", "/")
    if normalized.startswith("assets/"):
        normalized = normalized[len("assets/"):]
    return str(get_assets_dir() / normalized)


def _load_asset_template(asset_path: str, thread=None):
    resolved = _resolve_asset_path(asset_path)
    template = cv2.imread(resolved)
    if template is None and thread is not None:
        thread.log_message(
            f"Template not found or unreadable: {asset_path} (resolved: {resolved})",
            "warning",
            force_console=True,
        )
    return template


def _profile_bounds(screen, profile_name):
    h, w = screen.shape[:2]
    left_r, top_r, right_r, bottom_r = AREA_PROFILES[profile_name]
    x1 = max(0, min(w - 1, int(w * left_r)))
    y1 = max(0, min(h - 1, int(h * top_r)))
    x2 = max(x1 + 1, min(w, int(w * right_r)))
    y2 = max(y1 + 1, min(h, int(h * bottom_r)))
    return x1, y1, x2, y2


def _crop_profile(screen, profile_name):
    if screen is None or screen.size == 0:
        return None
    x1, y1, x2, y2 = _profile_bounds(screen, profile_name)
    roi = screen[y1:y2, x1:x2]
    if roi is None or roi.size == 0:
        return None
    return roi


def _profile_center(screen, profile_name):
    x1, y1, x2, y2 = _profile_bounds(screen, profile_name)
    return (x1 + x2) // 2, (y1 + y2) // 2


def _save_debug_frame(thread, label, frame=None):
    if not get_debug_mode():
        return

    try:
        debug_frame = frame
        if debug_frame is None:
            debug_frame = thread.capture_and_validate_screen(ads=False)

        if debug_frame is None or debug_frame.size == 0:
            return

        os.makedirs("temp", exist_ok=True)
        safe_label = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in str(label))
        file_path = os.path.join("temp", f"jr_{safe_label}_{get_current_datetime_string()}.png")
        cv2.imwrite(file_path, debug_frame)
    except Exception:
        pass


def _default_join_rally_controls():
    return {
        "data": [],
        "settings": {
            "enabled": True,
            "service_mode": "manual",
            "manual_running": False,
            "join_oldest_rallies_first": False,
            "selected_presets": {"presets": {}},
            "auto_use_stamina": {"enabled": False, "option": None},
            "march_speed_boost": {"enabled": False, "option": None},
        },
        "cache": {
            "skipped_monster_cords_img": [],
            "previous_preset_number": None,
            "no_marches_until_ts": 0,
            "no_rallies_until_ts": 0,
        },
    }


def _ensure_join_rally_controls(thread):
    controls = thread.cache.get('join_rally_controls')
    if not isinstance(controls, dict):
        controls = _default_join_rally_controls()

    try:
        latest_controls = get_join_rally_controls(thread.main_window, thread.index)
        if isinstance(latest_controls, dict):
            controls.update({k: v for k, v in latest_controls.items() if v is not None})
    except Exception as e:
        thread.log_message(
            f"Failed to read join rally controls, using safe defaults: {e}",
            "warning",
            force_console=True
        )

    controls.setdefault('settings', {})
    controls['settings'].setdefault('enabled', True)
    controls['settings'].setdefault('service_mode', 'manual')
    controls['settings'].setdefault('manual_running', False)
    controls['settings'].setdefault('join_oldest_rallies_first', False)
    controls['settings'].setdefault('selected_presets', {"presets": {}})
    controls['settings'].setdefault('auto_use_stamina', {"enabled": False, "option": None})
    controls['settings'].setdefault('march_speed_boost', {"enabled": False, "option": None})
    controls.setdefault('data', [])
    controls.setdefault('cache', {})
    controls['cache'].setdefault('skipped_monster_cords_img', [])
    controls['cache'].setdefault('previous_preset_number', None)
    controls['cache'].setdefault('no_marches_until_ts', 0)
    controls['cache'].setdefault('no_rallies_until_ts', 0)

    thread.cache['join_rally_controls'] = controls
    return controls


def _set_no_marches_cooldown(thread, seconds=NO_MARCHES_RETRY_COOLDOWN_SECONDS):
    controls = _ensure_join_rally_controls(thread)
    cache = controls.setdefault('cache', {})
    now = time.time()
    existing_until = float(cache.get('no_marches_until_ts') or 0)
    next_until = max(existing_until, now + max(1, int(seconds)))
    cache['no_marches_until_ts'] = next_until
    return max(0.0, next_until - now)


def _get_no_marches_cooldown_remaining(thread):
    controls = _ensure_join_rally_controls(thread)
    cache = controls.setdefault('cache', {})
    until_ts = float(cache.get('no_marches_until_ts') or 0)
    return max(0.0, until_ts - time.time())


def _is_no_marches_cooldown_active(thread, log=False):
    remaining = _get_no_marches_cooldown_remaining(thread)
    if remaining <= 0:
        return False

    if log:
        thread.log_message(
            f"No march slots available. Waiting {remaining:.1f}s before next rally join attempt.",
            "info",
            force_console=True
        )
    return True


def _set_no_rallies_cooldown(thread, seconds=NO_RALLIES_RETRY_COOLDOWN_SECONDS):
    controls = _ensure_join_rally_controls(thread)
    cache = controls.setdefault('cache', {})
    now = time.time()
    existing_until = float(cache.get('no_rallies_until_ts') or 0)
    next_until = max(existing_until, now + max(1, int(seconds)))
    cache['no_rallies_until_ts'] = next_until
    cache['no_rallies_rescan_required'] = True
    return max(0.0, next_until - now)


def _get_no_rallies_cooldown_remaining(thread):
    controls = _ensure_join_rally_controls(thread)
    cache = controls.setdefault('cache', {})
    until_ts = float(cache.get('no_rallies_until_ts') or 0)
    return max(0.0, until_ts - time.time())


def _is_no_rallies_cooldown_active(thread, log=False):
    remaining = _get_no_rallies_cooldown_remaining(thread)
    if remaining <= 0:
        return False

    if log:
        thread.log_message(
            f"[Join-Rally] Cooling off for {remaining:.1f}s before next rally scan.",
            "info",
            force_console=True
        )
    return True


def _normalize_ocr_for_phrase_match(text):
    return " ".join(re.sub(r'[^a-z]+', ' ', (text or '').lower()).split())


def _is_no_more_troops_text(text):
    normalized = _normalize_ocr_for_phrase_match(text)
    if not normalized:
        return False

    if "cannot send more troops" in normalized or "cant send more troops" in normalized:
        return True

    required_tokens = ("send", "more", "troops")
    return ("cannot" in normalized or "cant" in normalized) and all(token in normalized for token in required_tokens)


def _detect_no_more_troops_banner(thread, checks=3, delay_between_checks=0.45):
    for idx in range(max(1, int(checks))):
        screen = thread.capture_and_validate_screen(ads=False)
        _save_debug_frame(thread, f"no_marches_check_{idx + 1}", screen)
        if screen is None:
            if idx < checks - 1:
                time.sleep(delay_between_checks)
            continue

        for profile_name in ("no_marches_banner_ocr", "no_marches_banner_ocr_fallback"):
            roi = _crop_profile(screen, profile_name)
            if roi is None:
                continue

            try:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (3, 3), 0)
                upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                _, thresh = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                candidates = [
                    pytesseract.image_to_string(upscaled, config='--oem 3 --psm 7'),
                    pytesseract.image_to_string(thresh, config='--oem 3 --psm 7'),
                    pytesseract.image_to_string(thresh, config='--oem 3 --psm 6'),
                    pytesseract.image_to_string(thresh, config='--oem 3 --psm 11'),
                ]
            except Exception:
                candidates = []

            for candidate in candidates:
                if _is_no_more_troops_text(candidate):
                    thread.log_message(
                        f"No-marches banner detected from OCR: {_normalize_ocr_for_phrase_match(candidate)}",
                        "info",
                        force_console=True
                    )
                    return True

        if idx < checks - 1:
            time.sleep(delay_between_checks)

    return False


def _is_march_confirm_button_still_visible(screen):
    if screen is None:
        return False

    roi_x1, roi_y1, roi_x2, roi_y2 = _profile_bounds(screen, "march_confirm_search")
    if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
        return False

    roi = screen[roi_y1:roi_y2, roi_x1:roi_x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    lower_green = np.array([35, 55, 40], dtype=np.uint8)
    upper_green = np.array([95, 255, 255], dtype=np.uint8)
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    kernel = np.ones((5, 5), np.uint8)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, kernel)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = width * height
        if area < 1200 or height <= 0:
            continue
        if width / float(height) < 1.8:
            continue
        return True

    return False


def _classify_post_march_result(thread, screen):
    if screen is None:
        return "unknown"

    if ensure_and_setup_pvp_war_window_screen(thread):
        return "returned_to_rally_list"

    if _is_march_confirm_button_still_visible(screen):
        return "march_dialog_still_visible"

    return "unknown"


def run_join_rally(thread):
    controls = _ensure_join_rally_controls(thread)
    join_oldest_rallies_first = controls.get('settings', {}).get('join_oldest_rallies_first', False)
    # Set the rally joining position based on the oldest rallies checkbox value
    scroll_through_rallies(thread,join_oldest_rallies_first,5,True)
    # Switch the swipe direction after setting up the join_oldest_rallies_first option
    swipe_direction = False if join_oldest_rallies_first else True

    swipe_iteration  = 0
    max_swipe_iteration  = 0
    # Initialize runtime cache for rally scanning and preset rotation
    controls.setdefault('cache', {}).setdefault('skipped_monster_cords_img', [])
    controls['cache'].setdefault('previous_preset_number', None)

    while thread.thread_status():
        try:
            if _is_no_marches_cooldown_active(thread, log=True):
                time.sleep(min(1.0, _get_no_marches_cooldown_remaining(thread)))
                continue

            if _is_no_rallies_cooldown_active(thread, log=True):
                time.sleep(min(1.0, _get_no_rallies_cooldown_remaining(thread)))
                continue

            if not navigate_join_rally_window(thread):
                wait_seconds = _set_no_rallies_cooldown(thread, NO_RALLIES_RETRY_COOLDOWN_SECONDS)
                thread.log_message(
                    f"[Join-Rally] Rally navigation unavailable. Cooling off for {wait_seconds:.1f}s before retry.",
                    "info",
                    force_console=True,
                )
                continue

            # Process boss monster rallies
            process_monster_rallies(thread,join_oldest_rallies_first)

            if _is_no_marches_cooldown_active(thread, log=False):
                time.sleep(min(1.0, _get_no_marches_cooldown_remaining(thread)))
                continue

            thread.log_message(
                f"Swipe Direction: {swipe_direction} :: iteration: {swipe_iteration} itr cap: {max_swipe_iteration}",
                "debug",
                console=False
            )

            # Swipe based on the direction
            if not scroll_through_rallies(thread, swipe_direction):
                wait_seconds = _set_no_rallies_cooldown(thread, NO_RALLIES_RETRY_COOLDOWN_SECONDS)
                thread.log_message(
                    f"[Join-Rally] Rally navigation unavailable. Cooling off for {wait_seconds:.1f}s before retry.",
                    "info",
                    force_console=True,
                )
                continue

            # Update iterations
            swipe_iteration += 1
            max_swipe_iteration += 1

            # Switch direction if limit reached
            if swipe_iteration == 5:
                swipe_direction = not swipe_direction
                swipe_iteration = 0

            # Reset navigation after reaching max iteration
            if max_swipe_iteration >= 20:
                # Clear skipped cords images
                _ensure_join_rally_controls(thread).setdefault('cache', {})['skipped_monster_cords_img'] = []
                # Press back
                press_back_with_exit_guard(thread)
                time.sleep(1)
                if not navigate_join_rally_window(thread):
                    break
                # Update the swipe to scroll down
                swipe_direction = True
                max_swipe_iteration = 0
        except Exception as e:
            thread.log_message(f"Join rally loop error: {e}", "warning", force_console=True)
            thread.log_message(f"Traceback: {traceback.format_exc()}", "debug", force_console=False)


def _init_jr_scan_state(thread, controls):
    join_oldest_rallies_first = controls.get('settings', {}).get('join_oldest_rallies_first', False)
    scroll_through_rallies(thread, join_oldest_rallies_first, 5, True)
    thread.log_message(
        "[Join-Rally] Starting to join rallies now...",
        "info",
        force_console=True,
    )

    return {
        'initialized': True,
        'join_oldest_rallies_first': join_oldest_rallies_first,
        'swipe_direction': False if join_oldest_rallies_first else True,
        'swipe_iteration': 0,
        'max_swipe_iteration': 0,
        'scan_cycle_found_any': False,
        'scan_cycle_views_checked': 0,
    }


def run_join_rally_scan_pass(thread):
    """Run one join-rally scan pass for orchestrator mode."""
    if hasattr(thread, 'preempt_for_bubble_if_due') and thread.preempt_for_bubble_if_due("join-rally scan setup"):
        return False

    if _is_no_marches_cooldown_active(thread, log=False):
        return False

    if _is_no_rallies_cooldown_active(thread, log=False):
        return False

    controls = _ensure_join_rally_controls(thread)
    jr_controls_cache = controls.setdefault('cache', {})
    cache_state = thread.cache.setdefault('jr_scan_state', {})
    if jr_controls_cache.pop('no_rallies_rescan_required', False):
        thread.log_message(
            "[Join-Rally] Cool-off finished. Resetting list position and rescanning the full rally list.",
            "info",
            force_console=True,
        )
        cache_state.clear()

    if not cache_state.get('initialized', False):
        cache_state.update(_init_jr_scan_state(thread, controls))

    try:
        join_oldest_rallies_first = cache_state['join_oldest_rallies_first']
        swipe_direction = cache_state['swipe_direction']
        swipe_iteration = cache_state['swipe_iteration']
        max_swipe_iteration = cache_state['max_swipe_iteration']
        scan_cycle_found_any = cache_state.get('scan_cycle_found_any', False)
        scan_cycle_views_checked = cache_state.get('scan_cycle_views_checked', 0)

        if not navigate_join_rally_window(thread):
            wait_seconds = _set_no_rallies_cooldown(thread, NO_RALLIES_RETRY_COOLDOWN_SECONDS)
            thread.log_message(
                f"[Join-Rally] Rally navigation unavailable. Cooling off for {wait_seconds:.1f}s before retry.",
                "info",
                force_console=True,
            )
            cache_state.update({
                'scan_cycle_found_any': False,
                'scan_cycle_views_checked': 0,
            })
            return False

        rallies_found = process_monster_rallies(thread, join_oldest_rallies_first)
        scan_cycle_views_checked += 1
        if rallies_found > 0:
            scan_cycle_found_any = True

        if _is_no_marches_cooldown_active(thread, log=False):
            return False

        thread.log_message(
            f"Swipe Direction: {swipe_direction} :: iteration: {swipe_iteration} itr cap: {max_swipe_iteration}",
            "debug",
            console=False
        )

        if not scroll_through_rallies(thread, swipe_direction):
            wait_seconds = _set_no_rallies_cooldown(thread, NO_RALLIES_RETRY_COOLDOWN_SECONDS)
            thread.log_message(
                f"[Join-Rally] Rally navigation unavailable. Cooling off for {wait_seconds:.1f}s before retry.",
                "info",
                force_console=True,
            )
            cache_state.update({
                'scan_cycle_found_any': False,
                'scan_cycle_views_checked': 0,
            })
            return False

        swipe_iteration += 1
        max_swipe_iteration += 1
        completed_full_scan_cycle = False

        if swipe_iteration == 5:
            swipe_direction = not swipe_direction
            swipe_iteration = 0

        if max_swipe_iteration >= 20:
            completed_full_scan_cycle = True
            _ensure_join_rally_controls(thread).setdefault('cache', {})['skipped_monster_cords_img'] = []
            press_back_with_exit_guard(thread)
            time.sleep(1)
            if navigate_join_rally_window(thread):
                swipe_direction = True
                max_swipe_iteration = 0
                swipe_iteration = 0

        if completed_full_scan_cycle or (
            not scan_cycle_found_any and scan_cycle_views_checked >= NO_RALLIES_EMPTY_SWEEP_VIEWS
        ):
            if not scan_cycle_found_any:
                wait_seconds = _set_no_rallies_cooldown(thread, NO_RALLIES_RETRY_COOLDOWN_SECONDS)
                thread.log_message(
                    (
                        "[Join-Rally] No visible valid rallies found across the current scan sweep. "
                        f"Cooling off for {wait_seconds:.1f}s before next scan."
                    ),
                    "info",
                    force_console=True,
                )
            scan_cycle_found_any = False
            scan_cycle_views_checked = 0
            if not completed_full_scan_cycle:
                swipe_iteration = 0
                max_swipe_iteration = 0
                swipe_direction = False if join_oldest_rallies_first else True

        cache_state.update({
            'swipe_direction': swipe_direction,
            'swipe_iteration': swipe_iteration,
            'max_swipe_iteration': max_swipe_iteration,
            'scan_cycle_found_any': scan_cycle_found_any,
            'scan_cycle_views_checked': scan_cycle_views_checked,
        })

        return True
    except Exception as e:
        thread.log_message(f"Join rally scan pass error: {e}", "warning", force_console=True)
        thread.log_message(f"Traceback: {traceback.format_exc()}", "debug", force_console=False)
        return False

def process_monster_rallies(thread,scan_direction):

    if _is_no_marches_cooldown_active(thread, log=False):
        return 0

    if _is_no_rallies_cooldown_active(thread, log=False):
        return 0

    rally_cords = get_valid_rallies_area_cords(thread)
    temporary_unjoinable_rejections = 0
    joined_rallies = 0
    thread.log_message(
        f"[Join-Rally] Rallies found: {len(rally_cords)}",
        "info",
        force_console=True,
    )
    if not rally_cords:
        return 0
    # Reorder the cords based on the scan direction
    if scan_direction:
        rally_cords.reverse()
    # print(rally_cords)
    for cords in rally_cords:
        thread.cache.pop('jr_last_monster_name', None)
        if hasattr(thread, 'preempt_for_bubble_if_due') and thread.preempt_for_bubble_if_due("join-rally scan loop"):
            return len(rally_cords)
        if _is_no_marches_cooldown_active(thread, log=False):
            return len(rally_cords)
        # Recapture the  screen
        src_img = thread.capture_and_validate_screen(ads=False)
        if src_img is None:
            thread.log_message("Rally list capture failed; skipping current scan pass.", "warning", force_console=True)
            return len(rally_cords)
        _save_debug_frame(thread, "rally_list_scan", src_img)
        thread.log_message(f"Rally scan count: {len(rally_cords)} :: {cords}", "debug", console=False)
        x1, y1, x2, y2 = cords
        roi_src = src_img[y1:y2, x1:x2]
        # validate before joining the rally
        if not check_skipped_rallies(thread,roi_src):
            continue
        # Click on the rally
        thread.log_message(f"Opening rally at cords: {cords}", "info", force_console=True)
        thread.adb_manager.tap(x1, y2)
        time.sleep(1)

        rally_detail_screen = thread.capture_and_validate_screen(ads=False)
        _save_debug_frame(thread, "rally_detail_opened", rally_detail_screen)

        # Scan rally details
        thread.cache['jr_last_detail_reject_reason'] = None
        rally_info = scan_rally_info(thread,roi_src)

        if not rally_info:
            if thread.cache.get('jr_last_detail_reject_reason') in {'cant_join_on_time', 'remaining_time_too_high'}:
                temporary_unjoinable_rejections += 1
            thread.log_message("Rally detail scan failed, returning to list.", "warning", force_console=True)
            press_back_with_exit_guard(thread)
            time.sleep(1)
            continue

        # Proceed to join the rally
        join_alliance_war_btn_img = _load_asset_template("assets/540p/join_rally/join_alliance_war_btn.png", thread)
        fallback_join_btn_img = _load_asset_template("assets/540p/join_rally/join_btn.png", thread)
        if join_alliance_war_btn_img is None and fallback_join_btn_img is None:
            thread.log_message(
                "Join button templates are unavailable; cannot continue rally join flow.",
                "warning",
                force_console=True
            )
            press_back_with_exit_guard(thread)
            time.sleep(1)
            continue
        join_alliance_war_btn_match = None
        for attempt in range(2):
            rally_detail_img = thread.capture_and_validate_screen(ads=False)
            if rally_detail_img is None:
                thread.log_message(
                    f"Join button search skipped on attempt {attempt + 1}: rally detail capture failed.",
                    "debug",
                    console=False
                )
                continue
            _save_debug_frame(thread, f"join_btn_search_attempt_{attempt + 1}", rally_detail_img)
            join_alliance_war_btn_match = template_match_coordinates(rally_detail_img, join_alliance_war_btn_img)
            if not join_alliance_war_btn_match:
                join_alliance_war_btn_match = template_match_coordinates(rally_detail_img, fallback_join_btn_img)
            if join_alliance_war_btn_match:
                thread.log_message(
                    f"Join button found (attempt {attempt + 1}) at {join_alliance_war_btn_match}.",
                    "info",
                    force_console=True
                )
                break
            time.sleep(0.4)

        if not join_alliance_war_btn_match:
            thread.log_message(
                "Join button not found (likely rally already started). Skipping this rally.",
                "warning",
                force_console=True
            )
            press_back_with_exit_guard(thread)
            time.sleep(1)
            continue
        
        thread.log_message("[Join-Rally] Tapping green Join button...", "info", force_console=True)
        thread.adb_manager.tap(*join_alliance_war_btn_match)
        thread.log_message(
            "[Join-Rally] Green Join button tapped. Waiting for March dialog...",
            "info",
            force_console=True,
        )

        # Wait for march selection dialog to appear.
        # Avoid an immediate post-tap screenshot here; this exact window has been the most crash-prone.
        time.sleep(1.5)

        thread.log_message(
            "[Join-Rally] Handing off to March dialog handler.",
            "info",
            force_console=True,
        )

        # Apply march preset from the joined rally controls
        if not handle_march_selection_dialog(thread, rally_info):
            thread.log_message("March selection dialog handling failed, pressing back.", "warning", force_console=True)
            press_back_with_exit_guard(thread)
            time.sleep(1)
            if _is_no_marches_cooldown_active(thread, log=False):
                return len(rally_cords)
            continue
        
        joined_monster = thread.cache.get('jr_last_monster_name') or "Unknown"
        thread.log_message(
            f"Joined Monster Rally - {joined_monster}",
            "info",
            force_console=True,
        )
        jr_scan_state = thread.cache.get('jr_scan_state')
        if isinstance(jr_scan_state, dict):
            jr_scan_state['scan_cycle_found_any'] = False
            jr_scan_state['scan_cycle_views_checked'] = 0
        joined_rallies += 1
        time.sleep(1)

    if joined_rallies == 0 and temporary_unjoinable_rejections > 0:
        wait_seconds = _set_no_rallies_cooldown(thread, NO_RALLIES_RETRY_COOLDOWN_SECONDS)
        thread.log_message(
            (
                "[Join-Rally] All scanned rallies are temporarily unjoinable. "
                f"Treating as no rallies found; cooling off for {wait_seconds:.1f}s before next scan."
            ),
            "info",
            force_console=True,
        )

    return len(rally_cords)


def add_rally_cord_to_skip_list(thread, src_img):
    """Add rally snippet to skip-cache and keep cache bounded."""
    if src_img is None or src_img.size == 0:
        return

    controls = _ensure_join_rally_controls(thread)
    cache = controls['cache'].setdefault('skipped_monster_cords_img', [])
    cache.append(src_img.copy())

    if len(cache) > 30:
        del cache[:-30]




def handle_march_selection_dialog(thread, rally_info):
    """
    Handle the march selection dialog that appears after clicking join.
    Apply presets (troops reset, general selection) and confirm the join.
    """
    try:
        if hasattr(thread, 'preempt_for_bubble_if_due') and thread.preempt_for_bubble_if_due("join-rally march dialog start"):
            return False

        thread.log_message("March dialog: starting march dialog handler", "info", force_console=True)
        
        # Wait a bit more for dialog to fully render
        time.sleep(1)
        
        debug_mode = get_debug_mode()

        # Capture screen and save for reference
        march_dialog_screen = thread.capture_and_validate_screen(ads=False)
        _save_debug_frame(thread, "march_dialog_screen", march_dialog_screen)
        if debug_mode and march_dialog_screen is not None:
            timestamp = get_current_datetime_string()
            march_screen_path = os.path.join("temp", f"march_dialog_{timestamp}.png")
            os.makedirs("temp", exist_ok=True)
            cv2.imwrite(march_screen_path, march_dialog_screen)
            thread.log_message(f"March dialog screenshot saved: {march_screen_path}", "debug", force_console=False)
        
        # Get the join_rally_controls from thread cache
        join_rally_controls = thread.cache.get('join_rally_controls', {})
        selected_presets = join_rally_controls.get('settings', {}).get('selected_presets', {})
        presets_config = selected_presets.get('presets', {})
        
        thread.log_message(f"March dialog: Found {len(presets_config)} presets to apply", "debug", force_console=False)
        
        if presets_config:
            available_presets = list(presets_config.keys())
            if available_presets:
                cache = join_rally_controls.setdefault('cache', {})
                previous_preset = cache.get('previous_preset_number')
                if previous_preset in available_presets:
                    previous_index = available_presets.index(previous_preset)
                    selected_preset_num = available_presets[(previous_index + 1) % len(available_presets)]
                else:
                    selected_preset_num = available_presets[0]

                cache['previous_preset_number'] = selected_preset_num
                preset_options = presets_config[selected_preset_num]
                
                thread.log_message(
                    f"Applying march preset {selected_preset_num}: reset_troops={preset_options.get('reset_to_one_troop')}, use_generals={preset_options.get('use_selected_generals')}",
                    "info",
                    force_console=True
                )
                
                # Handle troop reset if needed
                if preset_options.get('reset_to_one_troop'):
                    thread.log_message("Attempting to reset troops to 1", "info", force_console=True)
                    apply_troops_reset(thread)
        
        # Wait slightly before confirming
        time.sleep(0.5)

        if hasattr(thread, 'preempt_for_bubble_if_due') and thread.preempt_for_bubble_if_due("join-rally march confirm"):
            return False
        
        # Click the confirm march button - this is the button that ACTUALLY joins the rally
        march_confirm_btn = find_march_confirm_button(thread)
        if march_confirm_btn:
            thread.log_message(f"Tapping march confirm button at {march_confirm_btn}", "info", force_console=True)
            
            # Crop and save the button region for verification
            if debug_mode and march_dialog_screen is not None:
                try:
                    btn_x, btn_y = march_confirm_btn
                    crop_size = 80  # pixels around the button center
                    x1 = max(0, btn_x - crop_size)
                    x2 = min(march_dialog_screen.shape[1], btn_x + crop_size)
                    y1 = max(0, btn_y - crop_size)
                    y2 = min(march_dialog_screen.shape[0], btn_y + crop_size)
                    
                    button_crop = march_dialog_screen[y1:y2, x1:x2]
                    timestamp = get_current_datetime_string()
                    button_crop_path = os.path.join("temp", f"march_button_tap_{btn_x}_{btn_y}_{timestamp}.png")
                    cv2.imwrite(button_crop_path, button_crop)
                    thread.log_message(f"Button region saved: {button_crop_path}", "debug", force_console=False)
                except Exception as e:
                    thread.log_message(f"Could not save button crop: {e}", "debug", force_console=False)
            
            thread.adb_manager.tap(*march_confirm_btn)
            _save_debug_frame(thread, "march_confirm_tapped")
            thread.log_message("Waiting for march result...", "debug", force_console=False)
            time.sleep(1.2)

            stamina_prompt_result = handle_stamina_prompt_and_recover(thread)
            if stamina_prompt_result is False:
                thread.log_message("Stamina prompt detected but handling failed.", "warning", force_console=True)
                return False
            if stamina_prompt_result is True:
                thread.log_message("Stamina prompt handled and rally flow recovered.", "info", force_console=True)
                return True

            if _detect_no_more_troops_banner(thread, checks=6, delay_between_checks=0.7):
                wait_seconds = _set_no_marches_cooldown(thread, NO_MARCHES_RETRY_COOLDOWN_SECONDS)
                thread.log_message(
                    f"Join failed: no march slots available (cannot send more troops). Cooling down for {wait_seconds:.1f}s.",
                    "warning",
                    force_console=True
                )
                return False

            time.sleep(1.2)
            post_march_screen = thread.capture_and_validate_screen(ads=False)
            post_march_result = _classify_post_march_result(thread, post_march_screen)
            if post_march_result == "returned_to_rally_list":
                thread.log_message(
                    "[Join-Rally] Returned to rally list after March confirm; treating join as successful.",
                    "info",
                    force_console=True
                )
                return True

            if post_march_result == "march_dialog_still_visible":
                if _detect_no_more_troops_banner(thread, checks=3, delay_between_checks=0.5):
                    wait_seconds = _set_no_marches_cooldown(thread, NO_MARCHES_RETRY_COOLDOWN_SECONDS)
                    thread.log_message(
                        f"Join failed: no march slots available (cannot send more troops). Cooling down for {wait_seconds:.1f}s.",
                        "warning",
                        force_console=True
                    )
                    return False

                thread.log_message(
                    "Join did not complete: March dialog is still visible after confirm tap.",
                    "warning",
                    force_console=True
                )
                return False

            thread.log_message(
                "[Join-Rally] March confirm outcome unclear, but March dialog is no longer visible; treating join as successful.",
                "info",
                force_console=True
            )
            return True
        else:
            thread.log_message("Could not determine march confirm button location", "warning", force_console=True)
            return False
            
    except Exception as e:
        thread.log_message(f"Error in march selection dialog handling: {e}", "warning", force_console=True)
        thread.log_message(f"Traceback: {traceback.format_exc()}", "debug", force_console=False)
        return False


def apply_troops_reset(thread):
    """Reset troop count to 1 in the march selection dialog"""
    try:
        # The troops field is typically in the march dialog
        # For 540x960 resolution, the dialog is centered and troops input is usually in the middle area
        
        # Tap on the troops input field (estimated center-left area of dialog)
        troops_field_x, troops_field_y = 200, 500
        
        thread.log_message(f"Tapping troops field at ({troops_field_x}, {troops_field_y})", "debug", force_console=False)
        thread.adb_manager.tap(troops_field_x, troops_field_y)
        time.sleep(0.5)
        
        # Clear the field by pressing delete multiple times
        # Android doesn't support Ctrl+A reliably, so delete backwards
        try:
            for _ in range(5):
                thread.adb_manager.device.shell("input keyevent KEYCODE_DEL")
                time.sleep(0.1)
        except Exception as e:
            thread.log_message(f"Delete key failed: {e}", "debug", force_console=False)
        
        # Type "1"
        try:
            thread.adb_manager.device.shell("input text 1")
            thread.log_message("Troops reset to 1", "debug", force_console=False)
        except Exception as e:
            thread.log_message(f"Failed to type troops value: {e}", "warning", force_console=False)
            
        time.sleep(0.3)
        return True
    except Exception as e:
        thread.log_message(f"Failed to reset troops: {e}", "warning", force_console=False)
        return False


def handle_stamina_prompt_and_recover(thread):
    """
    Handle the stamina prompt that can appear after tapping March.
    Returns:
      - True  -> prompt was detected and handled successfully
      - False -> prompt was detected but handling failed
      - None  -> prompt was not detected
    """
    try:
        screen = thread.capture_and_validate_screen(ads=False)
        _save_debug_frame(thread, "post_march_result", screen)
        if screen is None:
            return None

        if not is_stamina_prompt_visible(screen):
            return None

        join_rally_controls = thread.cache.get('join_rally_controls', {})
        stamina_config = join_rally_controls.get('settings', {}).get('auto_use_stamina', {})
        auto_use_enabled = bool(stamina_config.get('enabled', False))
        stamina_option = (stamina_config.get('option') or "Min Stamina").strip()

        thread.log_message(
            f"Stamina prompt detected. auto_use_stamina={auto_use_enabled}, option={stamina_option}",
            "warning",
            force_console=True
        )

        confirm_btn = find_stamina_prompt_confirm_button(screen)

        if not auto_use_enabled:
            thread.log_message("Auto-use stamina disabled. Dismissing prompt.", "warning", force_console=True)
            if confirm_btn:
                cancel_x = max(20, int(screen.shape[1] - confirm_btn[0]))
                thread.adb_manager.tap(cancel_x, confirm_btn[1])
            else:
                thread.adb_manager.press_back()
            time.sleep(0.8)
            return False

        if not confirm_btn:
            thread.log_message("Could not locate stamina prompt confirm button.", "warning", force_console=True)
            return False

        thread.adb_manager.tap(*confirm_btn)
        _save_debug_frame(thread, "stamina_prompt_confirm_tapped")
        time.sleep(1.1)

        if not handle_stamina_screen(thread, stamina_option):
            return False

        return True
    except Exception as e:
        thread.log_message(f"Error handling stamina prompt: {e}", "warning", force_console=True)
        thread.log_message(f"Traceback: {traceback.format_exc()}", "debug", force_console=False)
        return False


def is_stamina_prompt_visible(screen):
    """Detect stamina modal by OCRing the center dialog area for stamina-specific words."""
    try:
        roi = _crop_profile(screen, "stamina_prompt_text_ocr")
        if roi is None:
            return False

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, config='--oem 3 --psm 6')
        normalized = " ".join((text or "").lower().split())

        if "stamina" in normalized:
            return True
        if "add" in normalized and "more" in normalized:
            return True
        if "insufficient" in normalized and "stamina" in normalized:
            return True
        if "not enough" in normalized and "stamina" in normalized:
            return True

        return False
    except Exception:
        return False


def find_stamina_prompt_confirm_button(screen):
    """Find the right-side green confirm button in stamina prompt dialog."""
    roi_x1, roi_y1, roi_x2, roi_y2 = _profile_bounds(screen, "stamina_prompt_confirm_search")

    if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
        return None

    roi = screen[roi_y1:roi_y2, roi_x1:roi_x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    lower_green = np.array([35, 55, 40], dtype=np.uint8)
    upper_green = np.array([95, 255, 255], dtype=np.uint8)
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    kernel = np.ones((5, 5), np.uint8)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, kernel)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_rect = None
    best_score = 0
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = bw * bh
        if area < 1200 or bh <= 0:
            continue
        aspect_ratio = bw / float(bh)
        if aspect_ratio < 1.6:
            continue

        score = area
        if score > best_score:
            best_score = score
            best_rect = (x, y, bw, bh)

    if not best_rect:
        return None

    x, y, bw, bh = best_rect
    center_x = roi_x1 + x + (bw // 2)
    center_y = roi_y1 + y + (bh // 2)
    return center_x, center_y


def find_stamina_screen_use_button(screen):
    """Find the bottom-center green button on stamina use screen."""
    roi_x1, roi_y1, roi_x2, roi_y2 = _profile_bounds(screen, "stamina_use_button_search")

    if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
        return None

    roi = screen[roi_y1:roi_y2, roi_x1:roi_x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    lower_green = np.array([35, 55, 40], dtype=np.uint8)
    upper_green = np.array([95, 255, 255], dtype=np.uint8)
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    kernel = np.ones((5, 5), np.uint8)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, kernel)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_rect = None
    best_score = 0
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = bw * bh
        if area < 1800 or bh <= 0:
            continue
        aspect_ratio = bw / float(bh)
        if aspect_ratio < 2.0:
            continue

        score = area
        if score > best_score:
            best_score = score
            best_rect = (x, y, bw, bh)

    if not best_rect:
        return None

    x, y, bw, bh = best_rect
    center_x = roi_x1 + x + (bw // 2)
    center_y = roi_y1 + y + (bh // 2)
    return center_x, center_y


def find_stamina_item_use_button(screen, stamina_option):
    """Find a stamina item row 'Use(...)' button on the right side of the Use Item list."""
    roi_x1, roi_y1, roi_x2, roi_y2 = _profile_bounds(screen, "stamina_item_use_button_search")

    if roi_x2 <= roi_x1 or roi_y2 <= roi_y1:
        return None

    roi = screen[roi_y1:roi_y2, roi_x1:roi_x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    lower_green = np.array([35, 55, 40], dtype=np.uint8)
    upper_green = np.array([95, 255, 255], dtype=np.uint8)
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    kernel = np.ones((5, 5), np.uint8)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, kernel)
    mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        area = bw * bh
        if area < 1500 or bh <= 0:
            continue

        aspect_ratio = bw / float(bh)
        if aspect_ratio < 1.5:
            continue

        center_x = roi_x1 + x + (bw // 2)
        center_y = roi_y1 + y + (bh // 2)
        candidates.append((center_x, center_y, area))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[1])
    option_normalized = (stamina_option or "").lower()
    selected = candidates[-1] if "max" in option_normalized else candidates[0]
    return selected[0], selected[1]


def is_stamina_item_screen(screen):
    """Detect Use Item list screen by OCRing top region text."""
    try:
        if screen is None:
            return False

        h, w = screen.shape[:2]
        x1, y1, x2, y2 = int(w * 0.15), int(h * 0.02), int(w * 0.85), int(h * 0.22)
        roi = screen[y1:y2, x1:x2]
        if roi is None or roi.size == 0:
            return False

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, config='--oem 3 --psm 6')
        normalized = " ".join((text or "").lower().split())

        return "use item" in normalized or "select an item" in normalized
    except Exception:
        return False


def handle_stamina_screen(thread, stamina_option):
    """Tap stamina option (Min/Max), use it, then return to rally window."""
    try:
        screen = thread.capture_and_validate_screen(ads=False)
        _save_debug_frame(thread, "stamina_screen_opened", screen)
        if screen is None:
            return False

        use_btn = find_stamina_item_use_button(screen, stamina_option)
        if use_btn:
            thread.log_message(
                f"Tapping stamina list use button for '{stamina_option}' at {use_btn}",
                "info",
                force_console=True
            )
            thread.adb_manager.tap(*use_btn)
            _save_debug_frame(thread, "stamina_use_tapped")
        else:
            option_normalized = (stamina_option or "").lower()
            fallback_profile = "stamina_item_use_max_fallback" if "max" in option_normalized else "stamina_item_use_min_fallback"
            fallback_use = _profile_center(screen, fallback_profile)
            thread.log_message(
                f"Could not detect stamina list use button, tapping fallback at {fallback_use}.",
                "warning",
                force_console=True
            )
            thread.adb_manager.tap(*fallback_use)
            _save_debug_frame(thread, "stamina_use_fallback_tapped")

        time.sleep(1.2)

        post_use_screen = thread.capture_and_validate_screen(ads=False)
        _save_debug_frame(thread, "stamina_post_use_screen", post_use_screen)

        if post_use_screen is not None and is_stamina_prompt_visible(post_use_screen):
            confirm_btn = find_stamina_prompt_confirm_button(post_use_screen)
            if confirm_btn:
                thread.log_message(f"Confirming stamina prompt at {confirm_btn}", "info", force_console=True)
                thread.adb_manager.tap(*confirm_btn)
                _save_debug_frame(thread, "stamina_prompt_confirm_after_use")
                time.sleep(0.8)
            else:
                thread.log_message("Stamina prompt visible after item use, but confirm button not found.", "warning", force_console=True)

        if post_use_screen is not None and is_stamina_item_screen(post_use_screen):
            thread.log_message("Still on Use Item screen after item tap, pressing back.", "debug", force_console=False)
            thread.adb_manager.press_back()
            time.sleep(0.8)

        return navigate_join_rally_window(thread)
    except Exception as e:
        thread.log_message(f"Error handling stamina screen: {e}", "warning", force_console=True)
        thread.log_message(f"Traceback: {traceback.format_exc()}", "debug", force_console=False)
        return False


def find_march_confirm_button(thread):
    """
    Find the March confirm button in the march selection dialog.
    Tries multiple common locations for button on 540x960 screen.
    Returns coordinates of the button if found, None otherwise.
    """
    try:
        screen = thread.capture_and_validate_screen(ads=False)
        if screen is None:
            return None
            
        screen_height, screen_width = screen.shape[:2]
        
        thread.log_message(f"Screen dimensions: {screen_width}x{screen_height}", "debug", force_console=False)

        roi_x1, roi_y1, roi_x2, roi_y2 = _profile_bounds(screen, "march_confirm_search")

        if roi_x2 > roi_x1 and roi_y2 > roi_y1:
            roi = screen[roi_y1:roi_y2, roi_x1:roi_x2]
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

            lower_green = np.array([35, 55, 40], dtype=np.uint8)
            upper_green = np.array([95, 255, 255], dtype=np.uint8)
            mask_green = cv2.inRange(hsv, lower_green, upper_green)

            kernel = np.ones((5, 5), np.uint8)
            mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, kernel)
            mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            best_rect = None
            best_score = 0
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                if area < 1200:
                    continue
                if h <= 0:
                    continue
                aspect_ratio = w / float(h)
                if aspect_ratio < 1.8:
                    continue

                score = area
                if score > best_score:
                    best_score = score
                    best_rect = (x, y, w, h)

            if best_rect:
                x, y, w, h = best_rect
                center_x = roi_x1 + x + (w // 2)
                center_y = roi_y1 + y + (h // 2)
                thread.log_message(
                    f"March button detected via green ROI at ({center_x}, {center_y}) with bbox ({x}, {y}, {w}, {h}).",
                    "info",
                    force_console=True
                )
                return center_x, center_y
        
        # The march dialog has TWO buttons at the bottom:
        # LEFT: "Reset" button at ~(270, 905)
        # RIGHT: "March" button at ~(405-445, 905)
        # We need the RIGHT button (March button)
        
        button_candidates = [
            _profile_center(screen, "march_confirm_fallback"),
            (int(screen_width * 0.80), int(screen_height * 0.90)),
            (int(screen_width * 0.76), int(screen_height * 0.94)),
        ]
        
        thread.log_message(f"March button candidates: {button_candidates}", "debug", force_console=False)
        
        # Return RIGHT button (index 0) - the March button
        # DO NOT return index 1 which is the Reset button!
        return button_candidates[0]
        
    except Exception as e:
        thread.log_message(f"Error finding march confirm button: {e}", "warning", force_console=False)
        return None


def scan_rally_info(thread,roi_src):
    strict_monster_match = get_strict_monster_match()
    thread.cache['jr_last_detail_reject_reason'] = None

    thread.log_message("Scan rally info: start", "info", force_console=True)

    # Load template images
    boss_monster_flag_img = _load_asset_template("assets/540p/join_rally/boss_monster_flag.png", thread)
    if boss_monster_flag_img is None:
        thread.log_message("Missing boss_monster_flag template; skipping rally detail scan.", "warning", force_console=True)
        return False


    # Capture the current screen
    thread.log_message("Scan rally info: capture screen", "info", force_console=True)
    src_img = thread.capture_and_validate_screen(ads=False)
    _save_debug_frame(thread, "scan_rally_info_source", src_img)
    thread.log_message("Scan rally info: screen captured", "info", force_console=True)

    # Make sure the rally is in progress
    if not is_template_match(src_img,boss_monster_flag_img):
        thread.cache['jr_last_detail_reject_reason'] = 'boss_flag_not_found'
        thread.log_message("Rally detail rejected: boss monster flag not found.", "warning", force_console=True)
        return False
    # Make sure there is enough time to join the rally
    thread.log_message("Scan rally info: reading remaining time", "info", force_console=True)
    try:
        remaining_time = get_remaining_rally_time(src_img, thread)
    except Exception as e:
        thread.cache['jr_last_detail_reject_reason'] = 'remaining_time_ocr_error'
        thread.log_message(
            f"Rally detail rejected: remaining time OCR error ({e}).",
            "warning",
            force_console=True
        )
        return False
    thread.log_message(f"Scan rally info: remaining time={remaining_time}", "info", force_console=True)
    if not remaining_time:
        thread.cache['jr_last_detail_reject_reason'] = 'remaining_time_unreadable'
        thread.log_message("Rally detail rejected: remaining time unreadable.", "warning", force_console=True)
        return False
    # Check whether the timer is above 5 mins
    if remaining_time > timedelta(minutes=5):
        thread.cache['jr_last_detail_reject_reason'] = 'remaining_time_too_high'
        thread.log_message(f"Rally detail rejected: remaining time too high ({remaining_time}).", "info", force_console=True)
        add_rally_cord_to_skip_list(thread, roi_src)
        return False
    # Get the Timer on the join rally button TODO fix the code to extract the correct timer always
    thread.log_message("Scan rally info: reading march time", "info", force_console=True)
    march_time = get_march_join_time(roi_src, thread)
    thread.log_message(f"Scan rally info: march time={march_time}", "info", force_console=True)
    if not march_time:
        thread.cache['jr_last_detail_reject_reason'] = 'invalid_march_time'
        thread.log_message("Rally detail rejected: invalid march time.", "warning", force_console=True)
        add_rally_cord_to_skip_list(thread, roi_src)
        return False
    thread.log_message(f"Remaining Time: {remaining_time} :: March Time {march_time}", "info", force_console=True)
    # Add buffer time to march time
    total_march_time = march_time + timedelta(seconds=10)
    thread.log_message(f"Total march time {total_march_time}", "info", force_console=True)
    # Check if march time + buffer is within remaining rally time
    if total_march_time >= remaining_time:
        thread.cache['jr_last_detail_reject_reason'] = 'cant_join_on_time'
        thread.log_message("Rally detail rejected: can't join on time.", "warning", force_console=True)
        add_rally_cord_to_skip_list(thread, roi_src)
        return False

    # Read the boss
    try:
        extracted_boss_data = read_monster_data(thread, src_img.copy())
    except Exception as e:
        if strict_monster_match:
            thread.log_message(
                f"Monster data extraction failed ({e}). Strict monster mode enabled, skipping rally.",
                "warning",
                force_console=True
            )
            return False
        thread.log_message(
            f"Monster data extraction failed ({e}). Proceeding with default march preset flow.",
            "warning",
            force_console=True
        )
        return True

    if not extracted_boss_data:
        if strict_monster_match:
            thread.log_message(
                "Monster not recognized from rally card. Strict monster mode enabled, skipping rally.",
                "warning",
                force_console=True
            )
            return False
        thread.log_message(
            "Monster not recognized from rally card. Proceeding with default march preset flow.",
            "warning",
            force_console=True
        )
        return True

    # Verify if the boss is in the selected join list
    if not verify_monster_join(thread,extracted_boss_data):
        if strict_monster_match:
            thread.log_message("Rally detail rejected: monster not in join list.", "warning", force_console=True)
            return False
        thread.log_message(
            "Monster not in selected join list, but strict mode is disabled. Proceeding with default march preset flow.",
            "warning",
            force_console=True
        )
        return True

    return True

def read_monster_data(thread,src_img):
    # monster_power_icon_img = cv2.imread("assets/540p/join_rally/monster_power_icon.png")

    extracted_monster_name = ""
    for profile_name in ("monster_text_ocr", "monster_text_ocr_fallback"):
        boss_text_img = _crop_profile(src_img, profile_name)
        if boss_text_img is None:
            continue
        _save_debug_frame(thread, f"monster_text_roi_{profile_name}", boss_text_img)
        extracted_monster_name = extract_monster_name_from_image(boss_text_img)
        if extracted_monster_name:
            break

    if not extracted_monster_name:
        return None

    thread.log_message(f"Extracted monster text: {extracted_monster_name}", "info", force_console=True)
    thread.cache['jr_last_monster_name_ocr'] = extracted_monster_name
    thread.cache['jr_last_monster_name'] = extracted_monster_name

    # Check and skip dawn monster
    if "dawn" in extracted_monster_name:
        # print("Skipping Dawn Monsters")
        return None



    # Get the all the matching boss objects from the extracted text
    bosses = lookup_boss_by_name(extracted_monster_name)

    if not bosses:
        # print("Cannot find the boss in the db \ read wrong name")
        return None

    try:
        candidate_labels = [f"{boss.name}(boss_id={boss.boss_monster_id},level_id={boss.id},logic={logic})" for boss, logic in bosses]
        thread.log_message(
            f"Monster lookup candidates: {', '.join(candidate_labels)}",
            "debug",
            force_console=False
        )
    except Exception:
        pass

    # Prefer a canonical DB monster label for user-facing logs.
    # This avoids OCR glue artifacts like "wahgysphinx" while keeping OCR raw text for debug.
    try:
        normalized_extracted = normalize_boss_text(extracted_monster_name)
        if normalized_extracted:
            ranked = []
            for boss, _logic in bosses:
                boss_name = (getattr(boss, 'name', '') or '').strip()
                normalized_name = normalize_boss_text(boss_name)
                if not normalized_name:
                    continue

                exact = 1 if normalized_name == normalized_extracted else 0
                substring = 1 if (normalized_name in normalized_extracted or normalized_extracted in normalized_name) else 0
                ranked.append((exact, substring, len(normalized_name), boss_name))

            if ranked:
                ranked.sort(reverse=True)
                canonical_name = ranked[0][3]
                if canonical_name:
                    thread.cache['jr_last_monster_name'] = canonical_name
    except Exception:
        pass

    return bosses

def verify_monster_join(thread,extracted_boss_data):
    if not extracted_boss_data:
        return False

    selected_levels_data = _ensure_join_rally_controls(thread).get('data', [])
    if not selected_levels_data:
        return False

    # Support both formats:
    # 1) dict {boss_id: set(level_ids)}
    # 2) list[MonsterLevel] from get_join_rally_controls
    if isinstance(selected_levels_data, dict):
        selected_boss_levels = selected_levels_data
    else:
        selected_boss_levels = {}
        for level in selected_levels_data:
            boss_id = getattr(level, "boss_monster_id", None)
            level_id = getattr(level, "id", None)
            if boss_id is None or level_id is None:
                continue
            selected_boss_levels.setdefault(boss_id, set()).add(level_id)

    if not selected_boss_levels:
        return False

    src_img = thread.capture_and_validate_screen(ads=False)
    extracted_power_text = extract_monster_power_from_image(src_img.copy()) if src_img is not None else ""
    extracted_power = (extracted_power_text or "").strip().lower()

    selected_boss_ids = set(selected_boss_levels.keys())

    for boss, logic in extracted_boss_data:
        selected_levels = selected_boss_levels.get(boss.boss_monster_id)
        if not selected_levels:
            continue

        if logic in (1, 3):
            if boss.id in selected_levels:
                return True
            continue

        if logic in (2, 4):
            boss_power = (boss.power or "").strip().lower()
            if boss.id not in selected_levels:
                continue

            # Power-aware matching when available.
            if extracted_power and boss_power == extracted_power:
                return True

            # Fallback when power OCR is empty/unreliable: allow selected level match.
            if not extracted_power:
                return True

    # Fallback: if OCR found the correct boss but ambiguous level/power, allow by boss id.
    for boss, _logic in extracted_boss_data:
        if boss.boss_monster_id in selected_boss_ids:
            thread.log_message(
                f"Monster matched by boss id fallback (boss_id={boss.boss_monster_id}, level_id={boss.id}).",
                "debug",
                force_console=False
            )
            return True

    return False




def get_march_join_time(src_img, thread=None):
    join_btn = _load_asset_template("assets/540p/join_rally/join_btn.png", thread)
    if join_btn is None:
        return False
    join_btn_match = template_match_coordinates(src_img,join_btn,return_center=False)
    if not join_btn_match:
        return False
    # Get template(join_btn) dimensions
    join_btn_height, join_btn_width = join_btn.shape[:2]

    # Define new starting and ending crop coordinates
    y1_new = join_btn_match[1] + join_btn_height
    x2 = join_btn_match[0] + join_btn_width
    y2 = y1_new + join_btn_height

    # Ensure crop is within image bounds
    height_img, width_img = src_img.shape[:2]
    x2 = min(x2, width_img)
    y2 = min(y2, height_img)

    # Perform cropping
    src_img = src_img[y1_new+2:y2-6, join_btn_match[0]+10:x2-10]
    # cv2.imwrite(fr"E:\Projects\PyCharmProjects\TaskEX\temp\jb_{get_current_datetime_string()}.png",src_img)

    if src_img is None or src_img.size == 0:
        return False

    # Full debug of join timer ROI comes from caller screenshot; keep focused crop for OCR diagnostics.

    # Skip if join time text is red (already too late)
    if detect_red_color(src_img):
        return False

    return parse_timer_to_timedelta(extract_join_rally_time_from_image(src_img))


def _extract_remaining_time_text_with_timeout(src_img, timeout_sec=5):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(extract_remaining_rally_time_from_image, src_img)
    try:
        return future.result(timeout=timeout_sec)
    except TimeoutError:
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _parse_remaining_time_candidate(raw_text):
    if not raw_text or not isinstance(raw_text, str):
        return None

    normalized = raw_text.replace("\n", " ").replace("\r", " ").replace(".", ":")

    # Keep only digits/colon as timer candidates; letters are never valid timer chars.
    cleaned = re.sub(r"[^0-9:]", " ", normalized)
    matches = re.findall(r"(?<!\d)(?:\d{1,2}:)?\d{2}:\d{2}(?!\d)", cleaned)
    for token in matches:
        parsed = parse_timer_to_timedelta(token)
        if parsed is not None:
            return parsed

    return None


def _build_remaining_time_rois(src_img):
    timer_bar = _crop_profile(src_img, "remaining_time_ocr_timer_bar")
    primary = _crop_profile(src_img, "remaining_time_ocr_primary")
    fallback = _crop_profile(src_img, "remaining_time_ocr_fallback")

    rois = []
    if timer_bar is not None and timer_bar.size > 0:
        rois.append(timer_bar)
    if primary is not None and primary.size > 0:
        rois.append(primary)
    if fallback is not None and fallback.size > 0:
        rois.append(fallback)
    return rois


def get_remaining_rally_time(src_img, thread=None):
    candidate_rois = _build_remaining_time_rois(src_img)
    remaining_text = None
    remaining_time = None
    debug_roi = candidate_rois[0] if candidate_rois else src_img

    for roi in candidate_rois:
        debug_roi = roi
        remaining_text = _extract_remaining_time_text_with_timeout(roi, timeout_sec=1)
        try:
            if remaining_text:
                remaining_time = _parse_remaining_time_candidate(remaining_text)
                if remaining_time is not None:
                    break

            raw_text = extract_remaining_rally_time_text(roi)
            remaining_time = _parse_remaining_time_candidate(raw_text)
            if remaining_time is not None:
                break
        except Exception:
            pass

    if remaining_time is None and thread is not None:
        try:
            if remaining_text is None:
                thread.log_message(
                    "Remaining time OCR timed out.",
                    "warning",
                    force_console=True
                )
            raw_text = extract_remaining_rally_time_text(debug_roi)
            timestamp = get_current_datetime_string()
            os.makedirs("temp", exist_ok=True)
            raw_path = os.path.join("temp", f"rally_time_raw_{timestamp}.png")
            cv2.imwrite(raw_path, debug_roi)
            thread.log_message(
                f"Remaining time OCR failed. Raw text='{raw_text}'. Saved crop: {raw_path}",
                "warning",
                force_console=True
            )
        except Exception as e:
            thread.log_message(
                f"Remaining time OCR debug failed: {e}",
                "warning",
                force_console=True
            )

    return remaining_time


def check_skipped_rallies(thread,src_img):
    """
    Validate before proceeding to join
    """

    # Check skipped list
    controls = _ensure_join_rally_controls(thread)
    for cords_img in controls.get('cache', {}).get('skipped_monster_cords_img', []):
        if is_template_match(src_img, cords_img):
            # print("Already skipped one")
            return False

    return True

def get_valid_rallies_area_cords(thread):
    """
    Return the cords of the image area which contains the monster tag, cords(map icon) and join button with time
    """
    # Capture the current screen
    src_img = thread.capture_and_validate_screen(ads=False)

    # Load template images
    boss_monster_tag_img = _load_asset_template("assets/540p/join_rally/boss_monster_tag.png", thread)
    join_btn_img = _load_asset_template("assets/540p/join_rally/join_btn.png", thread)
    map_pinpoint_img = _load_asset_template("assets/540p/join_rally/map_pinpoint_tag.png", thread)

    if boss_monster_tag_img is None or join_btn_img is None or map_pinpoint_img is None:
        thread.log_message(
            "Join-rally list templates are unavailable; cannot detect rally rows.",
            "warning",
            force_console=True
        )
        return []

    # Get the boss monster rallies matches
    boss_monster_tag_matches = template_match_coordinates_all(src_img, boss_monster_tag_img)
    valid_cords = []
    # Loop through each boss monster tag match
    for (x1, y1) in boss_monster_tag_matches:
        # Define a limited ROI: From (x1, y1) to (end of width, y1 + 200)
        roi_y_end = min(y1 + 200, src_img.shape[0])  # Ensure it wont exceed the image height to avoid wrong set matching
        roi = src_img[y1:roi_y_end, x1:]

        # Check for join button within the ROI
        join_btn_matches = template_match_coordinates(roi, join_btn_img, False)

        if not join_btn_matches:
            continue

        # Get the first match coordinates for join_btn inside the ROI
        match_x1, match_y1 = join_btn_matches

        # Define the region for the cords icon(map pinpoint icon) template match
        combined_roi_x1 = x1
        combined_roi_y1 = y1
        combined_roi_x2 = x1 + match_x1 + join_btn_img.shape[1]  # add join_btn_img width
        combined_roi_y2 = y1 + match_y1 + join_btn_img.shape[0] * 2  # add join_btn_img height twice

        # Create an image area to scan for the map pinpoint icon (to get the cords of the monsters)
        combined_roi = src_img[combined_roi_y1:combined_roi_y2, combined_roi_x1:combined_roi_x2]

        # Search for the map pinpoint icon inside the combined ROI
        map_pinpoint_match = template_match_coordinates(combined_roi, map_pinpoint_img, False)

        if not map_pinpoint_match:
            continue

        # Get the map pinpoint coordinates relative to the combined ROI
        map_pinpoint_x1, map_pinpoint_y1 = map_pinpoint_match

        # Adjust combined ROI to start from the map pinpoint match coordinates
        adjusted_x1 = combined_roi_x1 + map_pinpoint_x1
        adjusted_y1 = combined_roi_y1 + map_pinpoint_y1
        adjusted_x2 = combined_roi_x2  # Keep the previous x2 boundary
        adjusted_y2 = combined_roi_y2  # Keep the previous y2 boundary

        # Create the adjusted combined ROI
        # adjusted_combined_roi = src_img[adjusted_y1:adjusted_y2, adjusted_x1:adjusted_x2]
        # cv2.imwrite(fr"E:\Projects\PyCharmProjects\TaskEX\temp\{x1},{y1}.png",adjusted_combined_roi)

        valid_cords.append((adjusted_x1, adjusted_y1, adjusted_x2, adjusted_y2))

    return valid_cords

def scroll_through_rallies(thread,swipe_direction,swipe_limit=1,initial_swipe = False):
    """
    swipe_direction True = scroll down, False = scroll up
    """
    # Swipe coordinates based on direction
    swipe_cords = [250, 810, 250, 320] if swipe_direction else [250, 320, 250, 810]
    # Navigate to the alliance war window
    if not navigate_join_rally_window(thread):
        thread.log_message("Cannot navigate to join rally window.", "warning", force_console=True)
        return False
    if initial_swipe:
        thread.log_message(
            "[Join-Rally] Scrolling to end of rally list...",
            "info",
            force_console=True,
        )
    # If the join oldest rally is not checked, then skip this.
    if initial_swipe and not swipe_direction:
        return True
    # Load the template image
    background_img = _load_asset_template("assets/540p/join_rally/alliance_war_window_background.png", thread)
    for i in range(swipe_limit):
        # Check if there is any rallies to scroll through
        src_img = thread.capture_and_validate_screen(ads=False)
        if background_img is not None and is_template_match(src_img, background_img,False, 0.95):
            if initial_swipe:
                thread.log_message(
                    "[Join-Rally] End of rally list reached.",
                    "info",
                    force_console=True,
                )
            # print("No more rallies in the list")
            # cv2.imwrite(r"E:\Projects\PyCharmProjects\TaskEX\temp\demo.png",draw_template_match(src_img, background_img,False, 0.95))
            break
        thread.adb_manager.swipe(*swipe_cords, 1500)
        time.sleep(1)
    return True


