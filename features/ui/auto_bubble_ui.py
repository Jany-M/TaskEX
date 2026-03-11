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

    # Note: Bubble template configuration is now handled app-wide in Bot Manager > Bubbles tab

    outer_layout.addWidget(bubble_group)
    outer_layout.addStretch()
