
import time
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import timedelta

import cv2
import numpy as np
from pytesseract import pytesseract
from config.settings import get_strict_monster_match, get_debug_mode
from features.utils.join_rally_helper_utils import crop_middle_portion, crop_image_fixed_height, crop_boss_text_area, \
    extract_monster_name_from_image, lookup_boss_by_name
from utils.get_controls_info import get_join_rally_controls
from utils.helper_utils import parse_timer_to_timedelta, get_current_datetime_string
from utils.image_recognition_utils import is_template_match, draw_template_match, template_match_coordinates_all, \
    template_match_coordinates, detect_red_color
from utils.navigate_utils import navigate_join_rally_window
from utils.text_extraction_util import extract_remaining_rally_time_from_image, extract_join_rally_time_from_image, \
    extract_monster_power_from_image, extract_remaining_rally_time_text


def run_join_rally(thread):
    # Get the controls and store it in the thread cache
    if 'join_rally_controls' not in thread.cache:
        thread.cache['join_rally_controls'] = get_join_rally_controls(thread.main_window, thread.index)
    # print(thread.cache['join_rally_controls']['settings']['join_oldest_rallies_first'])
    join_oldest_rallies_first = thread.cache['join_rally_controls']['settings']['join_oldest_rallies_first']
    # Set the rally joining position based on the oldest rallies checkbox value
    scroll_through_rallies(thread,join_oldest_rallies_first,5,True)
    # Switch the swipe direction after setting up the join_oldest_rallies_first option
    swipe_direction = False if join_oldest_rallies_first else True

    swipe_iteration  = 0
    max_swipe_iteration  = 0
    # Initialize runtime cache for rally scanning and preset rotation
    thread.cache['join_rally_controls'].setdefault('cache', {}).setdefault('skipped_monster_cords_img', [])
    thread.cache['join_rally_controls']['cache'].setdefault('previous_preset_number', None)

    while thread.thread_status():
        try:
            # Process boss monster rallies
            process_monster_rallies(thread,join_oldest_rallies_first)
            thread.log_message(
                f"Swipe Direction: {swipe_direction} :: iteration: {swipe_iteration} itr cap: {max_swipe_iteration}",
                "debug",
                console=False
            )

            # Swipe based on the direction
            scroll_through_rallies(thread, swipe_direction)

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
                thread.cache['join_rally_controls']['cache']['skipped_monster_cords_img'] = []
                # Press back
                thread.adb_manager.press_back()
                time.sleep(1)
                if not navigate_join_rally_window(thread):
                    break
                # Update the swipe to scroll down
                swipe_direction = True
                max_swipe_iteration = 0
        except Exception as e:
            thread.log_message(f"Join rally loop error: {e}", "warning", force_console=True)
            thread.log_message(f"Traceback: {traceback.format_exc()}", "debug", force_console=False)

def process_monster_rallies(thread,scan_direction):

    rally_cords = get_valid_rallies_area_cords(thread)
    # Reorder the cords based on the scan direction
    if scan_direction:
        rally_cords.reverse()
    # print(rally_cords)
    for cords in rally_cords:
        # Recapture the  screen
        src_img = thread.capture_and_validate_screen(ads=False)
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

        # Scan rally details
        rally_info = scan_rally_info(thread,roi_src)

        if not rally_info:
            thread.log_message("Rally detail scan failed, returning to list.", "warning", force_console=True)
            thread.adb_manager.press_back()
            time.sleep(1)
            continue

        # Proceed to join the rally
        join_alliance_war_btn_img = cv2.imread("assets/540p/join_rally/join_alliance_war_btn.png")
        fallback_join_btn_img = cv2.imread("assets/540p/join_rally/join_btn.png")
        join_alliance_war_btn_match = None
        for attempt in range(2):
            rally_detail_img = thread.capture_and_validate_screen(ads=False)
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
            if rally_detail_img is not None:
                fallback_x = int(rally_detail_img.shape[1] * 0.50)
                fallback_y = int(rally_detail_img.shape[0] * 0.93)
                join_alliance_war_btn_match = (fallback_x, fallback_y)
                thread.log_message(
                    f"Join template not found; using centered fallback at {join_alliance_war_btn_match}.",
                    "warning",
                    force_console=True
                )
            else:
                thread.log_message(
                    "Join Alliance War button not found in rally detail screen. Skipping this rally.",
                    "warning",
                    force_console=True
                )
                thread.adb_manager.press_back()
                time.sleep(1)
                continue
        
        thread.log_message("Tapping join button...", "debug", force_console=False)
        thread.adb_manager.tap(*join_alliance_war_btn_match)
        
        # Wait for march selection dialog to appear
        time.sleep(1.5)
        
        # Apply march preset from the joined rally controls
        if not handle_march_selection_dialog(thread, rally_info):
            thread.log_message("March selection dialog handling failed, pressing back.", "warning", force_console=True)
            thread.adb_manager.press_back()
            time.sleep(1)
            continue
        
        thread.log_message("Rally joined successfully.", "info", force_console=True)
        time.sleep(1)


def add_rally_cord_to_skip_list(thread, src_img):
    """Add rally snippet to skip-cache and keep cache bounded."""
    if src_img is None or src_img.size == 0:
        return

    cache = thread.cache['join_rally_controls']['cache'].setdefault('skipped_monster_cords_img', [])
    cache.append(src_img.copy())

    if len(cache) > 30:
        del cache[:-30]




def handle_march_selection_dialog(thread, rally_info):
    """
    Handle the march selection dialog that appears after clicking join.
    Apply presets (troops reset, general selection) and confirm the join.
    """
    try:
        thread.log_message("March dialog: starting march dialog handler", "info", force_console=True)
        
        # Wait a bit more for dialog to fully render
        time.sleep(1)
        
        debug_mode = get_debug_mode()

        # Capture screen and save for reference
        march_dialog_screen = thread.capture_and_validate_screen(ads=False)
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
            thread.log_message("Waiting for march result...", "debug", force_console=False)
            time.sleep(1.2)

            stamina_prompt_result = handle_stamina_prompt_and_recover(thread)
            if stamina_prompt_result is False:
                thread.log_message("Stamina prompt detected but handling failed.", "warning", force_console=True)
                return False
            if stamina_prompt_result is True:
                thread.log_message("Stamina prompt handled and rally flow recovered.", "info", force_console=True)
                return True

            time.sleep(1.8)
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
        h, w = screen.shape[:2]
        x1 = int(w * 0.12)
        x2 = int(w * 0.88)
        y1 = int(h * 0.24)
        y2 = int(h * 0.72)
        roi = screen[y1:y2, x1:x2]

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
    h, w = screen.shape[:2]
    roi_x1 = int(w * 0.48)
    roi_x2 = int(w * 0.95)
    roi_y1 = int(h * 0.54)
    roi_y2 = int(h * 0.90)

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
    h, w = screen.shape[:2]
    roi_x1 = int(w * 0.20)
    roi_x2 = int(w * 0.80)
    roi_y1 = int(h * 0.78)
    roi_y2 = int(h * 0.98)

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


def handle_stamina_screen(thread, stamina_option):
    """Tap stamina option (Min/Max), use it, then return to rally window."""
    try:
        screen = thread.capture_and_validate_screen(ads=False)
        if screen is None:
            return False

        h, w = screen.shape[:2]
        option_normalized = (stamina_option or "").lower()
        if "max" in option_normalized:
            option_x = int(w * 0.70)
        else:
            option_x = int(w * 0.30)
        option_y = int(h * 0.52)

        thread.log_message(
            f"Selecting stamina option '{stamina_option}' at ({option_x}, {option_y}).",
            "info",
            force_console=True
        )
        thread.adb_manager.tap(option_x, option_y)
        time.sleep(0.5)

        use_screen = thread.capture_and_validate_screen(ads=False)
        if use_screen is None:
            return False

        use_btn = find_stamina_screen_use_button(use_screen)
        if use_btn:
            thread.log_message(f"Tapping stamina use button at {use_btn}", "info", force_console=True)
            thread.adb_manager.tap(*use_btn)
        else:
            fallback_use = (int(w * 0.50), int(h * 0.92))
            thread.log_message(
                f"Could not detect stamina use button, tapping fallback at {fallback_use}.",
                "warning",
                force_console=True
            )
            thread.adb_manager.tap(*fallback_use)

        time.sleep(1.2)

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

        roi_x1 = int(screen_width * 0.58)
        roi_x2 = int(screen_width * 0.98)
        roi_y1 = int(screen_height * 0.84)
        roi_y2 = int(screen_height * 0.985)

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
            (int(screen_width * 0.82), int(screen_height * 0.94)),   # RIGHT button - March (445, 905)
            (int(screen_width * 0.5), int(screen_height * 0.88)),    # CENTER - Reset (270, 844) - WRONG!
            (int(screen_width * 0.8), int(screen_height * 0.90)),    # Right side alternative
            (int(screen_width * 0.75), int(screen_height * 0.94)),   # Right side, lower
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

    thread.log_message("Scan rally info: start", "info", force_console=True)

    # Load template images
    boss_monster_flag_img = cv2.imread("assets/540p/join_rally/boss_monster_flag.png")
    map_pinpoint_img = cv2.imread("assets/540p/join_rally/map_pinpoint_tag.png")


    # Capture the current screen
    thread.log_message("Scan rally info: capture screen", "info", force_console=True)
    src_img = thread.capture_and_validate_screen(ads=False)
    thread.log_message("Scan rally info: screen captured", "info", force_console=True)

    # Make sure the rally is in progress
    if not is_template_match(src_img,boss_monster_flag_img):
        thread.log_message("Rally detail rejected: boss monster flag not found.", "warning", force_console=True)
        return False
    # Make sure there is enough time to join the rally
    thread.log_message("Scan rally info: reading remaining time", "info", force_console=True)
    try:
        remaining_time = get_remaining_rally_time(src_img, thread)
    except Exception as e:
        thread.log_message(
            f"Rally detail rejected: remaining time OCR error ({e}).",
            "warning",
            force_console=True
        )
        return False
    thread.log_message(f"Scan rally info: remaining time={remaining_time}", "info", force_console=True)
    if not remaining_time:
        thread.log_message("Rally detail rejected: remaining time unreadable.", "warning", force_console=True)
        return False
    # Check whether the timer is above 5 mins
    if remaining_time > timedelta(minutes=5):
        thread.log_message(f"Rally detail rejected: remaining time too high ({remaining_time}).", "info", force_console=True)
        add_rally_cord_to_skip_list(thread, roi_src)
        return False
    # Get the Timer on the join rally button TODO fix the code to extract the correct timer always
    thread.log_message("Scan rally info: reading march time", "info", force_console=True)
    march_time = get_march_join_time(roi_src)
    thread.log_message(f"Scan rally info: march time={march_time}", "info", force_console=True)
    if not march_time:
        thread.log_message("Rally detail rejected: invalid march time.", "warning", force_console=True)
        add_rally_cord_to_skip_list(thread, roi_src)
        return False
    thread.log_message(f"Remaining Time: {remaining_time} :: March Time {march_time}", "info", force_console=True)
    # Add buffer time to march time
    total_march_time = march_time + timedelta(seconds=10)
    thread.log_message(f"Total march time {total_march_time}", "info", force_console=True)
    # Check if march time + buffer is within remaining rally time
    if total_march_time >= remaining_time:
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
        thread.log_message("Rally detail rejected: monster not in join list.", "warning", force_console=True)
        return False

    return True

def read_monster_data(thread,src_img):
    # monster_power_icon_img = cv2.imread("assets/540p/join_rally/monster_power_icon.png")

    boss_text_img = crop_boss_text_area(src_img)
    # cv2.imwrite(fr"E:\Projects\PyCharmProjects\TaskEX\temp\boss_text_img_{get_current_datetime_string()}.png",boss_text_img)
# cv2.imwrite(fr"E:\Projects\PyCharmProjects\TaskEX\temp\src_img_{get_current_datetime_string()}.png",src_img)

    # Get the text from the image
    extracted_monster_name = extract_monster_name_from_image(boss_text_img)
    thread.log_message(f"Extracted Text: {extracted_monster_name}", "debug", console=False)

    # Check and skip dawn monster
    if "dawn" in extracted_monster_name:
        # print("Skipping Dawn Monsters")
        return None



    # Get the all the matching boss objects from the extracted text
    bosses = lookup_boss_by_name(extracted_monster_name)

    if not bosses:
        # print("Cannot find the boss in the db \ read wrong name")
        return None

    return bosses

def verify_monster_join(thread,extracted_boss_data):
    if not extracted_boss_data:
        return False

    selected_boss_levels = thread.cache['join_rally_controls'].get('data', {})
    if not selected_boss_levels:
        return False

    src_img = thread.capture_and_validate_screen(ads=False)
    extracted_power_text = extract_monster_power_from_image(src_img.copy()) if src_img is not None else ""
    extracted_power = (extracted_power_text or "").strip().lower()

    for boss, logic in extracted_boss_data:
        selected_levels = selected_boss_levels.get(boss.boss_monster_id)
        if not selected_levels:
            continue

        if logic in (1, 3):
            if len(extracted_boss_data) == 1 and boss.id in selected_levels:
                return True
            continue

        if logic in (2, 4):
            boss_power = (boss.power or "").strip().lower()
            if extracted_power and boss_power == extracted_power and boss.id in selected_levels:
                return True

    return False




def get_march_join_time(src_img):
    join_btn = cv2.imread("assets/540p/join_rally/join_btn.png")
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

    # Skip if join time text is red (already too late)
    if detect_red_color(src_img):
        return False

    return parse_timer_to_timedelta(extract_join_rally_time_from_image(src_img))


def _extract_remaining_time_text_with_timeout(src_img, timeout_sec=5):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(extract_remaining_rally_time_from_image, src_img)
        try:
            return future.result(timeout=timeout_sec)
        except TimeoutError:
            return None


def get_remaining_rally_time(src_img, thread=None):
    # Crop the image row wise 3 times and retain the middle portion
    src_img = crop_middle_portion(src_img,True)
    # Crop the image column wise 3 times and retain the middle portion
    src_img = crop_middle_portion(src_img,False)
    # Crop the image with a fixed height of 50 pixels to extract just the timer portion
    src_img = crop_image_fixed_height(src_img,50)

    remaining_text = _extract_remaining_time_text_with_timeout(src_img, timeout_sec=1)
    if not remaining_text:
        remaining_time = None
    else:
        remaining_time = parse_timer_to_timedelta(remaining_text)

    if remaining_time is None and thread is not None:
        try:
            if remaining_text is None:
                thread.log_message(
                    "Remaining time OCR timed out.",
                    "warning",
                    force_console=True
                )
            raw_text = extract_remaining_rally_time_text(src_img)
            timestamp = get_current_datetime_string()
            os.makedirs("temp", exist_ok=True)
            raw_path = os.path.join("temp", f"rally_time_raw_{timestamp}.png")
            cv2.imwrite(raw_path, src_img)
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
    for cords_img in thread.cache['join_rally_controls']['cache']['skipped_monster_cords_img']:
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
    boss_monster_tag_img = cv2.imread("assets/540p/join_rally/boss_monster_tag.png")
    join_btn_img = cv2.imread("assets/540p/join_rally/join_btn.png")
    map_pinpoint_img = cv2.imread("assets/540p/join_rally/map_pinpoint_tag.png")

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
    # If the join oldest rally is not checked, then skip this.
    if initial_swipe and not swipe_direction:
        return True
    # Load the template image
    background_img = cv2.imread("assets/540p/join_rally/alliance_war_window_background.png")
    for i in range(swipe_limit):
        # Check if there is any rallies to scroll through
        src_img = thread.capture_and_validate_screen(ads=False)
        if is_template_match(src_img, background_img,False, 0.95):
            # print("No more rallies in the list")
            # cv2.imwrite(r"E:\Projects\PyCharmProjects\TaskEX\temp\demo.png",draw_template_match(src_img, background_img,False, 0.95))
            break
        thread.adb_manager.swipe(*swipe_cords, 1500)
        time.sleep(1)
    return True


