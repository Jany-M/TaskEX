import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QCheckBox,
    QLabel, QSpinBox, QComboBox, QPushButton,
)

from core.services.bubble_service import get_all_bubble_types, get_bubble_display_name


def load_auto_bubble_ui(instance_ui, main_window, index):
    """Populate the general_tab_ with auto-bubble controls."""
    tab_widget = getattr(instance_ui, 'general_tab_', None)
    if tab_widget is None:
        return

    outer_layout = QVBoxLayout()
    tab_widget.setLayout(outer_layout)

    # ── Auto-Bubble checkable group box ──────────────────────────────────────
    bubble_group = QGroupBox("Auto-Bubble")
    bubble_group.setCheckable(True)
    bubble_group.setChecked(True)
    bubble_group.setObjectName("ab_enabled___")
    setattr(instance_ui, bubble_group.objectName(), bubble_group)

    inner = QVBoxLayout()
    bubble_group.setLayout(inner)

    # Bubble type combobox
    mode_row = QHBoxLayout()
    mode_row.addWidget(QLabel("Service mode:"))
    service_mode_combo = QComboBox()
    service_mode_combo.setObjectName("ab_service_mode___")
    service_mode_combo.addItem("Auto-run always", "auto")
    service_mode_combo.addItem("Manual start/stop", "manual")
    service_mode_combo.addItem("Auto-run off", "off")
    service_mode_combo.setCurrentIndex(0)  # bubble defaults to auto-enabled
    setattr(instance_ui, service_mode_combo.objectName(), service_mode_combo)
    mode_row.addWidget(service_mode_combo)

    manual_btn = QPushButton("Start")
    manual_btn.setObjectName("ab_manual_running___")
    manual_btn.setCheckable(True)
    manual_btn.setProperty("type", "checkable")
    setattr(instance_ui, manual_btn.objectName(), manual_btn)

    def _sync_manual_state():
        is_manual = service_mode_combo.currentData() == "manual"
        if not is_manual:
            manual_btn.setChecked(False)
        manual_btn.setEnabled(is_manual)

    manual_btn.toggled.connect(lambda checked: manual_btn.setText("Stop" if checked else "Start"))
    service_mode_combo.currentIndexChanged.connect(lambda _: _sync_manual_state())
    _sync_manual_state()

    mode_row.addWidget(manual_btn)
    mode_row.addStretch()
    inner.addLayout(mode_row)

    type_row = QHBoxLayout()
    type_row.addWidget(QLabel("Bubble type:"))
    bubble_type_combo = QComboBox()
    bubble_type_combo.setObjectName("ab_bubble_type___")
    try:
        for bt in get_all_bubble_types():
            bubble_type_combo.addItem(get_bubble_display_name(bt), bt.id)
    except Exception:
        pass
    setattr(instance_ui, bubble_type_combo.objectName(), bubble_type_combo)
    type_row.addWidget(bubble_type_combo)
    inner.addLayout(type_row)

    # Trigger threshold in minutes
    trigger_row = QHBoxLayout()
    trigger_row.addWidget(QLabel("Trigger when remaining bubble time is less than (minutes):"))
    trigger_spinbox = QSpinBox()
    trigger_spinbox.setObjectName("ab_trigger_minutes___")
    trigger_spinbox.setMinimum(0)
    trigger_spinbox.setMaximum(9999)
    trigger_spinbox.setValue(60)
    setattr(instance_ui, trigger_spinbox.objectName(), trigger_spinbox)
    trigger_row.addWidget(trigger_spinbox)
    inner.addLayout(trigger_row)

    # Prioritise inventory bubbles over purchase
    prioritize_cb = QCheckBox("Prioritize existing inventory bubbles before purchasing")
    prioritize_cb.setObjectName("ab_prioritize_existing___")
    prioritize_cb.setChecked(True)
    setattr(instance_ui, prioritize_cb.objectName(), prioritize_cb)
    inner.addWidget(prioritize_cb)

    # Allow gem purchase fallback
    gem_cb = QCheckBox("Allow buying bubble with gems if none in inventory")
    gem_cb.setObjectName("ab_allow_gem_purchase___")
    gem_cb.setChecked(False)
    setattr(instance_ui, gem_cb.objectName(), gem_cb)
    inner.addWidget(gem_cb)

    def _autosave_auto_bubble_controls():
        """Persist auto-bubble controls immediately so terminal restarts do not lose them."""
        try:
            from db.db_setup import get_session
            from db.models import ProfileData, InstanceSettings

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

            def _normalize_payload(raw):
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

            def _upsert_entry(blob, class_name, object_name, value):
                entries = blob.setdefault(class_name, [])
                for entry in entries:
                    if entry.get("object_name") == object_name:
                        entry["value"] = value
                        return
                entries.append({"object_name": object_name, "value": value})

            # 1) Generic save path (best effort only)
            try:
                from gui.controllers.run_tab_controller import save_profile_controls
                save_profile_controls(main_window, index, profile_id=profile_id)
            except Exception as e:
                logging.getLogger("taskex_boot").warning(
                    "[Auto-Bubble][Autosave] generic save_profile_controls failed for instance index %s: %s",
                    index,
                    e,
                )

            # 2) Direct write for Auto-Bubble controls from live widgets (hard guarantee)
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

                payload = _normalize_payload(latest.settings if latest else {})
                blob = payload["settings_by_instance"].get(storage_key)
                if not isinstance(blob, dict):
                    blob = {}

                _upsert_entry(blob, "QGroupBox", "ab_enabled___", bool(bubble_group.isChecked()))
                _upsert_entry(blob, "QComboBox", "ab_service_mode___", service_mode_combo.currentData())
                _upsert_entry(blob, "QComboBox", "ab_bubble_type___", bubble_type_combo.currentData())
                _upsert_entry(blob, "QSpinBox", "ab_trigger_minutes___", int(trigger_spinbox.value()))
                _upsert_entry(blob, "QCheckBox", "ab_prioritize_existing___", bool(prioritize_cb.isChecked()))
                _upsert_entry(blob, "QCheckBox", "ab_allow_gem_purchase___", bool(gem_cb.isChecked()))

                payload["settings_by_instance"][storage_key] = blob
                payload["default"] = blob

                if latest is not None:
                    latest.settings = payload
                else:
                    session.add(ProfileData(profile_id=profile_id, settings=payload))

                for row in stale:
                    session.delete(row)

                # Hard source-of-truth for per-instance bubble settings.
                if instance_id is not None:
                    instance_settings = (
                        session.query(InstanceSettings)
                        .filter_by(instance_id=instance_id)
                        .first()
                    )
                    bubble_payload = {
                        "enabled": bool(bubble_group.isChecked()),
                        "service_mode": service_mode_combo.currentData(),
                        "manual_running": bool(manual_btn.isChecked()),
                        "bubble_type_id": bubble_type_combo.currentData(),
                        "trigger_minutes": int(trigger_spinbox.value()),
                        "prioritize_existing": bool(prioritize_cb.isChecked()),
                        "allow_gem_purchase": bool(gem_cb.isChecked()),
                    }
                    instance_payload = _normalize_instance_runtime_payload(
                        instance_settings.auto_bubble if instance_settings is not None else {}
                    )
                    instance_payload["auto_bubble"] = bubble_payload
                    if instance_settings is None:
                        session.add(
                            InstanceSettings(
                                instance_id=instance_id,
                                auto_bubble=instance_payload,
                            )
                        )
                    else:
                        instance_settings.auto_bubble = instance_payload

                session.commit()
                logging.getLogger("taskex_boot").info(
                    "[Auto-Bubble][Autosave] profile_id=%s storage_key=%s bubble_type=%s prioritize_existing=%s allow_gem_purchase=%s",
                    profile_id,
                    storage_key,
                    bubble_type_combo.currentData(),
                    bool(prioritize_cb.isChecked()),
                    bool(gem_cb.isChecked()),
                )
            finally:
                session.close()
        except Exception as e:
            logging.getLogger("taskex_boot").warning(
                "[Auto-Bubble][Autosave] failed for instance index %s: %s",
                index,
                e,
            )

    bubble_group.toggled.connect(lambda _: _autosave_auto_bubble_controls())
    service_mode_combo.currentIndexChanged.connect(lambda _: _autosave_auto_bubble_controls())
    manual_btn.toggled.connect(lambda _: _autosave_auto_bubble_controls())
    bubble_type_combo.currentIndexChanged.connect(lambda _: _autosave_auto_bubble_controls())
    trigger_spinbox.valueChanged.connect(lambda _: _autosave_auto_bubble_controls())
    prioritize_cb.toggled.connect(lambda _: _autosave_auto_bubble_controls())
    gem_cb.toggled.connect(lambda _: _autosave_auto_bubble_controls())

    # Note: Bubble template configuration is now handled app-wide in Bot Manager > Bubbles tab

    outer_layout.addWidget(bubble_group)
    outer_layout.addStretch()
