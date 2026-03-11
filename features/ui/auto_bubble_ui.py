from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QCheckBox,
    QLabel, QSpinBox, QComboBox, QPushButton,
)

from core.services.bubble_service import get_all_bubble_types


def load_auto_bubble_ui(instance_ui, main_window, index):
    """Populate the more_activities_tab_ with auto-bubble controls."""
    tab_widget = getattr(instance_ui, 'more_activities_tab_', None)
    if tab_widget is None:
        return

    outer_layout = QVBoxLayout()
    tab_widget.setLayout(outer_layout)

    # ── Auto-Bubble checkable group box ──────────────────────────────────────
    bubble_group = QGroupBox("Auto-Bubble")
    bubble_group.setCheckable(True)
    bubble_group.setChecked(False)
    bubble_group.setObjectName("ab_enabled___")
    setattr(instance_ui, bubble_group.objectName(), bubble_group)

    inner = QVBoxLayout()
    bubble_group.setLayout(inner)

    # Bubble type combobox
    type_row = QHBoxLayout()
    type_row.addWidget(QLabel("Bubble type:"))
    bubble_type_combo = QComboBox()
    bubble_type_combo.setObjectName("ab_bubble_type___")
    try:
        for bt in get_all_bubble_types():
            bubble_type_combo.addItem(bt.name, bt.id)
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

    # Configure templates button
    configure_btn = QPushButton("Configure Bubble Templates…")
    configure_btn.setObjectName("ab_configure_btn___")
    configure_btn.clicked.connect(lambda: _open_bubble_config(main_window))
    inner.addWidget(configure_btn)

    outer_layout.addWidget(bubble_group)
    outer_layout.addStretch()


def _open_bubble_config(main_window):
    from gui.widgets.BubbleConfigDialog import BubbleConfigDialog
    dlg = BubbleConfigDialog(main_window)
    dlg.exec()
