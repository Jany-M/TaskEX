import os

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtGui import QPixmap

from core.services.bubble_service import (
    update_bubble_type_template,
    clear_bubble_type_template,
    get_bubble_display_name,
)


class BubbleProfileWidget(QWidget):
    """Display and configure a single bubble type from the app-wide Bubble Manager."""

    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.data = data
        self.setObjectName(f"bubble_profile_{self.data.id}")
        self._build_ui()

    def _build_ui(self):
        """Build the UI for displaying/editing a bubble type."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Bubble name and duration header
        header_layout = QHBoxLayout()
        name_label = QLabel(get_bubble_display_name(self.data))
        name_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        meta_label = QLabel(
            f"Row {self.data.id} on the Use Item screen | Duration: {self.data.duration_hours}h\n"
            "Runtime action on the right side is detected as either 'Use' or a gem price.\n"
            "Inventory count appears at the bottom-right of the in-game icon when available."
        )
        meta_label.setWordWrap(True)
        meta_label.setStyleSheet("color: #bbb;")
        layout.addWidget(meta_label)

        # Template image preview
        preview_layout = QHBoxLayout()
        preview_label = QLabel("Template Image:")
        preview_layout.addWidget(preview_label)

        if self.data.img_540p and os.path.isfile(self.data.img_540p):
            pixmap = QPixmap(self.data.img_540p)
            if not pixmap.isNull():
                pixmap = pixmap.scaledToHeight(60)
                img_display = QLabel()
                img_display.setPixmap(pixmap)
                preview_layout.addWidget(img_display)
            else:
                preview_path_label = QLabel("(Invalid image)")
                preview_layout.addWidget(preview_path_label)
        else:
            no_img_label = QLabel("(No template set)")
            no_img_label.setStyleSheet("color: #999;")
            preview_layout.addWidget(no_img_label)

        preview_layout.addStretch()
        layout.addLayout(preview_layout)

        # Threshold spinbox
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Match Threshold:"))
        threshold_spinbox = QDoubleSpinBox()
        threshold_spinbox.setMinimum(0.10)
        threshold_spinbox.setMaximum(1.00)
        threshold_spinbox.setSingleStep(0.01)
        threshold_spinbox.setValue(float(self.data.img_threshold or 0.85))
        threshold_spinbox.valueChanged.connect(
            lambda val: self._save_threshold(val)
        )
        threshold_layout.addWidget(threshold_spinbox)
        threshold_layout.addStretch()
        layout.addLayout(threshold_layout)

        # Browse and Clear buttons
        button_layout = QHBoxLayout()
        browse_btn = QPushButton("Browse Template…")
        browse_btn.setMinimumWidth(120)
        browse_btn.clicked.connect(self._browse_template)
        button_layout.addWidget(browse_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setMinimumWidth(80)
        clear_btn.clicked.connect(self._clear_template)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _browse_template(self):
        """Open file dialog to select a bubble template image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select template for {self.data.name}",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if file_path:
            update_bubble_type_template(self.data.id, file_path, self.data.img_threshold)
            # Reload the widget to show new image
            self._refresh_preview()
            QMessageBox.information(self, "Success", "Bubble template updated.")

    def _save_threshold(self, value):
        """Save threshold value to the database."""
        update_bubble_type_template(self.data.id, self.data.img_540p, value)
        self.data.img_threshold = value

    def _clear_template(self):
        """Remove the template from this bubble type."""
        clear_bubble_type_template(self.data.id)
        self.data.img_540p = None
        self.data.preview_image = None
        self._refresh_preview()
        QMessageBox.information(self, "Success", "Bubble template cleared.")

    def _refresh_preview(self):
        """Rebuild the UI to reflect template changes."""
        # Clear existing layout
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().setParent(None)
        # Rebuild
        self._build_ui()
