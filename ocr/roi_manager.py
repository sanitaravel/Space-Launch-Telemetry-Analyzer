import json
import threading
from typing import Dict, List, Optional
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


class ROI:
    def __init__(self, data: Dict):
        # expected keys: id,label,y,h,x,w,start_time,end_time,vehicle,measurement_unit,points
        self.id = data.get("id")
        self.label = data.get("label")
        self.y = int(data.get("y", 0))
        self.h = int(data.get("h", 0))
        self.x = int(data.get("x", 0))
        self.w = int(data.get("w", 0))
        # In our config these are frame indices (or null)
        self.start_frame = None if data.get("start_time") is None else int(data.get("start_time"))
        self.end_frame = None if data.get("end_time") is None else int(data.get("end_time"))
        self.vehicle = data.get("vehicle")  # New: Vehicle assignment
        self.measurement_unit = data.get("measurement_unit")  # New: Unit for extraction
        # Optional pre-defined engine/point coordinates stored in the ROI config
        pts = data.get("points")
        if pts is None:
            self.points = None
        else:
            # Normalize coordinates to lists of two ints for safety
            normalized: Dict[str, List[List[int]]] = {}
            try:
                for section, coords in pts.items():
                    normalized_coords: List[List[int]] = []
                    for p in coords:
                        # allow tuples/lists and coerce values to ints
                        if not (isinstance(p, (list, tuple)) and len(p) >= 2):
                            continue
                        normalized_coords.append([int(p[0]), int(p[1])])
                    normalized[section] = normalized_coords
            except Exception:
                # If the structure is unexpected, keep raw value to allow downstream handling
                normalized = pts
            self.points = normalized

    def is_active(self, frame_idx: Optional[int]) -> bool:
        # If frame_idx is None, treat ROI as active
        if frame_idx is None:
            return True
        if self.start_frame is not None and frame_idx < self.start_frame:
            return False
        if self.end_frame is not None and frame_idx >= self.end_frame:
            return False
        return True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "label": self.label,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "vehicle": self.vehicle,  # New
            "measurement_unit": self.measurement_unit,  # New
            "points": self.points,
        }


class ROIManager:
    def __init__(self, config_path: Optional[str] = None):
        self._lock = threading.RLock()
        self.config_path = Path(config_path) if config_path else Path("configs/default_rois.json")
        self.version = None
        self.time_unit = None
        self.vehicles: List[str] = []  # New: List of vehicles from config
        self._rois: List[ROI] = []
        self.reload()

    def reload(self) -> None:
        """Reload the ROI config file. Safe to call at runtime."""
        with self._lock:
            try:
                logger.debug(f"Loading ROI config from {self.config_path}")
                text = self.config_path.read_text(encoding="utf-8")
                data = json.loads(text)
                self.version = data.get("version")
                self.time_unit = data.get("time_unit")
                self.vehicles = data.get("vehicles", [])  # New: Load vehicles list
                rois = data.get("rois", [])
                parsed: List[ROI] = []
                for r in rois:
                    try:
                        parsed.append(ROI(r))
                    except Exception as e:
                        logger.error(f"Failed to parse ROI entry {r}: {e}")
                self._rois = parsed
                logger.info(f"Loaded {len(self._rois)} ROIs for vehicles {self.vehicles} (time_unit={self.time_unit})")
            except FileNotFoundError:
                logger.error(f"ROI config not found at {self.config_path}")
                self._rois = []
            except Exception as e:
                logger.exception(f"Error loading ROI config: {e}")
                self._rois = []

    def get_active_rois(self, frame_idx: Optional[int] = None) -> List[ROI]:
        """Return list of ROIs active for a given frame index (or all if None)."""
        with self._lock:
            return [r for r in self._rois if r.is_active(frame_idx)]

    def get_roi_for_role(self, role: str, frame_idx: Optional[int] = None) -> Optional[ROI]:
        """Return the first ROI matching match_to_role==role and active at frame_idx, or None."""
        with self._lock:
            for r in self._rois:
                if r.match_to_role == role and r.is_active(frame_idx):
                    return r
            return None

    def get_roi_for_id(self, roi_id: str, vehicle: Optional[str] = None, frame_idx: Optional[int] = None) -> Optional[ROI]:
        """Return the first ROI matching id and optionally vehicle, active at frame_idx."""
        with self._lock:
            for r in self._rois:
                if r.id == roi_id and (vehicle is None or r.vehicle == vehicle) and r.is_active(frame_idx):
                    return r
            return None

    def get_rois_for_vehicle(self, vehicle: str, frame_idx: Optional[int] = None) -> List[ROI]:
        """Return ROIs for a specific vehicle, active at frame_idx."""
        with self._lock:
            return [r for r in self._rois if r.vehicle == vehicle and r.is_active(frame_idx)]

    def list_rois(self) -> List[Dict]:
        with self._lock:
            return [r.to_dict() for r in self._rois]


# Lazy singleton
_default_manager: Optional[ROIManager] = None

def get_default_manager() -> ROIManager:
    global _default_manager
    if _default_manager is None:
        # Update to load a specific config, e.g., for SpaceX Starship
        config_path = "configs/spacex/starship/flight_6_rois.json"  # Or make dynamic
        _default_manager = ROIManager(config_path)
    return _default_manager


def set_default_manager_config(config_path: str) -> ROIManager:
    """Replace the global default ROIManager with one using the provided config path.

    Returns the new default manager instance.
    """
    global _default_manager
    try:
        _default_manager = ROIManager(config_path)
        logger.info(f"Default ROI manager set to config: {config_path}")
    except Exception as e:
        logger.exception(f"Failed to set default ROI manager to {config_path}: {e}")
        # Fall back to an empty manager to avoid crash
        _default_manager = ROIManager()
    return _default_manager
