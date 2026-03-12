import re
import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFrame, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QComboBox
from core.custom_widgets.FlowLayout import FlowLayout
from core.custom_widgets.QCheckComboBox import QCheckComboBox
from core.services.bm_monsters_service import fetch_boss_monster_data
from db.db_setup import get_session
from db.models import BossMonster, MonsterLevel, ProfileData, InstanceSettings
from gui.widgets.LevelSelectionDialog import LevelSelectionDialog
from gui.widgets.MarchSpeedSelectionJRDialog import MarchSpeedSelectionJRDialog
from gui.widgets.PresetConfigDialog import PresetConfigDialog


def _obj_name(base_name, suffix=""):
    return f"{base_name}{suffix}" if suffix else base_name


def _extract_boss_id(object_name):
    match = re.search(r"boss(\d+)", object_name or "")
    return int(match.group(1)) if match else None


def _clear_layout(layout):
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


def _get_active_instance_indexes(main_window):
    indexes = []
    top_menu = getattr(main_window.widgets, "topMenu", None)
    if top_menu is None:
        return indexes

    for button in top_menu.findChildren(QPushButton):
        object_name = button.objectName() or ""
        if object_name.startswith("btn_emu_"):
            try:
                indexes.append(int(object_name.split("_")[-1]))
            except ValueError:
                continue

    return sorted(set(indexes))


def _snapshot_join_rally_monster_ui(main_window, index):
    state = {
        "checked_boss_ids": set(),
        "checked_combo_levels": {},
        "logic4_skipped_levels": {},
    }

    frame1 = getattr(main_window.widgets, f"jr_monster_list1_frame_{index}", None)
    frame2 = getattr(main_window.widgets, f"jr_monster_list2_frame_{index}", None)

    for frame in [frame1, frame2]:
        if frame is None:
            continue
        for checkbox in frame.findChildren(QCheckBox):
            if checkbox.isChecked():
                boss_id = checkbox.property("boss_id")
                if boss_id is None:
                    boss_id = _extract_boss_id(checkbox.objectName())
                if boss_id is not None:
                    state["checked_boss_ids"].add(int(boss_id))

    if frame2 is not None:
        for combo_box in frame2.findChildren(QCheckComboBox):
            boss_id = _extract_boss_id(combo_box.objectName())
            if boss_id is None:
                continue
            selected_level_ids = []
            for i in combo_box.checkedIndices():
                level_id = combo_box.itemData(i)
                if level_id is not None:
                    selected_level_ids.append(int(level_id))
            state["checked_combo_levels"][boss_id] = selected_level_ids

        for button in frame2.findChildren(QPushButton):
            if not (button.objectName() or "").startswith("jr_button_boss"):
                continue
            boss_id = _extract_boss_id(button.objectName())
            if boss_id is None:
                continue
            skipped_levels = button.property("value") or []
            state["logic4_skipped_levels"][boss_id] = [int(level_id) for level_id in skipped_levels]

    return state


def refresh_join_rally_monsters(main_window, index):
    frame1 = getattr(main_window.widgets, f"jr_monster_list1_frame_{index}", None)
    frame2 = getattr(main_window.widgets, f"jr_monster_list2_frame_{index}", None)
    if frame1 is None or frame2 is None:
        return

    previous_state = _snapshot_join_rally_monster_ui(main_window, index)

    flow_layout_1 = frame1.layout()
    flow_layout_2 = frame2.layout()
    _clear_layout(flow_layout_1)
    _clear_layout(flow_layout_2)

    session = get_session()
    try:
        boss_monsters = fetch_boss_monster_data(session, 1, 1, None)
        boss_monsters += fetch_boss_monster_data(session, 1, None, BossMonster.preview_name)
        for boss in boss_monsters:
            if boss.monster_logic.id == 1:
                setup_logic_1(boss, main_window.widgets, main_window, flow_layout_1, name_suffix=str(index))

        boss_monsters = fetch_boss_monster_data(session, [2, 3, 4], None, BossMonster.preview_name)
        for boss in boss_monsters:
            if boss.monster_logic.id == 2:
                setup_logic_2(boss, main_window.widgets, main_window, flow_layout_2, name_suffix=str(index))
            elif boss.monster_logic.id == 3:
                setup_logic_3(boss, main_window.widgets, main_window, flow_layout_2, name_suffix=str(index))
            elif boss.monster_logic.id == 4:
                setup_logic_4(boss, main_window.widgets, main_window, flow_layout_2, name_suffix=str(index))
    finally:
        session.close()

    for boss_id in previous_state["checked_boss_ids"]:
        checkbox = getattr(main_window.widgets, f"jr_checkbox_boss{boss_id}___{index}", None)
        if checkbox is not None:
            checkbox.setChecked(True)

    for boss_id, level_ids in previous_state["checked_combo_levels"].items():
        combo_box = getattr(main_window.widgets, f"jr_combobox_boss{boss_id}___{index}", None)
        if combo_box is None:
            continue
        for i in range(combo_box.count()):
            combo_box.setItemCheckState(i, Qt.Checked if combo_box.itemData(i) in level_ids else Qt.Unchecked)

    for boss_id, skipped_levels in previous_state["logic4_skipped_levels"].items():
        button = getattr(main_window.widgets, f"jr_button_boss{boss_id}___{index}", None)
        if button is not None:
            button.setProperty("value", skipped_levels)


def refresh_join_rally_monsters_for_all_instances(main_window):
    for index in _get_active_instance_indexes(main_window):
        refresh_join_rally_monsters(main_window, index)


def load_join_rally_ui(instance_ui,main_window,index):

    _add_join_rally_runtime_controls(instance_ui, main_window, index)

    # For Logic 1
    jr_monster_list1_frame = getattr(instance_ui, "jr_monster_list1_frame_")
    flow_layout_1 =  FlowLayout()
    jr_monster_list1_frame.setLayout(flow_layout_1)

    # For Other Logics
    jr_monster_list2_frame = getattr(instance_ui, "jr_monster_list2_frame_")
    flow_layout_2 =  FlowLayout()
    jr_monster_list2_frame.setLayout(flow_layout_2)

    session = get_session()
    try:
        # Fetch Logic 1, Category 1 (no sorting by preview_name, keep the order by ID)
        boss_monsters = fetch_boss_monster_data(session, 1, 1, None)
        # Fetch Logic 1, Other Categories (sorted by preview_name)
        boss_monsters += fetch_boss_monster_data(session, 1, None, BossMonster.preview_name)
        for boss in boss_monsters:
            if boss.monster_logic.id == 1:
                setup_logic_1(boss,instance_ui,main_window,flow_layout_1)

        # Fetch Logics 2, 3, and 4 (sorted by preview_name)
        boss_monsters = fetch_boss_monster_data(session, [2, 3, 4], None, BossMonster.preview_name)
        for boss in boss_monsters:
            # print(f"Name : {boss.preview_name} :: Logic : {boss.monster_logic.id}")
            if boss.monster_logic.id == 2:
                setup_logic_2(boss, instance_ui, main_window, flow_layout_2)
            elif boss.monster_logic.id == 3:
                setup_logic_3(boss, instance_ui, main_window, flow_layout_2)
            elif boss.monster_logic.id == 4:
                setup_logic_4(boss, instance_ui, main_window, flow_layout_2)
    finally:
        session.close()

    ###--- Join Rally Settings ---###

    # Set the type as the property for the push button (profile saving logic)
    for i in range(1, 9):
        object_name = f"rotate_preset_{i}___"
        widget = getattr(instance_ui, object_name, None)  # Get the widget dynamically
        if widget:  # Check if the widget exists
            widget.setProperty("type", "checkable")  # Set the custom property

    # Connect the preset config dialog
    preset_config_btn = getattr(instance_ui, "jr_rotate_preset_settings_")
    preset_config_btn.clicked.connect(lambda :open_preset_settings(main_window,index))

    # Make Preset buttons checked for at least one preset option
    # Generate march preset button names dynamically
    button_names = [f"rotate_preset_{i}___" for i in range(1, 9)]

    # Find march preset buttons dynamically using the object names
    buttons = [getattr(instance_ui, name, None) for name in button_names]

    # Ensure all march preset buttons are valid
    buttons = [btn for btn in buttons if btn is not None]

    # Connect the toggled signal of each button to the on_button_toggled function
    for button in buttons:
        button.toggled.connect(lambda checked, btn=button: on_button_toggled(btn, buttons))

    # Set Auto Use Stamina Combobox
    auto_use_stamina_options = getattr(instance_ui,"jr_auto_use_stamina_options___")
    auto_use_stamina_options.addItem("Min Stamina",1)
    auto_use_stamina_options.addItem("Max Stamina",2)
    auto_use_stamina_options.setCurrentIndex(0)

    # Access the march speed config button
    march_speed_configure_btn = getattr(instance_ui, "jr_march_speed_configure___")
    march_speed_configure_btn.setProperty('type','value')

    # Initialize default settings for this button
    march_speed_configure_btn.setProperty('value',{
        "use_free_boost": True,
        "use_free_boost_gems": False,
        "boost_hours": 1,
        "boost_repeat_times": 9999,
    })

    # Connect boost march speed config button
    march_speed_configure_btn.clicked.connect(lambda: open_march_speed_config_settings(march_speed_configure_btn,main_window, index))


def _add_join_rally_runtime_controls(instance_ui, main_window, index):
    tab = getattr(instance_ui, "join_rally_tab_", None)
    if tab is None or tab.layout() is None:
        return

    runtime_frame = QFrame(tab)
    runtime_layout = QHBoxLayout(runtime_frame)
    runtime_layout.setContentsMargins(0, 0, 0, 8)

    enabled_cb = QCheckBox("Enable Join Rally")
    enabled_cb.setObjectName("jr_enabled___")
    enabled_cb.setChecked(True)
    setattr(instance_ui, enabled_cb.objectName(), enabled_cb)
    runtime_layout.addWidget(enabled_cb)

    runtime_layout.addWidget(QLabel("Service Mode:"))

    mode_combo = QComboBox(runtime_frame)
    mode_combo.setObjectName("jr_service_mode___")
    mode_combo.addItem("Auto-run always", "auto")
    mode_combo.addItem("Manual start/stop", "manual")
    mode_combo.addItem("Auto-run off", "off")
    mode_combo.setCurrentIndex(1)  # default manual for rallies
    setattr(instance_ui, mode_combo.objectName(), mode_combo)
    runtime_layout.addWidget(mode_combo)

    manual_btn = QPushButton("Start", runtime_frame)
    manual_btn.setObjectName("jr_manual_running___")
    manual_btn.setCheckable(True)
    manual_btn.setChecked(False)
    manual_btn.setProperty("type", "checkable")
    setattr(instance_ui, manual_btn.objectName(), manual_btn)

    def _sync_manual_state():
        mode = mode_combo.currentData()
        is_manual = mode == "manual"
        if not is_manual:
            manual_btn.setChecked(False)
        manual_btn.setEnabled(is_manual)

    manual_btn.toggled.connect(lambda checked: manual_btn.setText("Stop" if checked else "Start"))
    mode_combo.currentIndexChanged.connect(lambda _: _sync_manual_state())
    _sync_manual_state()

    def _autosave_join_rally_runtime_controls():
        """Persist Join Rally runtime controls immediately per instance."""
        try:
            from gui.controllers.run_tab_controller import save_profile_controls

            profile_combo = getattr(main_window.widgets, f"emu_profile_{index}", None)
            profile_id = profile_combo.currentData() if profile_combo is not None else None
            if profile_id is None:
                return

            instance_id = profile_combo.property("instance_id") if profile_combo is not None else None
            storage_key = f"instance:{instance_id}" if instance_id is not None else f"index:{index}"

            def _decode_settings(raw):
                data = raw
                for _ in range(3):
                    if isinstance(data, str):
                        data = json.loads(data) if data else {}
                    else:
                        break
                return data if isinstance(data, dict) else {}

            def _normalize_profile_payload(raw):
                data = _decode_settings(raw)
                if "settings_by_instance" in data:
                    return {
                        "settings_by_instance": data.get("settings_by_instance") or {},
                        "default": data.get("default") or {},
                    }
                return {"settings_by_instance": {}, "default": data}

            def _normalize_instance_runtime_payload(raw):
                if not isinstance(raw, dict):
                    return {"auto_bubble": {}, "join_rally": {}}
                if "auto_bubble" in raw or "join_rally" in raw:
                    return {
                        "auto_bubble": raw.get("auto_bubble") or {},
                        "join_rally": raw.get("join_rally") or {},
                    }
                return {"auto_bubble": raw, "join_rally": {}}

            def _upsert_entry(blob, class_name, object_name, value, button_type=None):
                entries = blob.setdefault(class_name, [])
                for entry in entries:
                    if entry.get("object_name") == object_name:
                        entry["value"] = value
                        if button_type is not None:
                            entry["type"] = button_type
                        return
                payload = {"object_name": object_name, "value": value}
                if button_type is not None:
                    payload["type"] = button_type
                entries.append(payload)

            try:
                save_profile_controls(main_window, index, profile_id=profile_id)
            except Exception as e:
                logging.getLogger("taskex_boot").warning(
                    "[Join-Rally][Autosave] generic save_profile_controls failed for instance index %s: %s",
                    index,
                    e,
                )

            session = get_session()
            try:
                rows = (
                    session.query(ProfileData)
                    .filter_by(profile_id=profile_id)
                    .order_by(ProfileData.id.desc())
                    .all()
                )
                latest = rows[0] if rows else None
                stale = rows[1:] if len(rows) > 1 else []

                payload = _normalize_profile_payload(latest.settings if latest else {})
                blob = payload["settings_by_instance"].get(storage_key)
                if not isinstance(blob, dict):
                    blob = {}

                _upsert_entry(blob, "QCheckBox", "jr_enabled___", bool(enabled_cb.isChecked()))
                _upsert_entry(blob, "QComboBox", "jr_service_mode___", mode_combo.currentData())
                _upsert_entry(
                    blob,
                    "QPushButton",
                    "jr_manual_running___",
                    bool(manual_btn.isChecked()),
                    button_type="checkable",
                )

                payload["settings_by_instance"][storage_key] = blob
                payload["default"] = blob

                if latest is not None:
                    latest.settings = payload
                else:
                    session.add(ProfileData(profile_id=profile_id, settings=payload))

                for row in stale:
                    session.delete(row)

                if instance_id is not None:
                    instance_settings = (
                        session.query(InstanceSettings)
                        .filter_by(instance_id=instance_id)
                        .first()
                    )
                    runtime_payload = _normalize_instance_runtime_payload(
                        instance_settings.auto_bubble if instance_settings is not None else {}
                    )
                    runtime_payload["join_rally"] = {
                        "enabled": bool(enabled_cb.isChecked()),
                        "service_mode": mode_combo.currentData(),
                        "manual_running": bool(manual_btn.isChecked()),
                    }

                    if instance_settings is None:
                        session.add(InstanceSettings(instance_id=instance_id, auto_bubble=runtime_payload))
                    else:
                        instance_settings.auto_bubble = runtime_payload

                session.commit()
            finally:
                session.close()
        except Exception as e:
            logging.getLogger("taskex_boot").warning(
                "[Join-Rally][Autosave] failed for instance index %s: %s",
                index,
                e,
            )

    enabled_cb.toggled.connect(lambda _: _autosave_join_rally_runtime_controls())
    mode_combo.currentIndexChanged.connect(lambda _: _autosave_join_rally_runtime_controls())
    manual_btn.toggled.connect(lambda _: _autosave_join_rally_runtime_controls())

    runtime_layout.addWidget(manual_btn)
    runtime_layout.addStretch()

    tab.layout().insertWidget(0, runtime_frame)

def on_button_toggled(button, buttons):
    # Perform the check only if the march preset button is being unchecked
    if not button.isChecked():
        # Check if all march preset buttons are unchecked
        if not any(btn.isChecked() for btn in buttons):
            # Re-check the march preset button being toggled off
            button.setChecked(True)


def open_preset_settings(main_window,index):
    preset_config_dialog = PresetConfigDialog(main_window,index)
    preset_config_dialog.show()

def open_march_speed_config_settings(btn,main_window,index):
    march_speed_config_dialog = MarchSpeedSelectionJRDialog(main_window,btn,index)
    march_speed_config_dialog.show()


def setup_logic_1(boss,instance_ui,main_window,flow_layout, name_suffix=""):
    # print(f"Name : {boss.preview_name} :: Logic : {boss.monster_logic.id}")
    checkbox = QCheckBox(boss.preview_name)
    checkbox.setObjectName(_obj_name(f"jr_checkbox_boss{boss.id}___", name_suffix))
    # Custom property to store the boss id and logic
    # checkbox.setProperty("boss_id", boss.id)
    checkbox.setProperty("level_id", boss.levels[0].id)
    # checkbox.setProperty("logic", boss.monster_logic.id)
    setattr(instance_ui, checkbox.objectName(), checkbox)
    flow_layout.addWidget(checkbox)

def setup_logic_2(boss,instance_ui,main_window,flow_layout, name_suffix=""):
    frame = QFrame()
    vert_layout = QVBoxLayout()
    vert_layout.setContentsMargins(0, 0, 10, 5)

    # Add a checkbox for the boss
    checkbox = QCheckBox(boss.preview_name)
    checkbox.setObjectName(_obj_name(f"jr_checkbox_boss{boss.id}___", name_suffix))
    # Custom property to store the boss id and logic
    checkbox.setProperty("boss_id", boss.id)
    checkbox.setProperty("logic", boss.monster_logic.id)
    setattr(instance_ui, checkbox.objectName(), checkbox)
    checkbox.stateChanged.connect(lambda : switch_monster_checkbox(instance_ui,boss.id, name_suffix=name_suffix))
    vert_layout.addWidget(checkbox)

    # Add a QCheckComboBox for the boss's levels
    combo_box = QCheckComboBox(placeholderText="None")
    combo_box.setObjectName(_obj_name(f"jr_combobox_boss{boss.id}___", name_suffix))
    combo_box.setFixedHeight(40)
    combo_box.setMinimumWidth(135)
    setattr(instance_ui, combo_box.objectName(), combo_box)

    # Populate the QCheckComboBox with levels
    for i,level in enumerate(boss.levels):
        combo_box.addItem(f"Level {level.level}")
        combo_box.setItemData(i, level.id)
        combo_box.setItemCheckState(i, Qt.Unchecked)

    # Disable it by default
    combo_box.setDisabled(True)

    vert_layout.addWidget(combo_box)
    # Add the vertical layout to the frame
    frame.setLayout(vert_layout)

    # Add the frame to the flow layout
    flow_layout.addWidget(frame)

def setup_logic_3(boss,instance_ui,main_window,flow_layout, name_suffix=""):
    frame = QFrame()
    vert_layout = QVBoxLayout()
    vert_layout.setContentsMargins(0, 0, 10, 5)

    # Add a checkbox for the boss
    checkbox = QCheckBox(boss.preview_name)
    checkbox.setObjectName(_obj_name(f"jr_checkbox_boss{boss.id}___", name_suffix))
    # Custom property to store the boss id and logic
    checkbox.setProperty("boss_id", boss.id)
    checkbox.setProperty("logic", boss.monster_logic.id)
    setattr(instance_ui, checkbox.objectName(), checkbox)
    checkbox.stateChanged.connect(lambda : switch_monster_checkbox(instance_ui,boss.id, name_suffix=name_suffix))
    vert_layout.addWidget(checkbox)

    # Add a QCheckComboBox for the boss's levels
    combo_box = QCheckComboBox(placeholderText="None")
    combo_box.setObjectName(_obj_name(f"jr_combobox_boss{boss.id}___", name_suffix))
    combo_box.setFixedHeight(40)
    combo_box.setMinimumWidth(135)
    setattr(instance_ui, combo_box.objectName(), combo_box)

    # Populate the QCheckComboBox with levels
    for i,level in enumerate(boss.levels):
        combo_box.addItem(level.name)
        combo_box.setItemData(i, level.id)
        combo_box.setItemCheckState(i, Qt.Unchecked)

    # Disable it by default
    combo_box.setDisabled(True)

    vert_layout.addWidget(combo_box)
    # Add the vertical layout to the frame
    frame.setLayout(vert_layout)

    # Add the frame to the flow layout
    flow_layout.addWidget(frame)


def setup_logic_4(boss,instance_ui,main_window,flow_layout, name_suffix=""):
    frame = QFrame()
    vert_layout = QVBoxLayout()
    vert_layout.setContentsMargins(0, 0, 10, 5)

    # Add a checkbox for the boss
    checkbox = QCheckBox(boss.preview_name)
    checkbox.setObjectName(_obj_name(f"jr_checkbox_boss{boss.id}___", name_suffix))
    # Custom property to store the boss id and logic
    checkbox.setProperty("boss_id", boss.id)
    checkbox.setProperty("logic", boss.monster_logic.id)
    setattr(instance_ui, checkbox.objectName(), checkbox)
    checkbox.stateChanged.connect(lambda: switch_monster_checkbox(instance_ui, boss.id, False, name_suffix=name_suffix))
    vert_layout.addWidget(checkbox)

    # Add a Pushbutton for listing boss levels
    button = QPushButton("Skip Levels")
    button.setObjectName(_obj_name(f"jr_button_boss{boss.id}___", name_suffix))
    button.setProperty("value", [])
    button.setFixedHeight(40)
    button.setMinimumWidth(135)
    button.setProperty("type", "value")  # Set the custom property
    setattr(instance_ui, button.objectName(), button)
    button.clicked.connect(lambda: open_level_dialog(button, boss.id))

    # Disable it by default
    button.setDisabled(True)

    vert_layout.addWidget(button)
    # Add the vertical layout to the frame
    frame.setLayout(vert_layout)

    # Add the frame to the flow layout
    flow_layout.addWidget(frame)


def switch_monster_checkbox(instance_ui, boss_id, default=True, name_suffix=""):
    """
    Toggles the state of a combo box or a button based on the checkbox state.

    :param instance_ui: The UI instance containing the widgets.
    :param boss_id: The ID of the boss associated with the widgets.
    :param default: If True, handles the combo box. If False, handles the button.
    """
    checkbox = getattr(instance_ui, _obj_name(f"jr_checkbox_boss{boss_id}___", name_suffix))

    if default:  # Handle the combo box
        combobox = getattr(instance_ui, _obj_name(f"jr_combobox_boss{boss_id}___", name_suffix))
        if checkbox.isChecked():
            combobox.setDisabled(False)
            combobox.setCursor(Qt.ArrowCursor)  # Normal cursor
        else:
            # Uncheck all items in the combo box when disabled
            for i in combobox.checkedIndices():
                combobox.setItemCheckState(i, False)
            combobox.setDisabled(True)
            combobox.setCursor(Qt.ForbiddenCursor)  # Restricted cursor
    else:  # Handle the button
        button = getattr(instance_ui, _obj_name(f"jr_button_boss{boss_id}___", name_suffix))
        if checkbox.isChecked():
            button.setDisabled(False)
        else:
            button.setDisabled(True)
            # Clear the selected levels stored in the button
            button.setProperty("value", [])

def open_level_dialog(button, boss_id):
    """
    Open the level selection dialog and store selected levels in the button.
    """
    # Retrieve the previously selected IDs stored in the button
    selected_ids = button.property("value") or []

    # Get all the monster levels
    boss_levels = get_boss_levels(boss_id)

    # Open the dialog with selected IDs and level data
    dialog = LevelSelectionDialog(selected_ids, boss_levels,get_boss_preview_name(boss_id))
    dialog.update_group_checkbox_state()
    if dialog.exec():
        # Save the selected levels back to the button
        button.setProperty("value", list(dialog.selected_ids))  # Convert the set to a list
        # print(f"Selected Levels: {dialog.selected_ids}")



def get_boss_levels(boss_id):
    """
    Fetch all level details for a specific boss from the database.

    :param boss_id: ID of the boss to fetch levels for.
    :return: List of MonsterLevel objects.
    """
    session = get_session()
    try:
        # Query and return MonsterLevel instances
        levels = (
            session.query(MonsterLevel)
            .filter(MonsterLevel.boss_monster_id == boss_id)
            .order_by(MonsterLevel.level.asc())
            .all()
        )
        return levels
    finally:
        session.close()

def get_boss_preview_name(boss_id):
    """
    Fetch the preview name of a boss by its ID.

    :param boss_id: ID of the boss.
    :return: Preview name of the boss or None if not found.
    """
    session = get_session()
    try:
        # Query the preview_name from the BossMonster table
        preview_name = (
            session.query(BossMonster.preview_name)
            .filter(BossMonster.id == boss_id)
            .scalar()
        )
        return preview_name
    finally:
        session.close()