"""
Data models for ROI configuration.
"""
import json
import os
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import QMessageBox

from utils.logger import get_logger

logger = get_logger(__name__)


class ROIData:
    """Data class for ROI information."""
    def __init__(self, roi_dict: Optional[Dict[str, Any]] = None):
        self.id = ""
        self.vehicle = None
        self.label = ""
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0
        self.start_time = None
        self.end_time = None
        self.measurement_unit = ""
        self.points = {}  # For engine ROIs

        if roi_dict:
            self.from_dict(roi_dict)

    def from_dict(self, data: Dict[str, Any]):
        """Load from dictionary."""
        self.id = data.get('id', '')
        self.vehicle = data.get('vehicle')
        self.label = data.get('label', '')
        self.x = data.get('x', 0)
        self.y = data.get('y', 0)
        self.w = data.get('w', 0)
        self.h = data.get('h', 0)
        self.start_time = data.get('start_time')
        self.end_time = data.get('end_time')
        self.measurement_unit = data.get('measurement_unit', '')
        self.points = data.get('points', {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'id': self.id,
            'vehicle': self.vehicle,
            'label': self.label,
            'x': self.x,
            'y': self.y,
            'w': self.w,
            'h': self.h,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'measurement_unit': self.measurement_unit
        }
        if self.points:
            result['points'] = self.points
        return result

    def is_rectangle(self) -> bool:
        """Check if this is a rectangle ROI."""
        return not bool(self.points)

    def get_rect(self):
        """Get rectangle for display."""
        from PyQt6.QtCore import QRectF
        return QRectF(self.x, self.y, self.w, self.h)


class ROIConfig:
    """Handles ROI configuration file operations."""
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.version = 1
        self.video_source = {"type": "twitter/x", "url": ""}
        self.time_unit = "frames"
        self.vehicles = ["starship"]
        self.rois: List[ROIData] = []

        if config_path and os.path.exists(config_path):
            self.load_config(config_path)

    def load_config(self, config_path: str):
        """Load configuration from file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.version = data.get('version', 1)
            self.video_source = data.get('video_source', {"type": "twitter/x", "url": ""})
            self.time_unit = data.get('time_unit', 'frames')
            self.vehicles = data.get('vehicles', ['starship'])
            self.rois = [ROIData(roi) for roi in data.get('rois', [])]

            logger.info(f"Loaded config from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            QMessageBox.warning(None, "Load Error", f"Failed to load config: {e}")

    def save_config(self, config_path: Optional[str] = None):
        """Save configuration to file."""
        if config_path:
            self.config_path = config_path

        if not self.config_path:
            return False

        try:
            # Update vehicles list based on vehicles used in ROIs
            used_vehicles = set()
            for roi in self.rois:
                if roi.vehicle is not None:
                    used_vehicles.add(roi.vehicle)
            self.vehicles = sorted(list(used_vehicles))

            # Increment version if updating an existing file
            if os.path.exists(self.config_path):
                self.version += 1

            data = {
                'version': self.version,
                'video_source': self.video_source,
                'time_unit': self.time_unit,
                'vehicles': self.vehicles,
                'rois': [roi.to_dict() for roi in self.rois]
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved config to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            QMessageBox.warning(None, "Save Error", f"Failed to save config: {e}")
            return False