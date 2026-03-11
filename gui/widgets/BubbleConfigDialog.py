import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QFileDialog, QTableWidget, QTableWidgetItem,
)

from core.services.bubble_service import (
    get_all_bubble_types,
    update_bubble_type_template,
    clear_bubble_type_template,
)


class BubbleConfigDialog(QDialog):
    """App-wide manager for bubble template image paths and thresholds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._build_ui()
        self._load_rows()

    def _build_ui(self):
        self.setWindowTitle("Bubble Template Configuration")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(820, 420)

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Upload one template image per bubble type. "
            "Template should tightly crop the bubble item icon."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Bubble", "Duration (h)", "Template Path", "Threshold", "Browse", "Clear"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _load_rows(self):
        self.table.setRowCount(0)
        self._rows = []

        bubble_types = get_all_bubble_types()
        for bubble in bubble_types:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(bubble.name))
            self.table.setItem(row, 1, QTableWidgetItem(str(bubble.duration_hours)))
            self.table.setItem(row, 2, QTableWidgetItem(bubble.img_540p or ""))

            threshold = QDoubleSpinBox()
            threshold.setMinimum(0.10)
            threshold.setMaximum(1.00)
            threshold.setSingleStep(0.01)
            threshold.setValue(float(bubble.img_threshold or 0.85))
            threshold.valueChanged.connect(lambda val, b_id=bubble.id, r=row: self._save_threshold(b_id, r, val))
            self.table.setCellWidget(row, 3, threshold)

            browse_btn = QPushButton("Browse…")
            browse_btn.clicked.connect(lambda _=None, b_id=bubble.id, r=row: self._browse_template(b_id, r))
            self.table.setCellWidget(row, 4, browse_btn)

            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda _=None, b_id=bubble.id, r=row: self._clear_template(b_id, r))
            self.table.setCellWidget(row, 5, clear_btn)

            self._rows.append({"bubble_id": bubble.id})

    def _save_threshold(self, bubble_id, row, value):
        path = self.table.item(row, 2).text().strip() if self.table.item(row, 2) else ""
        if path:
            update_bubble_type_template(bubble_id, path, value)

    def _browse_template(self, bubble_id, row):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Bubble Template",
            "assets/540p/bubbles",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not path:
            return

        rel_path = path
        try:
            rel_path = os.path.relpath(path)
        except Exception:
            pass

        threshold_widget = self.table.cellWidget(row, 3)
        threshold_val = threshold_widget.value() if threshold_widget else 0.85
        update_bubble_type_template(bubble_id, rel_path, threshold_val)
        self.table.setItem(row, 2, QTableWidgetItem(rel_path))

    def _clear_template(self, bubble_id, row):
        clear_bubble_type_template(bubble_id)
        self.table.setItem(row, 2, QTableWidgetItem(""))
