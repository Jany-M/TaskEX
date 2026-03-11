from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QCheckBox,
    QLabel, QSpinBox, QPushButton,
)

from core.custom_widgets.QCheckComboBox import QCheckComboBox
from core.services.resource_service import get_all_resource_types


def load_auto_gather_ui(instance_ui, main_window, index):
    """Populate the resource_gathering_tab_ with auto-gather controls."""
    tab_widget = getattr(instance_ui, 'resource_gathering_tab_', None)
    if tab_widget is None:
        return

    outer_layout = QVBoxLayout()
    tab_widget.setLayout(outer_layout)

    # ── Auto-Gather checkable group box ──────────────────────────────────────
    gather_group = QGroupBox("Auto-Gather")
    gather_group.setCheckable(True)
    gather_group.setChecked(False)
    gather_group.setObjectName("ag_enabled___")
    setattr(instance_ui, gather_group.objectName(), gather_group)

    inner = QVBoxLayout()
    gather_group.setLayout(inner)

    # Resource type multi-select
    res_row = QHBoxLayout()
    res_row.addWidget(QLabel("Resources to gather:"))
    resources_combo = QCheckComboBox(placeholderText="Select resources…")
    resources_combo.setObjectName("ag_resources___")
    try:
        for i, rt in enumerate(get_all_resource_types()):
            resources_combo.addItem(rt.name)
            resources_combo.setItemData(i, rt.id)
            resources_combo.setItemCheckState(i, Qt.Checked)
    except Exception:
        pass
    setattr(instance_ui, resources_combo.objectName(), resources_combo)
    res_row.addWidget(resources_combo)
    inner.addLayout(res_row)

    # Min tile level
    min_row = QHBoxLayout()
    min_row.addWidget(QLabel("Min tile level:"))
    min_spinbox = QSpinBox()
    min_spinbox.setObjectName("ag_min_level___")
    min_spinbox.setMinimum(1)
    min_spinbox.setMaximum(30)
    min_spinbox.setValue(16)
    setattr(instance_ui, min_spinbox.objectName(), min_spinbox)
    min_row.addWidget(min_spinbox)
    inner.addLayout(min_row)

    # Max tile level (0 = no cap)
    max_row = QHBoxLayout()
    max_row.addWidget(QLabel("Max tile level (0 = any level):"))
    max_spinbox = QSpinBox()
    max_spinbox.setObjectName("ag_max_level___")
    max_spinbox.setMinimum(0)
    max_spinbox.setMaximum(30)
    max_spinbox.setValue(0)
    setattr(instance_ui, max_spinbox.objectName(), max_spinbox)
    max_row.addWidget(max_spinbox)
    inner.addLayout(max_row)

    # Max concurrent gather marches
    march_row = QHBoxLayout()
    march_row.addWidget(QLabel("Max concurrent gather marches:"))
    march_spinbox = QSpinBox()
    march_spinbox.setObjectName("ag_max_marches___")
    march_spinbox.setMinimum(1)
    march_spinbox.setMaximum(4)
    march_spinbox.setValue(1)
    setattr(instance_ui, march_spinbox.objectName(), march_spinbox)
    march_row.addWidget(march_spinbox)
    inner.addLayout(march_row)

    # Auto-collect when march returns
    collect_cb = QCheckBox("Auto-collect resources when march returns")
    collect_cb.setObjectName("ag_auto_collect___")
    collect_cb.setChecked(True)
    setattr(instance_ui, collect_cb.objectName(), collect_cb)
    inner.addWidget(collect_cb)

    # Configure tile templates button
    configure_btn = QPushButton("Configure Resource Tile Templates…")
    configure_btn.setObjectName("ag_configure_btn___")
    configure_btn.clicked.connect(lambda: _open_resource_config(main_window))
    inner.addWidget(configure_btn)

    outer_layout.addWidget(gather_group)
    outer_layout.addStretch()


def _open_resource_config(main_window):
    from gui.widgets.ResourceConfigDialog import ResourceConfigDialog
    dlg = ResourceConfigDialog(main_window)
    dlg.exec()
