import re
import time

import cv2
import numpy as np

from utils.image_recognition_utils import is_template_match, template_match_coordinates, template_match_coordinates_all


def _nav_log(thread, message, level="debug"):
    try:
        thread.log_message(f"[Navigation] {message}", level, force_console=True)
    except Exception:
        pass


def _load_template(path, thread):
    template = cv2.imread(path)
    if template is None:
        _nav_log(thread, f"Template not found or unreadable: {path}", "warning")
    return template


def _load_optional_template(path):
    return cv2.imread(path)


def _find_standard_dialog_button(screen, template_paths, hsv_ranges, min_area=1200):
    if isinstance(template_paths, str):
        template_paths = [template_paths]

    for template_path in template_paths:
        template = _load_optional_template(template_path)
        if template is not None:
            match = template_match_coordinates(screen, template, threshold=0.78)
            if match:
                return match

    hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
    mask = None
    for lower, upper in hsv_ranges:
        part = cv2.inRange(hsv, np.array(lower), np.array(upper))
        mask = part if mask is None else cv2.bitwise_or(mask, part)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area or w < 70 or h < 20:
            continue
        candidates.append((area, x + w // 2, y + h // 2))

    if not candidates:
        return None

    _, center_x, center_y = max(candidates, key=lambda item: item[0])
    return center_x, center_y


def find_dialog_confirm_button(screen):
    return _find_standard_dialog_button(
        screen,
        [
            'assets/540p/dialogs/confirm_btn.png',
            'assets/540p/dialogs/use_btn.png',
        ],
        hsv_ranges=[([70, 80, 100], [100, 255, 255])],
        min_area=1200,
    )


def _is_exit_game_prompt(screen):
    """Detect the specific 'Are you sure you want to exit the game?' prompt."""
    try:
        from pytesseract import pytesseract

        img_h, img_w = screen.shape[:2]
        x1 = int(img_w * 0.10)
        y1 = int(img_h * 0.42)
        x2 = int(img_w * 0.90)
        y2 = int(img_h * 0.62)
        roi = screen[y1:y2, x1:x2]
        if roi is None or roi.size == 0:
            return False

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        enlarged = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        text = pytesseract.image_to_string(enlarged, config='--psm 6').strip().lower()
        return 'exit the game' in text or ('are you sure' in text and 'exit' in text)
    except Exception:
        return False


def find_dialog_cancel_button(screen):
    return _find_standard_dialog_button(
        screen,
        'assets/540p/dialogs/cancel_btn.png',
        hsv_ranges=[([0, 80, 90], [20, 255, 255]), ([160, 80, 90], [180, 255, 255])],
        min_area=1200,
    )


def tap_dialog_confirm_button(thread, screen=None):
    if screen is None:
        screen = thread.capture_and_validate_screen(ads=False)
    if screen is None:
        return False

    if _is_exit_game_prompt(screen):
        _nav_log(thread, "Exit-game prompt detected while confirming dialog; pressing Cancel instead.", "warning")
        return tap_dialog_cancel_button(thread, screen=screen)

    confirm_btn = find_dialog_confirm_button(screen)
    if not confirm_btn:
        return False

    thread.adb_manager.tap(*confirm_btn)
    time.sleep(0.8)
    _nav_log(thread, f"Tapped dialog confirm button at {confirm_btn}")
    return True


def tap_dialog_cancel_button(thread, screen=None):
    if screen is None:
        screen = thread.capture_and_validate_screen(ads=False)
    if screen is None:
        return False

    cancel_btn = find_dialog_cancel_button(screen)
    if not cancel_btn:
        return False

    thread.adb_manager.tap(*cancel_btn)
    time.sleep(0.8)
    _nav_log(thread, f"Tapped dialog cancel button at {cancel_btn}")
    return True


def tap_back_button_full_screen(thread, back_icon_coords=(40, 105)):
    """
    Tap the back button for full-screen panels (like City Buff, Use Item).
    The back button is the top-left circle icon in the HUD.
    
    Args:
        thread: Emulator thread
        back_icon_coords: Tuple (x, y) for the back icon; default is (40, 105) for HUD icon
    
    Returns:
        True if back button was tapped, False otherwise
    """
    try:
        thread.adb_manager.tap(back_icon_coords[0], back_icon_coords[1])
        time.sleep(0.8)
        _nav_log(thread, f"Tapped back button at {back_icon_coords}")
        return True
    except Exception as e:
        _nav_log(thread, f"Failed to tap back button: {e}", "warning")
        return False


def press_back_with_exit_guard(thread, wait_seconds=0.8):
    """
    Press Android BACK, then cancel the "exit game" prompt if it appears.

    This protects retreat flows from backing out too far while still allowing
    normal in-game screen unwinding.
    """
    try:
        thread.adb_manager.press_back()
        time.sleep(wait_seconds)

        screen = thread.capture_and_validate_screen(ads=False)
        if screen is not None and tap_dialog_cancel_button(thread, screen=screen):
            _nav_log(thread, "Detected exit-game prompt after BACK; tapped Cancel.", "warning")
            return True
        return True
    except Exception as e:
        _nav_log(thread, f"Safe BACK failed: {e}", "warning")
        return False


def _get_top_right_popup_close_points(src_img):
    """Candidate taps for the common circular close button in the top-right popup corner."""
    img_h, img_w = src_img.shape[:2]
    return [
        (int(img_w * 0.93), int(img_h * 0.075)),
        (int(img_w * 0.91), int(img_h * 0.085)),
        (int(img_w * 0.95), int(img_h * 0.065)),
    ]


def tap_top_right_popup_close(thread, src_img=None):
    """
    Tap the common circular X close button shown in the top-right corner of many popups.
    """
    try:
        if src_img is None:
            src_img = thread.capture_and_validate_screen(ads=False)
        if src_img is None:
            return False

        img_h, img_w = src_img.shape[:2]
        x1 = int(img_w * 0.78)
        y1 = 0
        x2 = img_w
        y2 = int(img_h * 0.20)
        roi = src_img[y1:y2, x1:x2]
        if roi is not None and roi.size > 0:
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower_warm1 = np.array([0, 70, 80])
            upper_warm1 = np.array([20, 255, 255])
            lower_warm2 = np.array([160, 70, 80])
            upper_warm2 = np.array([180, 255, 255])
            mask1 = cv2.inRange(hsv, lower_warm1, upper_warm1)
            mask2 = cv2.inRange(hsv, lower_warm2, upper_warm2)
            mask = cv2.bitwise_or(mask1, mask2)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            candidates = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                if area < 250 or w < 20 or h < 20:
                    continue
                if abs(w - h) > max(10, int(max(w, h) * 0.35)):
                    continue
                candidates.append((area, x, y, w, h))

            if candidates:
                _, x, y, w, h = max(candidates, key=lambda item: item[0])
                tap_x = x1 + x + w // 2
                tap_y = y1 + y + h // 2
                thread.adb_manager.tap(tap_x, tap_y)
                time.sleep(0.8)
                _nav_log(thread, f"Closed popup via top-right circular X at ({tap_x}, {tap_y})")
                return True

        for tap_x, tap_y in _get_top_right_popup_close_points(src_img):
            thread.adb_manager.tap(tap_x, tap_y)
            time.sleep(0.8)
            _nav_log(thread, f"Tapped top-right popup close fallback at ({tap_x}, {tap_y})")
            return True
    except Exception as e:
        _nav_log(thread, f"Error tapping top-right popup close button: {e}", "warning")
    return False


def find_and_close_popup_via_red_x(thread, max_attempts=3):
    """
    Find and close small popup/modal UI elements by tapping one of the known close buttons.
    Tries red X detection first, then the common top-right circular X button.
    
    Args:
        thread: Emulator thread
        max_attempts: Number of close attempts before giving up
    
    Returns:
        True if popup was closed, False if no red X found or close failed
    """
    try:
        for _ in range(max_attempts):
            src_img = thread.capture_and_validate_screen(ads=False)
            if src_img is None:
                return False

            hsv = cv2.cvtColor(src_img, cv2.COLOR_BGR2HSV)
            lower_red1 = np.array([0, 80, 120])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 80, 120])
            upper_red2 = np.array([180, 255, 255])

            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                largest = max(contours, key=cv2.contourArea)
                M = cv2.moments(largest)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    thread.adb_manager.tap(cx, cy)
                    time.sleep(0.8)
                    _nav_log(thread, f"Closed popup via red X at ({cx}, {cy})")
                    return True

            if tap_top_right_popup_close(thread, src_img=src_img):
                return True

        _nav_log(thread, "No popup close button found on screen.", "debug")
    except Exception as e:
        _nav_log(thread, f"Error finding/closing red X popup: {e}", "warning")
    
    return False


def confirm_bubble_activation_dialogs(thread, max_dialogs=2):
    """
    Confirm bubble activation dialogs by tapping the green confirm buttons.
    
    There can be 1-2 dialogs:
    - Scenario 1 (no active bubble): Only 1 dialog (second confirmation)
    - Scenario 2 (active bubble exists): 2 dialogs (confirm replacement, then confirm activation)
    
    Args:
        thread: Emulator thread
        max_dialogs: Maximum number of dialogs to expect (default 2)
    
    Returns:
        True if at least one dialog was confirmed, False if no dialogs found
    """
    try:
        confirmed_count = 0
        
        for attempt in range(max_dialogs):
            time.sleep(0.5)  # Wait for dialog to appear
            
            src_img = thread.capture_and_validate_screen(ads=False)
            if src_img is None:
                break

            if _is_exit_game_prompt(src_img):
                _nav_log(thread, "Exit-game prompt detected during bubble dialog handling; tapping Cancel.", "warning")
                tap_dialog_cancel_button(thread, screen=src_img)
                return False

            confirm_btn = find_dialog_confirm_button(src_img)
            if not confirm_btn:
                _nav_log(thread, f"Dialog {attempt + 1}: No green confirm button detected (may be end of sequence).", "debug")
                break

            thread.adb_manager.tap(*confirm_btn)
            confirmed_count += 1
            _nav_log(thread, f"Dialog {attempt + 1}: Confirmed bubble activation at {confirm_btn}")
            time.sleep(0.8)
        
        return confirmed_count > 0
    except Exception as e:
        _nav_log(thread, f"Error confirming bubble activation dialogs: {e}", "warning")
        return False


def _parse_bubble_remaining_minutes(text):
    normalized = re.sub(r'[^a-z0-9: ]+', ' ', (text or '').lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    if not normalized:
        return None

    day_match = re.search(r'(\d+)\s*d[a-z]*\s*(\d{1,3})[:h]\s*(\d{1,2})', normalized)
    if day_match:
        days = int(day_match.group(1))
        hours = int(day_match.group(2))
        minutes = int(day_match.group(3))
        return days * 1440 + hours * 60 + minutes

    hms_match = re.search(r'(\d{1,3})\s*:\s*(\d{1,2})(?:\s*:\s*(\d{1,2}))?', normalized)
    if hms_match:
        hours = int(hms_match.group(1))
        minutes = int(hms_match.group(2))
        return hours * 60 + minutes

    hm_match = re.search(r'(\d{1,3})\s*h\s*(\d{1,2})', normalized)
    if hm_match:
        hours = int(hm_match.group(1))
        minutes = int(hm_match.group(2))
        return hours * 60 + minutes

    return None


def _read_use_item_remaining_banner(thread, src_img=None):
    if src_img is None:
        src_img = thread.capture_and_validate_screen(ads=False)
    if src_img is None:
        return None, ''

    img_h, img_w = src_img.shape[:2]
    x1 = int(img_w * 0.04)
    y1 = int(img_h * 0.06)
    x2 = int(img_w * 0.96)
    y2 = int(img_h * 0.16)
    roi = src_img[y1:y2, x1:x2]
    if roi is None or roi.size == 0:
        return None, ''

    from pytesseract import pytesseract

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9
    )
    variants = [roi, gray, thresh, adaptive]
    configs = ['--psm 7', '--psm 6', '--psm 13']

    observed_minutes = None
    best_text = ''
    for variant in variants:
        enlarged = cv2.resize(variant, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        for config in configs:
            text = pytesseract.image_to_string(enlarged, config=config).strip()
            parsed_minutes = _parse_bubble_remaining_minutes(text)
            if parsed_minutes is not None:
                return parsed_minutes, text
            if len(text) > len(best_text):
                best_text = text

    return observed_minutes, best_text


def verify_bubble_activation_remaining_time(thread, bubble, previous_minutes=None, previous_text='', tolerance_minutes=5, timeout_seconds=60):
    """
    Verify the Use Item top banner shows a timer close to the selected bubble duration.

    Example: after activating a 24h bubble, a banner like 23:58:51 is valid.
    A previous timer may be absent when no bubble was active before activation.
    If a previous timer exists, the new timer must also change from the previous value.
    In all cases, a successful activation must produce a new visible timer within the timeout.
    """
    try:
        expected_minutes = int(getattr(bubble, 'duration_hours', 0) or 0) * 60
        if expected_minutes <= 0:
            return False

        deadline = time.time() + max(1, timeout_seconds)
        latest_minutes = None
        latest_text = ''
        lower_bound = max(0, expected_minutes - tolerance_minutes)
        upper_bound = expected_minutes + 1
        had_previous_timer = bool((previous_text or '').strip()) or previous_minutes is not None

        while time.time() < deadline:
            observed_minutes, observed_text = _read_use_item_remaining_banner(thread)
            if observed_text:
                latest_text = observed_text
            if observed_minutes is not None:
                latest_minutes = observed_minutes
                timer_changed = True
                if previous_text:
                    timer_changed = observed_text.strip().lower() != previous_text.strip().lower()
                elif previous_minutes is not None:
                    timer_changed = observed_minutes != previous_minutes

                if lower_bound <= observed_minutes <= upper_bound and timer_changed:
                    _nav_log(
                        thread,
                        f"Bubble '{bubble.name}' verified via Use Item timer: {observed_minutes} min observed vs {expected_minutes} min expected.",
                    )
                    return True
            time.sleep(2.0)

        if latest_minutes is None:
            _nav_log(thread, f"Bubble '{bubble.name}' activation check failed: no timer appeared within {timeout_seconds}s. Last OCR: {latest_text}", "warning")
            return False

        if previous_text and latest_text.strip().lower() == previous_text.strip().lower():
            _nav_log(thread, f"Bubble '{bubble.name}' activation check failed: timer did not change from previous value ({latest_text}).", "warning")
            return False
        if previous_minutes is not None and latest_minutes == previous_minutes:
            _nav_log(thread, f"Bubble '{bubble.name}' activation check failed: timer stayed at {latest_minutes} min.", "warning")
            return False

        if not had_previous_timer:
            _nav_log(thread, f"Bubble '{bubble.name}' activation check saw a new timer, but it did not land within the expected duration window.", "warning")
            return False

        _nav_log(
            thread,
            f"Bubble '{bubble.name}' activation timer mismatch after waiting {timeout_seconds}s. Banner OCR: {latest_text} | observed={latest_minutes} min | expected={expected_minutes} min.",
            "warning",
        )
        return False
    except Exception as e:
        _nav_log(thread, f"Error verifying bubble activation timer: {e}", "warning")
        return False


def validate_screen_or_retreat(thread, validation_func, back_button_coords=(40, 105), screen_name="Unknown"):
    """
    Validate that a screen is correct. If validation fails, retreat (tap back button).
    
    Args:
        thread: Emulator thread
        validation_func: Callable that returns True if screen is correct, False otherwise
        back_button_coords: Coords to tap if screen is wrong
        screen_name: Name of expected screen (for logging)
    
    Returns:
        True if screen is valid, False if invalid (and retreated)
    """
    try:
        if validation_func(thread):
            _nav_log(thread, f"Screen validation passed: {screen_name}", "debug")
            return True
        else:
            _nav_log(thread, f"Screen validation failed for '{screen_name}'; retreating.", "warning")
            tap_back_button_full_screen(thread, back_button_coords)
            return False
    except Exception as e:
        _nav_log(thread, f"Error during screen validation: {e}", "warning")
        tap_back_button_full_screen(thread, back_button_coords)
        return False


def navigate_generals_window(thread):
    generals_btn_img = cv2.imread('assets/540p/other/generals_window_btn.png')
    menu_btn_img = cv2.imread('assets/540p/other/three_dots_menu_btn.png')

    # Make sure its inside the shared HUD start screen
    if not ensure_shared_feature_start_screen(thread):
        return False
    # Take the ss
    src_img = thread.capture_and_validate_screen()

    # Check if menu button is present
    menu_btn_match = template_match_coordinates(src_img, menu_btn_img)
    if menu_btn_match:
        # Check if Generals button is already visible
        generals_btn_match = template_match_coordinates(src_img, generals_btn_img)
        if generals_btn_match:
            thread.adb_manager.tap(generals_btn_match[0], generals_btn_match[1])
            time.sleep(1)
            return True
        else:
            # Tap the 3-dots menu button to reveal options
            thread.adb_manager.tap(menu_btn_match[0], menu_btn_match[1])
            time.sleep(1)
            # Capture a new screenshot
            src_img = thread.capture_and_validate_screen()
            # Recheck for the Generals button
            generals_btn_match = template_match_coordinates(src_img, generals_btn_img)
            if generals_btn_match:
                # Tap the Generals button and return success
                thread.adb_manager.tap(generals_btn_match[0], generals_btn_match[1])
                time.sleep(1)
                return True
    # Return failure if the Generals window could not be opened
    return False

def navigate_join_rally_window(thread):
    # Check if it already opened the right window by checking for the battle logs button and verify the options selected
    inside_alliance_war = ensure_and_setup_pvp_war_window_screen(thread)
    # Else, then make sure the game screen is inside alliance city or world map
    if inside_alliance_war:
        _nav_log(thread, "Already inside Alliance War window.")
        return True
    elif not ensure_shared_feature_start_screen(thread):
        _nav_log(thread, "Cannot ensure Alliance City or World Map before navigating to Join Rally.", "warning")
        return False
    # Take the ss
    src_img = thread.capture_and_validate_screen()

    ongoing_rally_btn_img = _load_template('assets/540p/join_rally/ongoing_rally_btn.png', thread)
    if ongoing_rally_btn_img is None:
        return False
    ongoing_rally_btn_match = template_match_coordinates(src_img,ongoing_rally_btn_img)
    if ongoing_rally_btn_match:
        # Tap the ongoing rally button and return success
        thread.adb_manager.tap(ongoing_rally_btn_match[0], ongoing_rally_btn_match[1])
        time.sleep(1)
        # Now Make sure it opened the right window
        if not ensure_and_setup_pvp_war_window_screen(thread):
            _nav_log(thread, "Tapped Ongoing Rally but failed to verify/setup Alliance War window.", "warning")
            return False
        return True
    # if no ongoing rally, manually navigate to the alliance war window
    _nav_log(thread, "Ongoing Rally button not found; attempting manual navigation via Alliance button.")
    alliance_btn_img = _load_template('assets/540p/other/alliance_btn.png', thread)
    if alliance_btn_img is None:
        return False
    alliance_btn_match = template_match_coordinates(src_img, alliance_btn_img)
    if not alliance_btn_match:
        _nav_log(thread, "Alliance button not found on current screen.", "warning")
        return False
    # Tap the alliance button
    thread.adb_manager.tap(alliance_btn_match[0], alliance_btn_match[1])
    time.sleep(1)
    src_img = thread.capture_and_validate_screen()
    alliance_war_window_option_img = _load_template('assets/540p/join_rally/alliance_war_window_option.png', thread)
    if alliance_war_window_option_img is None:
        return False
    alliance_war_window_option_match = template_match_coordinates(src_img, alliance_war_window_option_img)
    if not alliance_war_window_option_match:
        _nav_log(thread, "Alliance War window option not found after opening Alliance panel.", "warning")
        return False
    # Tap the alliance war window icon
    thread.adb_manager.tap(alliance_war_window_option_match[0], alliance_war_window_option_match[1])
    time.sleep(1)
    # src_img = thread.capture_and_validate_screen()
    if ensure_and_setup_pvp_war_window_screen(thread):
        return True
    else:
        _nav_log(thread, "Alliance War option tapped, but final window verification failed.", "warning")
        return False

def ensure_and_setup_pvp_war_window_screen(thread):
    alliance_war_window_tag_img = _load_template('assets/540p/join_rally/alliance_war_window_tag.png', thread)
    battle_logs_btn_img = _load_template('assets/540p/join_rally/battle_logs_btn.png', thread)
    pvp_war_tab_img = _load_template('assets/540p/join_rally/pvp_war_tab.png', thread)
    if alliance_war_window_tag_img is None or battle_logs_btn_img is None or pvp_war_tab_img is None:
        return False
    src_img = thread.capture_and_validate_screen()
    # Make sure it opened the right window, return false it not
    if not is_template_match(src_img, alliance_war_window_tag_img):
        _nav_log(thread, "Alliance War window tag not detected.")
        return False
    # Make sure battle logs button is present
    if not is_template_match(src_img, battle_logs_btn_img):
        _nav_log(thread, "Battle Logs button missing; attempting to switch to PvP War tab.")
        pvp_war_tab_match = template_match_coordinates(src_img,pvp_war_tab_img)
        if pvp_war_tab_match:
            # print("Moving to pvp war window")
            thread.adb_manager.tap(pvp_war_tab_match[0], pvp_war_tab_match[1])
            time.sleep(1)
            src_img = thread.capture_and_validate_screen()
        else:
            _nav_log(thread, "PvP War tab button not found.")

    # Check again if the battle logs button is present, if not then return false
    if not is_template_match(src_img, battle_logs_btn_img):
        _nav_log(thread, "Battle Logs button still not detected after PvP tab handling.")
        return False
    # Now verify only Monster War option is selected
    war_checked_img = _load_template('assets/540p/join_rally/war_checked.png', thread)
    war_unchecked_img = _load_template('assets/540p/join_rally/war_unchecked.png', thread)
    if war_checked_img is None or war_unchecked_img is None:
        return False

    # Crop the monster war and war option checkbox image area
    src_img_height,src_img_width,_ = src_img.shape

    # Calculate the height and width of src_image to crop
    piece_height = src_img_height // 5
    piece_width = src_img_width // 3

    # Extract the top piece (cropping the src image 5 times horizontally and take the top piece)
    top_piece = src_img[:piece_height, :, :]

    # Extract the first 2 pieces from the top_piece(cropping the top_piece 3 times vertically)
    monster_war_checkbox_src_img = top_piece[:, :piece_width, :]
    war_checkbox_src_img = top_piece[:, piece_width:2 * piece_width, :]

    # Check if monster war checkbox is checked or not, then check it if needed
    if is_template_match(monster_war_checkbox_src_img,war_unchecked_img):
        # print("Monster war option is not checked")
        # Check the monster war checkbox
        monster_war_checkbox_match = template_match_coordinates(monster_war_checkbox_src_img,war_unchecked_img)
        if monster_war_checkbox_match:
            # print(f"Checking monster war option {monster_war_checkbox_match[0]} {monster_war_checkbox_match[1]}")
            thread.adb_manager.tap(monster_war_checkbox_match[0], monster_war_checkbox_match[1])
            _nav_log(thread, "Enabled Monster War filter.")

    # Uncheck the war checkbox
    if is_template_match(war_checkbox_src_img, war_checked_img):
        # print("War option is checked")
        war_checkbox_match = template_match_coordinates(war_checkbox_src_img,war_checked_img)
        if war_checkbox_match:
            # print("Unchecking the war checkbox")
            thread.adb_manager.tap(war_checkbox_match[0]+piece_width, war_checkbox_match[1])
            _nav_log(thread, "Disabled War filter (kept Monster War only).")
    return True


def ensure_shared_feature_start_screen(thread, allow_city=True, allow_world_map=True):
    """
    Shared starting point for HUD-based features.

    Features that begin from the normal game HUD should first ensure they are on
    either Alliance City or World Map before checking feature-specific UI.
    """
    # Load templates
    ac_btn_img = _load_template(
        'assets/540p/other/explore_alliance_city_btn.png', thread)  # Common for both World Map and Ideal Land
    wm_btn_img = _load_template(
        'assets/540p/other/explore_world_map_btn.png', thread)
    alliance_btn_img = _load_template('assets/540p/other/alliance_btn.png', thread)  # World Map validation

    if ac_btn_img is None or wm_btn_img is None or alliance_btn_img is None:
        return False

    counter = 0
    max_attempts = 15  # Prevent infinite loops

    while counter < max_attempts:
        src_img = thread.capture_and_validate_screen()

        # Check Alliance City
        if allow_city:
            if is_template_match(src_img, wm_btn_img):  # Alliance City detected
                return True
            if not allow_world_map:  # Only Alliance City is required
                press_back_with_exit_guard(thread)
                counter += 1
                continue

        # Check World Map
        if allow_world_map:
            ac_btn_match = template_match_coordinates(src_img, ac_btn_img)  # Check for World Map/Ideal Land
            wm_alliance_match = is_template_match(src_img, alliance_btn_img)

            if ac_btn_match and wm_alliance_match:  # World Map detected
                return True
            elif ac_btn_match and not wm_alliance_match:  # Ideal Land case
                thread.adb_manager.tap(ac_btn_match[0], ac_btn_match[1])  # Navigate to Alliance City
                time.sleep(4)
                continue

        # If neither is detected, press back
        press_back_with_exit_guard(thread)
        counter += 1

    # Failed to ensure desired screen
    _nav_log(thread, "Failed to reach Alliance City/World Map after max back attempts.", "warning")
    return False


def ensure_alliance_city_or_world_map_screen(thread, ac=True, wm=True):
    """Backward-compatible wrapper for the shared feature start screen."""
    return ensure_shared_feature_start_screen(thread, allow_city=ac, allow_world_map=wm)


def navigate_to_world_map(thread):
    """Ensure the game is on World Map."""
    return ensure_shared_feature_start_screen(thread, allow_city=False, allow_world_map=True)


def _get_bubble_status_icon_points(src_img):
    """Tap candidates for the left-most small status circle under the portrait.
    
    Calibrated coordinates for 540x960 device:
    - Primary: (40, 105) - verified to open City Buff panel
    """
    img_h, img_w = src_img.shape[:2]
    return [
        (40, 105),  # Primary: leftmost HUD icon below character portrait
        (40, 115),  # Fallback: slightly lower if primary misses
    ]


def _top_left_panel_changed(before_img, after_img):
    if before_img is None or after_img is None:
        return False

    region_h = min(int(before_img.shape[0] * 0.34), before_img.shape[0])
    region_w = min(int(before_img.shape[1] * 0.48), before_img.shape[1])
    before_crop = before_img[:region_h, :region_w]
    after_crop = after_img[:region_h, :region_w]

    if before_crop.size == 0 or after_crop.size == 0:
        return False

    before_gray = cv2.cvtColor(before_crop, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after_crop, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(before_gray, after_gray)
    return float(np.mean(diff)) >= 4.0


def open_bubble_status_panel(thread):
    """
    Open the City Buff screen from the top-left HUD circle.

    Returns the screenshot after the screen opens, or None on failure.
    """
    if not ensure_shared_feature_start_screen(thread):
        _nav_log(thread, "Cannot open bubble status panel without the shared start screen.", "warning")
        return None

    before_img = thread.capture_and_validate_screen(ads=False)
    if before_img is None:
        return None

    for tap_x, tap_y in _get_bubble_status_icon_points(before_img):
        thread.adb_manager.tap(tap_x, tap_y)
        time.sleep(0.8)
        after_img = thread.capture_and_validate_screen(ads=False)
        if _top_left_panel_changed(before_img, after_img):
            return after_img

    _nav_log(thread, "Top-left bubble status icon did not open the City Buff screen.", "warning")
    return None


def open_bubble_selection_screen(thread, panel_img=None):
    """
    From the City Buff screen, open the bubble list by tapping the
    Truce Agreement row (the first buff card).
    
    Calibrated coordinates for 540x960 device:
    - Truce Agreement row tap: (300, 154) - verified to open Use Item screen
    
    Auto-retreat: If wrong screen opens, taps back button to return to City Buff.
    """
    if panel_img is None:
        panel_img = thread.capture_and_validate_screen(ads=False)
    if panel_img is None:
        return False

    # Tap the Truce Agreement row (center of the row button)
    tap_x = 300
    tap_y = 154

    thread.adb_manager.tap(tap_x, tap_y)
    time.sleep(0.8)
    
    # Validate that we opened the correct screen (Use Item screen with bubble list)
    after_img = thread.capture_and_validate_screen(ads=False)
    if after_img is None:
        return False
    
    # Simple validation: Use Item screen should have significantly different content
    # If the image is almost identical to panel_img, we likely didn't navigate
    if panel_img.shape == after_img.shape:
        diff = cv2.absdiff(panel_img, after_img)
        mean_diff = float(np.mean(diff))
        if mean_diff < 5.0:  # Very similar = wrong screen
            _nav_log(thread, "Truce Agreement tap did not open bubble list; screen unchanged.", "warning")
            return False
    
    return True


def _get_fixed_bubble_row_button_region(thread, src_img, bubble_type_id):
    """
    Bubble list order is fixed on the Use Item screen:
    1 = 8h, 2 = 24h, 3 = 3d, 4 = 7d.

    The 7-day row is partially hidden on first open, so scroll once before targeting it.
    Returns (working_img, (row_y1, row_y2, btn_x1, btn_x2)).
    """
    working_img = src_img
    img_h, img_w = working_img.shape[:2]
    row_slot = bubble_type_id

    if bubble_type_id == 4:
        thread.adb_manager.swipe(int(img_w * 0.50), int(img_h * 0.78), int(img_w * 0.50), int(img_h * 0.48), 450)
        time.sleep(0.8)
        working_img = thread.capture_and_validate_screen(ads=False)
        if working_img is None:
            return None, None
        img_h, img_w = working_img.shape[:2]
        row_slot = 3

    row_centers = {
        1: int(img_h * 0.318),
        2: int(img_h * 0.533),
        3: int(img_h * 0.748),
    }
    center_y = row_centers.get(row_slot)
    if center_y is None:
        return working_img, None

    row_y1 = max(center_y - int(img_h * 0.055), 0)
    row_y2 = min(center_y + int(img_h * 0.055), img_h)
    btn_x1 = min(max(int(img_w * 0.72), 0), img_w - 1)
    btn_x2 = min(int(img_w * 0.97), img_w)
    return working_img, (row_y1, row_y2, btn_x1, btn_x2)


def _select_and_use_bubble_from_current_screen(thread, controls):
    from core.services.bubble_service import get_all_bubble_types

    use_btn = _load_template('assets/540p/bubbles/use_btn.png', thread)

    bubble_type_id = controls.get('bubble_type_id')
    bubble = next((b for b in get_all_bubble_types() if b.id == bubble_type_id), None)
    if bubble is None:
        _nav_log(thread, "Selected bubble type is invalid.", "warning")
        return False

    src_img = thread.capture_and_validate_screen(ads=False)
    if src_img is None:
        return False

    previous_minutes, previous_text = _read_use_item_remaining_banner(thread, src_img=src_img)

    working_img, row_region = _get_fixed_bubble_row_button_region(thread, src_img, bubble_type_id)
    if working_img is None or row_region is None:
        _nav_log(thread, f"Bubble row for '{bubble.name}' could not be determined from fixed order.", "warning")
        return False

    row_y1, row_y2, btn_x1, btn_x2 = row_region
    button_roi = working_img[row_y1:row_y2, btn_x1:btn_x2]
    if button_roi is None or button_roi.size == 0:
        _nav_log(thread, "Bubble action button area is empty.", "warning")
        return False

    use_match = template_match_coordinates(button_roi, use_btn, threshold=0.78) if use_btn is not None else None
    if use_match:
        thread.adb_manager.tap(btn_x1 + use_match[0], row_y1 + use_match[1])
        time.sleep(1)
        # Confirm the activation dialogs (1-2 dialogs depending on active bubble state)
        if confirm_bubble_activation_dialogs(thread, max_dialogs=2):
            if verify_bubble_activation_remaining_time(thread, bubble, previous_minutes=previous_minutes, previous_text=previous_text):
                _nav_log(thread, f"Bubble '{bubble.name}' activated successfully after confirming dialogs.")
                return True
            _nav_log(thread, f"Bubble '{bubble.name}' dialogs confirmed, but remaining-time verification failed.", "warning")
            return False
        else:
            _nav_log(thread, f"Bubble '{bubble.name}' Use button tapped but dialog confirmation failed.", "warning")
            return False

    from pytesseract import pytesseract

    gray = cv2.cvtColor(button_roi, cv2.COLOR_BGR2GRAY)
    _, thresh_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    enlarged = cv2.resize(thresh_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    button_text = pytesseract.image_to_string(enlarged, config='--psm 7').strip().lower()
    if 'use' in button_text:
        thread.adb_manager.tap((btn_x1 + btn_x2) // 2, (row_y1 + row_y2) // 2)
        _nav_log(thread, f"Bubble '{bubble.name}' action button tapped via OCR Use detection.")
        time.sleep(1)
        if confirm_bubble_activation_dialogs(thread, max_dialogs=2):
            if verify_bubble_activation_remaining_time(thread, bubble, previous_minutes=previous_minutes, previous_text=previous_text):
                _nav_log(thread, f"Bubble '{bubble.name}' activated successfully after OCR dialog confirmation.")
                return True
            _nav_log(thread, f"Bubble '{bubble.name}' OCR dialogs confirmed, but remaining-time verification failed.", "warning")
            return False
        _nav_log(thread, f"Bubble '{bubble.name}' OCR Use detection tapped but dialog confirmation failed.", "warning")
        return False

    has_price = bool([token for token in button_text.split() if any(ch.isdigit() for ch in token)])

    if has_price:
        if not controls.get('allow_gem_purchase', False):
            _nav_log(thread, f"Bubble '{bubble.name}' requires gem purchase and gem buying is disabled.", "warning")
            return False

        thread.adb_manager.tap((btn_x1 + btn_x2) // 2, (row_y1 + row_y2) // 2)
        _nav_log(thread, f"Bubble '{bubble.name}' gem-purchase button tapped.")
        time.sleep(1)
        # Confirm the activation dialogs (1-2 dialogs depending on active bubble state)
        if confirm_bubble_activation_dialogs(thread, max_dialogs=2):
            if verify_bubble_activation_remaining_time(thread, bubble, previous_minutes=previous_minutes, previous_text=previous_text):
                _nav_log(thread, f"Bubble '{bubble.name}' purchased and activated successfully after confirming dialogs.")
                return True
            _nav_log(thread, f"Bubble '{bubble.name}' purchase dialogs confirmed, but remaining-time verification failed.", "warning")
            return False
        else:
            _nav_log(thread, f"Bubble '{bubble.name}' gem-purchase tapped but dialog confirmation failed.", "warning")
            return False

    _nav_log(thread, f"No usable action detected for bubble '{bubble.name}'. OCR: {button_text}", "warning")
    return False


def _navigate_to_bubble_use_via_inventory(thread, controls):
    from core.services.bubble_service import get_all_bubble_types

    src_img = thread.capture_and_validate_screen()
    if src_img is None:
        return False

    items_btn = _load_template('assets/540p/bubbles/items_btn.png', thread)
    protection_tab = _load_template('assets/540p/bubbles/protection_tab.png', thread)
    use_btn = _load_template('assets/540p/bubbles/use_btn.png', thread)
    if items_btn is None or protection_tab is None or use_btn is None:
        _nav_log(thread, "Missing base bubble inventory navigation templates.", "warning")
        return False

    item_match = template_match_coordinates(src_img, items_btn)
    if not item_match:
        _nav_log(thread, "Items button not found.", "warning")
        return False
    thread.adb_manager.tap(item_match[0], item_match[1])
    time.sleep(1)

    src_img = thread.capture_and_validate_screen()
    tab_match = template_match_coordinates(src_img, protection_tab)
    if tab_match:
        thread.adb_manager.tap(tab_match[0], tab_match[1])
        time.sleep(1)

    bubble_type_id = controls.get('bubble_type_id')
    bubble = next((b for b in get_all_bubble_types() if b.id == bubble_type_id), None)
    if bubble is None or not bubble.img_540p:
        _nav_log(thread, "Selected bubble type has no configured template.", "warning")
        return False

    bubble_tpl = _load_template(bubble.img_540p, thread)
    if bubble_tpl is None:
        return False

    src_img = thread.capture_and_validate_screen()
    threshold = bubble.img_threshold if bubble.img_threshold else 0.85
    bubble_match = template_match_coordinates(src_img, bubble_tpl, threshold=threshold)
    if not bubble_match:
        _nav_log(thread, f"Bubble template '{bubble.name}' not found on screen.", "warning")
        return False

    thread.adb_manager.tap(bubble_match[0], bubble_match[1])
    time.sleep(0.8)

    src_img = thread.capture_and_validate_screen()
    use_match = template_match_coordinates(src_img, use_btn, threshold=0.80)
    if not use_match:
        _nav_log(thread, "Use button not found after selecting bubble.", "warning")
        return False

    thread.adb_manager.tap(use_match[0], use_match[1])
    time.sleep(1)
    return True


def navigate_to_bubble_use(thread, controls):
    """
    Use the selected bubble template.

    Preferred path:
      1. Start from the shared city/world-map HUD screen.
      2. Tap the top-left bubble status circle to open City Buff.
      3. Tap Truce Agreement to enter the bubble list screen.
      4. Select and use the bubble.
    
    Auto-retreat on failure:
      - If any step fails, automatically tap back button to safe state
      - Graceful fallback to legacy inventory/protection navigation

    Expected controls keys:
      - bubble_type_id
      - prioritize_existing
      - allow_gem_purchase
    """
    try:
        if not ensure_shared_feature_start_screen(thread):
            _nav_log(thread, "Cannot start bubble navigation: failed to ensure shared HUD.", "warning")
            return False

        # Step 1: Open City Buff panel
        panel_img = open_bubble_status_panel(thread)
        if panel_img is None:
            _nav_log(thread, "Failed to open City Buff panel; retreating to HUD.", "warning")
            return False
        
        # Step 2: Open bubble selection screen
        if not open_bubble_selection_screen(thread, panel_img=panel_img):
            _nav_log(thread, "Failed to open bubble selection screen; retreating to City Buff.", "warning")
            tap_back_button_full_screen(thread)
            time.sleep(0.5)
            return False
        
        # Step 3: Select and use the bubble
        if _select_and_use_bubble_from_current_screen(thread, controls):
            return True
        
        # If bubble selection failed, retreat from Use Item screen
        _nav_log(thread, "Failed to select bubble; retreating from Use Item screen.", "warning")
        tap_back_button_full_screen(thread)
        time.sleep(0.5)
        
        # Attempt retreat from City Buff as well
        tap_back_button_full_screen(thread)
        time.sleep(0.5)
        
        # Fall back to legacy method
        _nav_log(thread, "Falling back to legacy inventory/protection bubble navigation.", "warning")
        return _navigate_to_bubble_use_via_inventory(thread, controls)
    except Exception as e:
        _nav_log(thread, f"navigate_to_bubble_use error: {e}", "warning")
        # Attempt retreat on exception
        try:
            tap_back_button_full_screen(thread)
        except:
            pass
        return False


def scan_resource_tiles_on_map(thread, resource_type_ids, min_level, max_level):
    """
    Find resource tiles using DB-configured templates.
    Returns a list of dicts: {x, y, resource_type_id, level, template_id}
    """
    from core.services.resource_service import get_tile_templates_for_resource

    src_img = thread.capture_and_validate_screen(ads=False)
    if src_img is None:
        return []

    found = []
    seen = set()
    for resource_type_id in resource_type_ids:
        templates = get_tile_templates_for_resource(resource_type_id, min_level=min_level, max_level=max_level)
        for template in templates:
            tpl = _load_template(template.img_540p, thread)
            if tpl is None:
                continue
            matches = template_match_coordinates_all(src_img, tpl, threshold=template.img_threshold or 0.85)
            for x, y in matches:
                key = (int(x / 18), int(y / 18), resource_type_id)
                if key in seen:
                    continue
                seen.add(key)
                found.append({
                    'x': x,
                    'y': y,
                    'resource_type_id': resource_type_id,
                    'level': template.tile_level,
                    'template_id': template.id,
                })

    found.sort(key=lambda t: t['level'], reverse=True)
    return found


def send_gather_march(thread, tile_coords, gather_controls):
    """Tap a tile and dispatch a gather march via configured UI buttons."""
    try:
        x = tile_coords.get('x')
        y = tile_coords.get('y')
        if x is None or y is None:
            return False

        gather_btn = _load_template('assets/540p/gather/gather_btn.png', thread)
        march_confirm_btn = _load_template('assets/540p/gather/march_confirm_btn.png', thread)
        if gather_btn is None or march_confirm_btn is None:
            _nav_log(thread, "Missing gather button templates.", "warning")
            return False

        # Retry tile opening with nearby taps when the popup does not appear immediately.
        gather_match = None
        for tx, ty in [(x, y), (x + 12, y), (x - 12, y), (x, y + 12), (x, y - 12)]:
            thread.adb_manager.tap(tx, ty)
            time.sleep(0.65)
            src_img = thread.capture_and_validate_screen(ads=False)
            gather_match = template_match_coordinates(src_img, gather_btn, threshold=0.80)
            if gather_match:
                break
        if not gather_match:
            return False

        thread.adb_manager.tap(gather_match[0], gather_match[1])
        time.sleep(0.9)

        src_img = thread.capture_and_validate_screen(ads=False)
        confirm_match = template_match_coordinates(src_img, march_confirm_btn, threshold=0.80)
        if not confirm_match:
            return False

        thread.adb_manager.tap(confirm_match[0], confirm_match[1])
        time.sleep(1.0)

        # Best-effort verification: confirm button should disappear after dispatch.
        post_img = thread.capture_and_validate_screen(ads=False)
        still_confirm = template_match_coordinates(post_img, march_confirm_btn, threshold=0.80)
        return not bool(still_confirm)
    except Exception as e:
        _nav_log(thread, f"send_gather_march error: {e}", "warning")
        return False
