import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QFileDialog,
    QTableWidget, QTableWidgetItem,
)

from core.services.resource_service import (
    get_all_resource_types,
    get_all_tile_templates,
    add_tile_template,
    delete_tile_template,
)


class ResourceConfigDialog(QDialog):
    """App-wide manager for resource tile templates (type + level)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_templates()

    def _build_ui(self):
        self.setWindowTitle("Resource Tile Template Configuration")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(980, 520)

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Add template images for each resource type and tile level. "
            "The scanner prefers higher level templates first."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        top_row = QHBoxLayout()
        self.resource_type = QComboBox()
        for rt in get_all_resource_types():
            self.resource_type.addItem(rt.name, rt.id)
        top_row.addWidget(self.resource_type)

        self.level = QSpinBox()
        self.level.setMinimum(1)
        self.level.setMaximum(30)
        self.level.setValue(16)
        top_row.addWidget(self.level)

        self.threshold = QDoubleSpinBox()
        self.threshold.setMinimum(0.10)
        self.threshold.setMaximum(1.00)
        self.threshold.setSingleStep(0.01)
        self.threshold.setValue(0.85)
        top_row.addWidget(self.threshold)

        add_btn = QPushButton("Add Template…")
        add_btn.clicked.connect(self._add_template)
        top_row.addWidget(add_btn)

        layout.addLayout(top_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Resource", "Level", "Template Path", "Threshold", "Delete"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _load_templates(self):
        templates = get_all_tile_templates()
        self.table.setRowCount(0)

        for tpl in templates:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(tpl.id)))
            name = tpl.resource_type.name if tpl.resource_type else str(tpl.resource_type_id)
            self.table.setItem(row, 1, QTableWidgetItem(name))
            self.table.setItem(row, 2, QTableWidgetItem(str(tpl.tile_level)))
            self.table.setItem(row, 3, QTableWidgetItem(tpl.img_540p or ""))
            self.table.setItem(row, 4, QTableWidgetItem(str(tpl.img_threshold or 0.85)))

            del_btn = QPushButton("Delete")
            del_btn.clicked.connect(lambda _=None, template_id=tpl.id: self._delete_template(template_id))
            self.table.setCellWidget(row, 5, del_btn)

    def _add_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Resource Tile Template",
            "assets/540p/gather",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path:
            return

        rel_path = path
        try:
            rel_path = os.path.relpath(path)
        except Exception:
            pass

        add_tile_template(
            resource_type_id=int(self.resource_type.currentData()),
            tile_level=int(self.level.value()),
            img_path=rel_path,
            threshold=float(self.threshold.value()),
        )
        self._load_templates()

    def _delete_template(self, template_id):
        delete_tile_template(template_id)
        self._load_templates()
