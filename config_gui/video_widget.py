"""
Video widget for displaying video with ROI overlays.
"""
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QImage
import cv2
import numpy as np

from .models import ROIData


class VideoWidget(QOpenGLWidget):
    """Widget for displaying video with ROI overlays."""
    roi_selected = pyqtSignal(ROIData)
    point_added = pyqtSignal()  # Signal when a point is added to an engine group

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
        self.vehicle_colors = {}  # Will be populated dynamically
        self.current_engine_group = ""  # Current engine group for point addition
        self.current_roi = None  # Current ROI being edited
        self.mode = 'select'  # 'select' or 'zoom'
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.last_pos = None

    def set_frame(self, frame: np.ndarray):
        self.frame = frame
        self.update()

    def set_rois(self, rois):
        self.rois = rois
        self.update_vehicle_colors()
        self.update()

    def set_current_roi(self, roi_dict):
        """Set the current ROI being edited."""
        self.current_roi = roi_dict

    def set_current_engine_group(self, group_name: str):
        """Set the current engine group for point addition."""
        self.current_engine_group = group_name

    def set_mode(self, mode: str):
        """Set the interaction mode: 'select' or 'zoom'."""
        self.mode = mode
        self.update()

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

    def update_vehicle_colors(self):
        """Update vehicle color mapping based on current ROIs."""
        vehicles = set()
        for roi in self.rois:
            vehicle = roi.get("vehicle")
            if vehicle:
                vehicles.add(vehicle)

        # Sort vehicles for consistent color assignment
        vehicles = sorted(vehicles)

        # Generate distinct colors for each vehicle
        self.vehicle_colors = {}
        num_vehicles = len(vehicles)

        if num_vehicles == 0:
            return

        for i, vehicle in enumerate(vehicles):
            # Use HSV color space to generate distinct colors
            hue = (i * 360) // num_vehicles  # Evenly distribute hues
            saturation = 255  # Maximum saturation for vibrant colors
            value = 255  # Full brightness

            # Convert HSV to RGB (fixed conversion)
            h = hue / 60.0
            c = saturation / 255.0
            x = c * (1 - abs(h % 2 - 1))
            m = (value / 255.0) - c

            if 0 <= h < 1:
                r, g, b = c, x, 0
            elif 1 <= h < 2:
                r, g, b = x, c, 0
            elif 2 <= h < 3:
                r, g, b = 0, c, x
            elif 3 <= h < 4:
                r, g, b = 0, x, c
            elif 4 <= h < 5:
                r, g, b = x, 0, c
            else:
                r, g, b = c, 0, x

            self.vehicle_colors[vehicle] = (
                int((r + m) * 255),
                int((g + m) * 255),
                int((b + m) * 255)
            )

    def get_roi_color(self, roi):
        """Get color for ROI based on vehicle and type."""
        vehicle = roi.get("vehicle", "")
        roi_type = roi.get("id", "")

        # Get base color for vehicle (or default if not found)
        base_color = self.vehicle_colors.get(vehicle, (128, 128, 128))  # Gray default

        # Variations for different ROI types
        type_variations = {
            "engines": base_color,
            "speed": tuple(min(255, c + 50) for c in base_color),  # Lighter
            "altitude": tuple(max(0, c - 50) for c in base_color),  # Darker
            "time": (base_color[1], base_color[2], base_color[0]),  # Rotated colors
        }

        return type_variations.get(roi_type, base_color)

    def paintEvent(self, event):
        painter = QPainter(self)
        # Clear background to black
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        if self.frame is not None:
            h, w, c = self.frame.shape
            bytes_per_line = 3 * w
            qimg = QImage(self.frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()

            if self.mode == 'zoom':
                # Use zoom_factor and pan
                scaled_w = int(w * self.zoom_factor)
                scaled_h = int(h * self.zoom_factor)
                x = self.pan_x
                y = self.pan_y
                scaled_qimg = qimg.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.IgnoreAspectRatio)
                painter.drawImage(x, y, scaled_qimg)
                self.display_scale = self.zoom_factor
                self.offset_x = x
                self.offset_y = y
            else:
                # Fit to widget
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
                    color = self.get_roi_color(roi)
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

                    # Draw engine points if they exist
                    if "points" in roi and isinstance(roi["points"], dict):
                        for group_name, pts in roi["points"].items():
                            if not pts:
                                continue
                            painter.setPen(QPen(qcolor, 2))
                            painter.setBrush(QBrush(qcolor))
                            for pt in pts:
                                px = int((pt[0] * self.scale * self.display_scale) + self.offset_x)
                                py = int((pt[1] * self.scale * self.display_scale) + self.offset_y)
                                # Draw smaller circles that scale with display
                                radius = max(1, int(2 * self.display_scale))
                                painter.drawEllipse(px - radius, py - radius, radius * 2, radius * 2)
        painter.end()

    def mousePressEvent(self, event):
        if self.mode == 'zoom':
            if event.button() == Qt.MouseButton.LeftButton:
                self.is_panning = True
                self.last_pos = event.pos()
        elif self.mode == 'select':
            if event.button() == Qt.MouseButton.LeftButton:
                self.start_pos = event.pos()
                self.is_selecting = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mode == 'zoom' and self.is_panning:
            delta = event.pos() - self.last_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == 'zoom':
            if event.button() == Qt.MouseButton.LeftButton:
                self.is_panning = False
        elif self.mode == 'select':
            if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
                self.is_selecting = False
                end_pos = event.pos()
                if self.start_pos and self.frame is not None:
                    # Check if we're adding a point to an engine group
                    if (self.current_roi and 
                        self.current_roi.get('id') == 'engines' and 
                        self.current_engine_group):
                        # Add point to engine group
                        h, w, c = self.frame.shape
                        # Use the click position (end_pos) for point addition
                        start_x = (end_pos.x() - self.offset_x) / self.display_scale
                        start_y = (end_pos.y() - self.offset_y) / self.display_scale
                        
                        x = int(start_x)
                        y = int(start_y)
                        
                        # Add point to the current ROI's points
                        if 'points' not in self.current_roi:
                            self.current_roi['points'] = {}
                        if self.current_engine_group not in self.current_roi['points']:
                            self.current_roi['points'][self.current_engine_group] = []
                        
                        self.current_roi['points'][self.current_engine_group].append([x, y])
                        self.point_added.emit()
                        self.update()  # Refresh display
                    else:
                        # Normal ROI creation
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

    def wheelEvent(self, event):
        if self.mode == 'zoom':
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_factor *= 1.2
            else:
                self.zoom_factor /= 1.2
            self.zoom_factor = max(0.1, min(10, self.zoom_factor))  # clamp
            self.update()
        super().wheelEvent(event)