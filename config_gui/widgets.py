"""
UI widgets for ROI configuration.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QFormLayout, QLineEdit, QComboBox, QSpinBox, QPushButton,
    QGroupBox, QSlider, QLabel, QCheckBox
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QImage
import cv2
import numpy as np

from .models import ROIData


class VideoWidget(QOpenGLWidget):
    """Widget for displaying video with ROI overlays."""
    roi_selected = pyqtSignal(ROIData)

    def __init__(self):
        super().__init__()
        self.frame = None
        self.rois = []
        self.frame_idx = 0
        self.fps = 30.0
        self.time_unit = "frames"
        self.scale = 1.0
        self.display_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.is_selecting = False
        self.start_pos = None

    def set_frame(self, frame: np.ndarray):
        self.frame = frame
        self.update()

    def set_rois(self, rois):
        self.rois = rois

    def is_active(self, roi, frame_idx: int) -> bool:
        start = roi.get("start_time")
        end = roi.get("end_time")
        if start is None and end is None:
            return True
        # Convert to frame index if time_unit != "frames"
        if self.time_unit == "frames":
            s = start
            e = end
        elif self.time_unit in ("seconds", "s"):
            s = None if start is None else int(start * self.fps)
            e = None if end is None else int(end * self.fps)
        else:
            s = start
            e = end
        if s is None and e is None:
            return True
        if s is None:
            return frame_idx <= e
        if e is None:
            return frame_idx >= s
        return s <= frame_idx <= e

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.frame is not None:
            h, w, c = self.frame.shape
            bytes_per_line = 3 * w
            qimg = QImage(self.frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()

            # Calculate scaled rect to fit widget while maintaining aspect ratio
            widget_w = self.width()
            widget_h = self.height()
            if w > 0 and h > 0:
                aspect = w / h
                if widget_w / widget_h > aspect:
                    scaled_h = widget_h
                    scaled_w = int(widget_h * aspect)
                    x = (widget_w - scaled_w) // 2
                    y = 0
                else:
                    scaled_w = widget_w
                    scaled_h = int(widget_w / aspect)
                    x = 0
                    y = (widget_h - scaled_h) // 2
                self.display_scale = scaled_w / w
                self.offset_x = x
                self.offset_y = y
                scaled_qimg = qimg.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.KeepAspectRatio)
                painter.drawImage(x, y, scaled_qimg)
            else:
                painter.drawImage(0, 0, qimg)
                self.display_scale = 1.0
                self.offset_x = 0
                self.offset_y = 0

            # Draw ROIs scaled and offset
            for roi in self.rois:
                if self.is_active(roi, self.frame_idx):
                    role = roi.get("id") or "default"
                    color = (0, 255, 0)  # green for ROIs
                    qcolor = QColor(*color)
                    measurement_unit = roi.get("measurement_unit", "")
                    vehicle = roi.get("vehicle")

                    x_roi = int((roi.get("x", 0) * self.scale * self.display_scale) + self.offset_x)
                    y_roi = int((roi.get("y", 0) * self.scale * self.display_scale) + self.offset_y)
                    w_roi = int(roi.get("w", 0) * self.scale * self.display_scale)
                    h_roi = int(roi.get("h", 0) * self.scale * self.display_scale)

                    if w_roi > 0 and h_roi > 0:
                        painter.setPen(QPen(qcolor, 2))
                        painter.setBrush(QBrush(qcolor, Qt.BrushStyle.Dense4Pattern))
                        painter.drawRect(x_roi, y_roi, w_roi, h_roi)

                    # Draw label
                    label = roi.get("label", roi.get("id", "ROI"))
                    if vehicle:
                        text = f"{label} ({vehicle}, {measurement_unit})"
                    else:
                        text = f"{label} ({role}, {measurement_unit})"
                    painter.setPen(QPen(qcolor, 1))
                    painter.drawText(max(8, x_roi), max(20, y_roi - 6), text)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.is_selecting = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Could draw selection rectangle here
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            end_pos = event.pos()
            if self.start_pos and self.frame is not None:
                # Convert screen coords to frame coords
                h, w, c = self.frame.shape
                start_x = (self.start_pos.x() - self.offset_x) / self.display_scale
                start_y = (self.start_pos.y() - self.offset_y) / self.display_scale
                end_x = (end_pos.x() - self.offset_x) / self.display_scale
                end_y = (end_pos.y() - self.offset_y) / self.display_scale

                x = min(start_x, end_x)
                y = min(start_y, end_y)
                w_roi = abs(end_x - start_x)
                h_roi = abs(end_y - start_y)

                if w_roi > 10 and h_roi > 10:
                    roi_data = ROIData()
                    roi_data.x = int(x)
                    roi_data.y = int(y)
                    roi_data.w = int(w_roi)
                    roi_data.h = int(h_roi)
                    self.roi_selected.emit(roi_data)
        super().mouseReleaseEvent(event)


class ROIPropertiesWidget(QWidget):
    """Widget for editing ROI properties."""
    properties_changed = pyqtSignal(ROIData)

    def __init__(self):
        super().__init__()
        self.current_roi = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the properties UI."""
        layout = QVBoxLayout()

        # Basic properties
        basic_group = QGroupBox("Basic Properties")
        basic_layout = QFormLayout()

        self.id_edit = QComboBox()
        self.id_edit.addItems([
            'engines', 'speed', 'altitude', 'time'
        ])
        self.label_edit = QLineEdit()
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.setEditable(True)
        self.vehicle_combo.addItems([
            '', 'superheavy', 'starship'
        ])
        self.vehicle_combo.lineEdit().editingFinished.connect(self.on_vehicle_changed)
        self.measurement_unit_edit = QLineEdit()

        basic_layout.addRow("ID:", self.id_edit)
        basic_layout.addRow("Label:", self.label_edit)
        basic_layout.addRow("Vehicle:", self.vehicle_combo)
        basic_layout.addRow("Measurement Unit:", self.measurement_unit_edit)
        basic_group.setLayout(basic_layout)

        # Geometry properties
        geom_group = QGroupBox("Geometry")
        geom_layout = QVBoxLayout()

        self.rect_radio = QCheckBox("Rectangle")
        self.rect_radio.setChecked(True)

        coords_layout = QFormLayout()
        self.x_spin = QSpinBox(); self.x_spin.setRange(0, 9999)
        self.y_spin = QSpinBox(); self.y_spin.setRange(0, 9999)
        self.w_spin = QSpinBox(); self.w_spin.setRange(0, 9999)
        self.h_spin = QSpinBox(); self.h_spin.setRange(0, 9999)

        coords_layout.addRow("X:", self.x_spin)
        coords_layout.addRow("Y:", self.y_spin)
        coords_layout.addRow("Width:", self.w_spin)
        coords_layout.addRow("Height:", self.h_spin)

        geom_layout.addWidget(self.rect_radio)
        geom_layout.addLayout(coords_layout)
        geom_group.setLayout(geom_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.reset_btn = QPushButton("Reset")
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.reset_btn)

        layout.addWidget(basic_group)
        layout.addWidget(geom_group)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect signals
        self.apply_btn.clicked.connect(self.apply_changes)
        self.reset_btn.clicked.connect(self.reset_changes)

    def on_vehicle_changed(self):
        """Handle vehicle combo editing finished to add new vehicles."""
        text = self.vehicle_combo.currentText()
        if text and text not in [self.vehicle_combo.itemText(i) for i in range(self.vehicle_combo.count())]:
            self.vehicle_combo.addItem(text)

    def set_roi(self, roi: ROIData):
        """Set current ROI for editing."""
        self.current_roi = roi
        self.id_edit.setCurrentText(roi.id)
        self.label_edit.setText(roi.label)
        vehicle = roi.vehicle if roi.vehicle else ''
        self.vehicle_combo.setCurrentText(vehicle)
        self.measurement_unit_edit.setText(roi.measurement_unit)
        self.rect_radio.setChecked(roi.is_rectangle())
        self.x_spin.setValue(roi.x)
        self.y_spin.setValue(roi.y)
        self.w_spin.setValue(roi.w)
        self.h_spin.setValue(roi.h)

    def apply_changes(self):
        """Apply changes to current ROI."""
        if not self.current_roi:
            return

        self.current_roi.id = self.id_edit.currentText()
        self.current_roi.label = self.label_edit.text()
        vehicle_text = self.vehicle_combo.currentText()
        self.current_roi.vehicle = vehicle_text if vehicle_text else None
        self.current_roi.measurement_unit = self.measurement_unit_edit.text()
        self.current_roi.x = self.x_spin.value()
        self.current_roi.y = self.y_spin.value()
        self.current_roi.w = self.w_spin.value()
        self.current_roi.h = self.h_spin.value()

        self.properties_changed.emit(self.current_roi)

    def reset_changes(self):
        """Reset changes."""
        if self.current_roi:
            self.set_roi(self.current_roi)