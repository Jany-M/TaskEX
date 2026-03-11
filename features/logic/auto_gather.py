"""
Auto-Gather Logic
=================
Dispatches gather marches to resource tiles on the World Map.
Called once per orchestrator cycle; reads per-instance settings and
respects the max-marches cap before sending any new marches.

Navigation templates required (upload via "Configure Resource Tile Templates"):
  assets/540p/gather/gather_btn.png         - tile-popup "Gather" button
  assets/540p/gather/march_confirm_btn.png  - march confirmation button
  assets/540p/gather/march_queue_icon.png   - (optional) active-march counter icon
  + per-ResourceType / per-level tile templates configured in the DB
"""

import time
import traceback

import cv2

from utils.navigate_utils import navigate_to_world_map, scan_resource_tiles_on_map, send_gather_march
from utils.get_controls_info import get_auto_gather_controls


def _count_active_gather_marches(thread):
    """
    Count active gather marches shown in the march-queue HUD.
    Returns 0 when the template is missing (conservative: assume slots free).
    """
    try:
        icon = cv2.imread('assets/540p/gather/march_queue_icon.png')
        if icon is None:
            return 0

        src_img = thread.capture_and_validate_screen(ads=False)
        if src_img is None:
            return 0

        from utils.image_recognition_utils import template_match_coordinates_all
        matches = template_match_coordinates_all(src_img, icon, threshold=0.80)
        if not matches:
            return 0

        # De-duplicate nearby detections from noisy template matches.
        deduped = []
        for x, y in matches:
            if all(abs(x - dx) > 18 or abs(y - dy) > 18 for dx, dy in deduped):
                deduped.append((x, y))
        return min(len(deduped), 4)
    except Exception:
        return 0


def run_auto_gather_cycle(thread):
    """
    One gather-dispatch pass (called by the multi-feature orchestrator).

    Navigates to World Map, finds resource tiles matching the per-instance
    configuration, and dispatches gather marches up to the configured cap.

    Returns True if at least one march was dispatched.
    """
    try:
        controls = get_auto_gather_controls(thread.main_window, thread.index)
        if not controls.get('enabled', False):
            return False

        max_marches = controls.get('max_marches', 1)
        active = _count_active_gather_marches(thread)

        if active >= max_marches:
            thread.log_message(
                f"[Auto-Gather] {active}/{max_marches} marches active — skipping dispatch.",
                "debug", force_console=False,
            )
            return False

        if not navigate_to_world_map(thread):
            thread.log_message(
                "[Auto-Gather] Cannot navigate to World Map.",
                "warning", force_console=True,
            )
            return False

        resource_type_ids = controls.get('resource_type_ids', [])
        if not resource_type_ids:
            thread.log_message("[Auto-Gather] No resource types selected.", "warning", force_console=False)
            return False

        min_level = controls.get('min_level', 1)
        max_level = controls.get('max_level', 0)

        tiles = scan_resource_tiles_on_map(thread, resource_type_ids, min_level, max_level)
        if not tiles:
            # Small pan then one retry improves reliability when map labels overlap tiles.
            thread.adb_manager.swipe(480, 420, 620, 420, 350)
            time.sleep(0.7)
            tiles = scan_resource_tiles_on_map(thread, resource_type_ids, min_level, max_level)

        thread.log_message(
            f"[Auto-Gather] Found {len(tiles)} candidate tile(s).",
            "info", force_console=True,
        )

        dispatched = 0
        for tile in tiles:
            if hasattr(thread, 'preempt_for_bubble_if_due') and thread.preempt_for_bubble_if_due("auto-gather"):
                return dispatched > 0
            if _count_active_gather_marches(thread) >= max_marches:
                break
            if send_gather_march(thread, tile, controls):
                dispatched += 1
                time.sleep(0.5)

        thread.log_message(
            f"[Auto-Gather] Dispatched {dispatched} gather march(es).",
            "info", force_console=True,
        )
        return dispatched > 0

    except Exception as e:
        thread.log_message(
            f"[Auto-Gather] Unexpected error: {e}", "warning", force_console=True
        )
        thread.log_message(traceback.format_exc(), "debug", force_console=False)
        return False
