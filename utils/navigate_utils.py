import time

import cv2

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


def navigate_generals_window(thread):
    generals_btn_img = cv2.imread('assets/540p/other/generals_window_btn.png')
    menu_btn_img = cv2.imread('assets/540p/other/three_dots_menu_btn.png')

    # Make sure its inside alliance city
    if not ensure_alliance_city_or_world_map_screen(thread):
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
    elif not ensure_alliance_city_or_world_map_screen(thread):
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


def ensure_alliance_city_or_world_map_screen(thread, ac=True, wm=True):
    """
    Ensures the screen is either Alliance City or World Map based on the parameters.

    Parameters:
        thread: The bot thread instance.
        ac (bool): If True, ensure the screen is in Alliance City.
        wm (bool): If True, ensure the screen is in World Map.

    Returns:
        bool: True if the desired screen is ensured, False otherwise.
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
        if ac:
            if is_template_match(src_img, wm_btn_img):  # Alliance City detected
                return True
            if not wm:  # Only Alliance City is required
                thread.adb_manager.press_back()
                time.sleep(1)
                counter += 1
                continue

        # Check World Map
        if wm:
            ac_btn_match = template_match_coordinates(src_img, ac_btn_img)  # Check for World Map/Ideal Land
            wm_alliance_match = is_template_match(src_img, alliance_btn_img)

            if ac_btn_match and wm_alliance_match:  # World Map detected
                return True
            elif ac_btn_match and not wm_alliance_match:  # Ideal Land case
                thread.adb_manager.tap(ac_btn_match[0], ac_btn_match[1])  # Navigate to Alliance City
                time.sleep(4)
                continue

        # If neither is detected, press back
        thread.adb_manager.press_back()
        time.sleep(1)
        counter += 1

    # Failed to ensure desired screen
    _nav_log(thread, "Failed to reach Alliance City/World Map after max back attempts.", "warning")
    return False


def navigate_to_world_map(thread):
    """Ensure the game is on World Map."""
    return ensure_alliance_city_or_world_map_screen(thread, ac=False, wm=True)


def navigate_to_bubble_use(thread, controls):
    """
    Navigate to inventory/protection and use the selected bubble template.

    Expected controls keys:
      - bubble_type_id
      - prioritize_existing
      - allow_gem_purchase
    """
    try:
        from core.services.bubble_service import get_all_bubble_types

        if not ensure_alliance_city_or_world_map_screen(thread, ac=True, wm=True):
            return False

        src_img = thread.capture_and_validate_screen()
        if src_img is None:
            return False

        items_btn = _load_template('assets/540p/bubbles/items_btn.png', thread)
        protection_tab = _load_template('assets/540p/bubbles/protection_tab.png', thread)
        use_btn = _load_template('assets/540p/bubbles/use_btn.png', thread)
        if items_btn is None or protection_tab is None or use_btn is None:
            _nav_log(thread, "Missing base bubble navigation templates.", "warning")
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
    except Exception as e:
        _nav_log(thread, f"navigate_to_bubble_use error: {e}", "warning")
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
    for resource_type_id in resource_type_ids:
        templates = get_tile_templates_for_resource(resource_type_id, min_level=min_level, max_level=max_level)
        for template in templates:
            tpl = _load_template(template.img_540p, thread)
            if tpl is None:
                continue
            matches = template_match_coordinates_all(src_img, tpl, threshold=template.img_threshold or 0.85)
            for x, y in matches:
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

        thread.adb_manager.tap(x, y)
        time.sleep(0.8)

        src_img = thread.capture_and_validate_screen(ads=False)
        gather_match = template_match_coordinates(src_img, gather_btn, threshold=0.80)
        if not gather_match:
            return False

        thread.adb_manager.tap(gather_match[0], gather_match[1])
        time.sleep(1)

        src_img = thread.capture_and_validate_screen(ads=False)
        confirm_match = template_match_coordinates(src_img, march_confirm_btn, threshold=0.80)
        if not confirm_match:
            return False

        thread.adb_manager.tap(confirm_match[0], confirm_match[1])
        time.sleep(1)
        return True
    except Exception as e:
        _nav_log(thread, f"send_gather_march error: {e}", "warning")
        return False
