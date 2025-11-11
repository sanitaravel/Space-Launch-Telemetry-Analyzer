"""
ROI properties widget for editing ROI properties.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QFormLayout, QLineEdit, QComboBox, QSpinBox, QPushButton,
    QGroupBox, QCheckBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from .models import ROIData


class ROIPropertiesWidget(QWidget):
    """Widget for editing ROI properties."""
    properties_changed = pyqtSignal(ROIData)
    engine_group_selected = pyqtSignal(str)  # Signal when engine group is selected

    def __init__(self):
        super().__init__()
        self.current_roi = None
        self.current_frame_idx = 0
        self.current_fps = 30.0
        self.time_unit = "frames"
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

        # Start frame and time
        start_frame_layout = QHBoxLayout()
        self.start_frame_spin = QSpinBox()
        self.start_frame_spin.setRange(0, 999999)
        self.start_now_btn = QPushButton("Now")
        start_frame_layout.addWidget(self.start_frame_spin)
        start_frame_layout.addWidget(self.start_now_btn)
        basic_layout.addRow("Start Frame:", start_frame_layout)

        start_time_layout = QHBoxLayout()
        self.start_time_spin = QDoubleSpinBox()
        self.start_time_spin.setRange(0, 999999)
        self.start_time_spin.setDecimals(2)
        self.start_time_now_btn = QPushButton("Now")
        start_time_layout.addWidget(self.start_time_spin)
        start_time_layout.addWidget(self.start_time_now_btn)
        basic_layout.addRow("Start Time (s):", start_time_layout)

        # End frame and time
        end_frame_layout = QHBoxLayout()
        self.end_frame_spin = QSpinBox()
        self.end_frame_spin.setRange(0, 999999)
        self.end_now_btn = QPushButton("Now")
        end_frame_layout.addWidget(self.end_frame_spin)
        end_frame_layout.addWidget(self.end_now_btn)
        basic_layout.addRow("End Frame:", end_frame_layout)

        end_time_layout = QHBoxLayout()
        self.end_time_spin = QDoubleSpinBox()
        self.end_time_spin.setRange(0, 999999)
        self.end_time_spin.setDecimals(2)
        self.end_time_now_btn = QPushButton("Now")
        end_time_layout.addWidget(self.end_time_spin)
        end_time_layout.addWidget(self.end_time_now_btn)
        basic_layout.addRow("End Time (s):", end_time_layout)
        basic_group.setLayout(basic_layout)

        # Geometry properties
        geom_group = QGroupBox("Geometry")
        geom_layout = QVBoxLayout()

        # Rectangle geometry (default)
        self.rect_widget = QWidget()
        rect_layout = QVBoxLayout()

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

        rect_layout.addWidget(self.rect_radio)
        rect_layout.addLayout(coords_layout)
        self.rect_widget.setLayout(rect_layout)

        # Engine points geometry
        self.engines_widget = QWidget()
        engines_layout = QVBoxLayout()

        # Engine groups list
        groups_layout = QHBoxLayout()
        self.groups_list = QListWidget()
        self.groups_list.itemSelectionChanged.connect(self.on_group_selected)

        groups_btn_layout = QVBoxLayout()
        self.add_group_btn = QPushButton("Add Group")
        self.remove_group_btn = QPushButton("Remove Group")
        self.add_group_btn.clicked.connect(self.add_engine_group)
        self.remove_group_btn.clicked.connect(self.remove_engine_group)

        groups_btn_layout.addWidget(self.add_group_btn)
        groups_btn_layout.addWidget(self.remove_group_btn)
        groups_btn_layout.addStretch()

        groups_layout.addWidget(self.groups_list)
        groups_layout.addLayout(groups_btn_layout)

        # Points for selected group
        points_layout = QHBoxLayout()
        self.points_list = QListWidget()

        points_btn_layout = QVBoxLayout()
        self.add_point_btn = QPushButton("Add Point")
        self.remove_point_btn = QPushButton("Remove Point")
        self.add_point_btn.clicked.connect(self.add_point)
        self.remove_point_btn.clicked.connect(self.remove_point)

        points_btn_layout.addWidget(self.add_point_btn)
        points_btn_layout.addWidget(self.remove_point_btn)
        points_btn_layout.addStretch()

        points_layout.addWidget(self.points_list)
        points_layout.addLayout(points_btn_layout)

        engines_layout.addLayout(groups_layout)
        engines_layout.addLayout(points_layout)
        self.engines_widget.setLayout(engines_layout)

        # Initially show rectangle widget
        geom_layout.addWidget(self.rect_widget)
        geom_layout.addWidget(self.engines_widget)
        self.engines_widget.hide()

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
        self.id_edit.currentTextChanged.connect(self.on_id_changed)
        self.start_frame_spin.valueChanged.connect(self.on_start_frame_changed)
        self.start_time_spin.valueChanged.connect(self.on_start_time_changed)
        self.end_frame_spin.valueChanged.connect(self.on_end_frame_changed)
        self.end_time_spin.valueChanged.connect(self.on_end_time_changed)
        self.start_now_btn.clicked.connect(self.on_start_now)
        self.start_time_now_btn.clicked.connect(self.on_start_now)
        self.end_now_btn.clicked.connect(self.on_end_now)
        self.end_time_now_btn.clicked.connect(self.on_end_now)

    def on_vehicle_changed(self):
        """Handle vehicle combo editing finished to add new vehicles."""
        text = self.vehicle_combo.currentText()
        if text and text not in [self.vehicle_combo.itemText(i) for i in range(self.vehicle_combo.count())]:
            self.vehicle_combo.addItem(text)

    def set_current_frame_info(self, frame_idx: int, fps: float, time_unit: str):
        """Set current frame information for now buttons."""
        self.current_frame_idx = frame_idx
        self.current_fps = fps
        self.time_unit = time_unit

    def set_roi(self, roi: ROIData):
        """Set current ROI for editing."""
        self.current_roi = roi
        self.id_edit.setCurrentText(roi.id)
        self.label_edit.setText(roi.label)
        vehicle = roi.vehicle if roi.vehicle else ''
        self.vehicle_combo.setCurrentText(vehicle)
        self.measurement_unit_edit.setText(roi.measurement_unit)

        # Set start and end times
        start_time = roi.start_time
        end_time = roi.end_time

        if start_time is not None:
            if self.time_unit == "frames":
                frame_val = start_time
                time_val = start_time / self.current_fps if self.current_fps else 0
            else:
                time_val = start_time
                frame_val = int(start_time * self.current_fps) if self.current_fps else 0
            self.start_frame_spin.setValue(frame_val)
            self.start_time_spin.setValue(time_val)
        else:
            self.start_frame_spin.setValue(0)
            self.start_time_spin.setValue(0)

        if end_time is not None:
            if self.time_unit == "frames":
                frame_val = end_time
                time_val = end_time / self.current_fps if self.current_fps else 0
            else:
                time_val = end_time
                frame_val = int(end_time * self.current_fps) if self.current_fps else 0
            self.end_frame_spin.setValue(frame_val)
            self.end_time_spin.setValue(time_val)
        else:
            self.end_frame_spin.setValue(0)
            self.end_time_spin.setValue(0)

        if roi.id == "engines":
            self.rect_widget.hide()
            self.engines_widget.show()
            # Load engine groups
            self.groups_list.clear()
            if hasattr(roi, 'points') and roi.points:
                for group_name in roi.points.keys():
                    self.groups_list.addItem(group_name)
            # Emit empty group selection initially
            self.engine_group_selected.emit("")
        else:
            self.engines_widget.hide()
            self.rect_widget.show()
            self.rect_radio.setChecked(roi.is_rectangle())
            self.x_spin.setValue(roi.x)
            self.y_spin.setValue(roi.y)
            self.w_spin.setValue(roi.w)
            self.h_spin.setValue(roi.h)
            # Emit empty group selection for non-engine ROIs
            self.engine_group_selected.emit("")

    def apply_changes(self):
        """Apply changes to current ROI."""
        if not self.current_roi:
            return

        self.current_roi.id = self.id_edit.currentText()
        self.current_roi.label = self.label_edit.text()
        vehicle_text = self.vehicle_combo.currentText()
        self.current_roi.vehicle = vehicle_text if vehicle_text else None
        self.current_roi.measurement_unit = self.measurement_unit_edit.text()

        # Set start and end times
        if self.time_unit == "frames":
            self.current_roi.start_time = self.start_frame_spin.value()
            self.current_roi.end_time = self.end_frame_spin.value()
        else:
            self.current_roi.start_time = self.start_time_spin.value()
            self.current_roi.end_time = self.end_time_spin.value()

        if self.current_roi.id == "engines":
            # For engines, points are already managed in the points dict
            # Clear rectangle coordinates for engines
            self.current_roi.x = 0
            self.current_roi.y = 0
            self.current_roi.w = 0
            self.current_roi.h = 0
        else:
            # For other types, use rectangle coordinates
            self.current_roi.x = self.x_spin.value()
            self.current_roi.y = self.y_spin.value()
            self.current_roi.w = self.w_spin.value()
            self.current_roi.h = self.h_spin.value()

        self.properties_changed.emit(self.current_roi)

    def reset_changes(self):
        """Reset changes."""
        if self.current_roi:
            self.set_roi(self.current_roi)

    def on_id_changed(self, id_text):
        """Handle ID combo box change to show appropriate geometry."""
        if id_text == "engines":
            self.rect_widget.hide()
            self.engines_widget.show()
        else:
            self.engines_widget.hide()
            self.rect_widget.show()

    def on_group_selected(self):
        """Handle engine group selection to show its points."""
        current_item = self.groups_list.currentItem()
        if current_item:
            group_name = current_item.text()
            self.load_points_for_group(group_name)
            self.engine_group_selected.emit(group_name)
        else:
            self.engine_group_selected.emit("")  # No group selected

    def add_engine_group(self):
        """Add a new engine group."""
        if not self.current_roi:
            return
        from PyQt6.QtWidgets import QInputDialog
        group_name, ok = QInputDialog.getText(self, "Add Engine Group", "Group name:")
        if ok and group_name:
            if not self.groups_list.findItems(group_name, Qt.MatchFlag.MatchExactly):
                self.groups_list.addItem(group_name)
                # Initialize empty points list for this group
                if not hasattr(self.current_roi, 'points'):
                    self.current_roi.points = {}
                self.current_roi.points[group_name] = []

    def remove_engine_group(self):
        """Remove the selected engine group."""
        if not self.current_roi:
            return
        current_item = self.groups_list.currentItem()
        if current_item:
            group_name = current_item.text()
            row = self.groups_list.row(current_item)
            self.groups_list.takeItem(row)
            if hasattr(self.current_roi, 'points') and group_name in self.current_roi.points:
                del self.current_roi.points[group_name]

    def add_point(self):
        """Add a point to the selected engine group."""
        if not self.current_roi:
            return
        current_group = self.groups_list.currentItem()
        if current_group:
            from PyQt6.QtWidgets import QInputDialog
            point_text, ok = QInputDialog.getText(self, "Add Point", "Point coordinates (x,y):")
            if ok and point_text:
                try:
                    # Parse coordinates like "154,980"
                    coords = point_text.split(',')
                    if len(coords) == 2:
                        x, y = int(coords[0].strip()), int(coords[1].strip())
                        group_name = current_group.text()
                        if hasattr(self.current_roi, 'points') and group_name in self.current_roi.points:
                            self.current_roi.points[group_name].append([x, y])
                            self.load_points_for_group(group_name)
                except ValueError:
                    pass  # Invalid coordinates

    def remove_point(self):
        """Remove the selected point from the current group."""
        if not self.current_roi:
            return
        current_group = self.groups_list.currentItem()
        current_point = self.points_list.currentItem()
        if current_group and current_point:
            group_name = current_group.text()
            point_index = self.points_list.row(current_point)
            if hasattr(self.current_roi, 'points') and group_name in self.current_roi.points:
                if 0 <= point_index < len(self.current_roi.points[group_name]):
                    del self.current_roi.points[group_name][point_index]
                    self.load_points_for_group(group_name)

    def on_start_frame_changed(self, value):
        if self.current_fps:
            self.start_time_spin.blockSignals(True)
            self.start_time_spin.setValue(value / self.current_fps)
            self.start_time_spin.blockSignals(False)

    def on_start_time_changed(self, value):
        if self.current_fps:
            self.start_frame_spin.blockSignals(True)
            self.start_frame_spin.setValue(int(value * self.current_fps))
            self.start_frame_spin.blockSignals(False)

    def on_end_frame_changed(self, value):
        if self.current_fps:
            self.end_time_spin.blockSignals(True)
            self.end_time_spin.setValue(value / self.current_fps)
            self.end_time_spin.blockSignals(False)

    def on_end_time_changed(self, value):
        if self.current_fps:
            self.end_frame_spin.blockSignals(True)
            self.end_frame_spin.setValue(int(value * self.current_fps))
            self.end_frame_spin.blockSignals(False)

    def on_start_now(self):
        self.start_frame_spin.setValue(self.current_frame_idx)

    def on_end_now(self):
        self.end_frame_spin.setValue(self.current_frame_idx)