"""
UI widgets for ROI configuration.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QFormLayout, QLineEdit, QComboBox, QSpinBox, QPushButton,
    QGroupBox, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QCheckBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor, QPainter

from .models import ROIData


class ROIGraphicsItem(QGraphicsRectItem):
    """Graphics item for displaying and editing ROIs."""
    def __init__(self, roi_data: ROIData):
        super().__init__(roi_data.get_rect())
        self.roi_data = roi_data
        self.setPen(QPen(QColor(255, 0, 0), 2))
        self.setBrush(QBrush(QColor(255, 0, 0, 50)))

        # Add label
        self.label_item = None
        self.update_label()

    def update_label(self):
        """Update the label display."""
        if self.label_item:
            self.scene().removeItem(self.label_item)

        label_text = f"{self.roi_data.id}"
        # Note: In full implementation, would add text item here

    def update_from_rect(self, rect: QRectF):
        """Update ROI data from rectangle."""
        self.roi_data.x = int(rect.x())
        self.roi_data.y = int(rect.y())
        self.roi_data.w = int(rect.width())
        self.roi_data.h = int(rect.height())
        self.setRect(rect)
        self.update_label()


class ImageViewer(QGraphicsView):
    """Widget for displaying images with ROI overlays."""
    roi_selected = pyqtSignal(ROIData)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.image_item = None
        self.roi_items = []
        self.selection_rect = None
        self.is_selecting = False
        self.start_pos = None

        self.setRenderHint(self.renderHints() | QPainter.RenderHint.Antialiasing)
        self.setMouseTracking(True)

    def load_image(self, image_path: str):
        """Load and display an image."""
        import os
        if not os.path.exists(image_path):
            return False

        # For now, create a placeholder image
        # TODO: Implement actual image loading with PIL or similar
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return False

        self.scene.clear()
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)

        return True

    def add_roi(self, roi_data: ROIData):
        """Add ROI to display."""
        if roi_data.is_rectangle():
            roi_item = ROIGraphicsItem(roi_data)
            self.scene.addItem(roi_item)
            self.roi_items.append(roi_item)

    def clear_rois(self):
        """Clear all ROI displays."""
        for item in self.roi_items:
            self.scene.removeItem(item)
        self.roi_items.clear()

    def mousePressEvent(self, event):
        """Handle mouse press for ROI selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.is_selecting = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for selection rectangle."""
        if self.is_selecting and self.start_pos:
            # Update selection rectangle
            pass  # Simplified for now
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to create ROI."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            # Create new ROI from selection
            end_pos = event.pos()
            if self.start_pos and self.image_item:
                scene_start = self.mapToScene(self.start_pos)
                scene_end = self.mapToScene(end_pos)

                rect = QRectF(scene_start, scene_end).normalized()
                if rect.width() > 10 and rect.height() > 10:  # Minimum size
                    roi_data = ROIData()
                    roi_data.x = int(rect.x())
                    roi_data.y = int(rect.y())
                    roi_data.w = int(rect.width())
                    roi_data.h = int(rect.height())
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

        self.id_edit = QLineEdit()
        self.label_edit = QLineEdit()
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItems([
            '', 'superheavy', 'starship'
        ])
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

    def set_roi(self, roi: ROIData):
        """Set current ROI for editing."""
        self.current_roi = roi
        self.id_edit.setText(roi.id)
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

        self.current_roi.id = self.id_edit.text()
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