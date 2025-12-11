import numpy as np
from typing import Tuple, Dict, Optional, Any
from utils import display_image
from .ocr import extract_values_from_roi
from .engine_detection import detect_engine_status
from .fuel_level_extraction import extract_fuel_levels
from utils.logger import get_logger
from .roi_manager import get_default_manager, ROIManager
import traceback  # Import at the top level instead of in exception handler
from utils.measurement_converter import convert_measurement

# Initialize logger
logger = get_logger(__name__)

# This module is now fully config-driven. ROI coordinates and activation windows
# are provided by `ocr.roi_manager.ROIManager` via `get_default_manager()`.

def slice_roi(img, y, h, x, w):
    """Helper function to safely slice an ROI from an image."""
    ih, iw = img.shape[0], img.shape[1]
    y0 = max(0, int(y))
    x0 = max(0, int(x))
    y1 = min(ih, int(y + h))
    x1 = min(iw, int(x + w))
    if y0 >= y1 or x0 >= x1:
        return None
    return img[y0:y1, x0:x1]

def preprocess_image(image: np.ndarray, display_rois: bool = False, roi_manager: Optional[ROIManager] = None, frame_idx: Optional[int] = None) -> Dict[str, Optional[np.ndarray]]:
    """
    DEPRECATED: This function is deprecated and will be removed in a future version.
    ROI preprocessing is now handled directly in extract_data().
    
    Preprocess the image to extract ROIs for Superheavy Speed, Superheavy Altitude, Starship Speed, Starship Altitude, and Time.

    Args:
        image (numpy.ndarray): The image to process.
        display_rois (bool): Whether to display the ROIs.

    Returns:
        tuple: A tuple containing the ROIs for Superheavy Speed, Superheavy Altitude, Starship Speed, Starship Altitude, and Time.
    """
    import warnings
    warnings.warn("preprocess_image() is deprecated and will be removed in a future version. "
                  "ROI preprocessing is now handled directly in extract_data().", 
                  DeprecationWarning, stacklevel=2)

    # Input validation
    if image is None:
        logger.error("Input image is None")
        return {}
    
    logger.debug(f"Preprocessing image of shape {image.shape}")

    # Decide which ROI definitions to use; require ROIManager (default loaded if None)
    use_manager = roi_manager
    if use_manager is None:
        try:
            use_manager = get_default_manager()
        except Exception:
            use_manager = None

    if use_manager is None:
        logger.error("ROI manager not available; cannot perform config-driven ROI slicing")
        return {}
    
    try:
        # Build mapping roi_id -> cropped image for all active ROIs
        rois_map: Dict[str, Optional[np.ndarray]] = {}
        active = use_manager.get_active_rois(frame_idx)

        for roi in active:
            try:
                rois_map[roi.id] = slice_roi(image, roi.y, roi.h, roi.x, roi.w)
            except Exception:
                logger.exception(f"Failed to slice ROI {roi.id}; inserting empty ROI")
                rois_map[roi.id] = None
        
        # Debug logging
        if display_rois:
            logger.debug("Displaying ROI slices for visual inspection")
            for roi in active:
                title = roi.id
                if roi.label:
                    title = f"{roi.id} ({roi.label})"
                roi_img = slice_roi(image, roi.y, roi.h, roi.x, roi.w)
                display_image(roi_img, title)

        return rois_map
    
    except Exception as e:
        logger.error(f"Error extracting ROIs: {str(e)}")
        logger.debug(f"Image shape: {image.shape if image is not None else 'None'}")
        return {}


def extract_time_data(time_roi: np.ndarray, display_rois: bool, debug: bool, zero_time_met: bool, regex: str = r'[+-]\d{2}:\d{2}:\d{2}') -> Dict:
    """
    Extract time data from the ROI.

    Args:
        time_roi (numpy.ndarray): The ROI for time.
        display_rois (bool): Whether to display the ROIs.
        debug (bool): Whether to enable debug prints.
        zero_time_met (bool): Whether a frame with time 0:0:0 has been met.

    Returns:
        dict: A dictionary containing the extracted time data.
    """
    logger.debug("Extracting time data from ROI")
    
    if zero_time_met:
        if debug:
            logger.debug("Zero time already met, returning default zero time")
        return {"sign": "+", "hours": 0, "minutes": 0, "seconds": 0}
    
    try:
        time_data = extract_values_from_roi(time_roi, mode="time", display_transformed=display_rois, debug=debug, regex=regex)
        
        if debug:
            if time_data:
                logger.debug(f"Extracted time: {time_data.get('sign')} " +
                           f"{time_data.get('hours', 0):02}:{time_data.get('minutes', 0):02}:{time_data.get('seconds', 0):02}")
                
                # Check if this is T-0 or T+0 time
                if time_data.get('hours', 0) == 0 and time_data.get('minutes', 0) == 0 and time_data.get('seconds', 0) == 0:
                    logger.debug("Found T-0/T+0 time point!")
            else:
                logger.debug("No time data extracted from time ROI")
        
        return time_data
    except Exception as e:
        logger.error(f"Error extracting time data: {str(e)}")
        logger.debug(traceback.format_exc())
        return {}


def extract_data(image: np.ndarray, display_rois: bool = False, debug: bool = False, zero_time_met: bool = False, roi_manager: Optional[ROIManager] = None, frame_idx: Optional[int] = None) -> Dict[str, any]:
    """
    Extract data from an image, returning {'vehicles': {...}, 'time': {...}}.
    """
    if debug:
        logger.debug("Starting data extraction from image")

    mgr = roi_manager or get_default_manager()
    vehicles_data = {}
    time_data = {}

    # Initialize vehicles from config
    for vehicle in mgr.vehicles:
        vehicles_data[vehicle] = {"speed": None, "altitude": None, "fuel": {"lox": {"fullness": 0}, "ch4": {"fullness": 0}}, "engines": {}}

    # Get active ROIs and process
    active_rois = mgr.get_active_rois(frame_idx)
    fuel_extracted = False
    for roi in active_rois:
        # Slice the ROI image directly
        roi_img = slice_roi(image, roi.y, roi.h, roi.x, roi.w)
        if roi_img is None:
            continue

        if roi.id == "time":
            time_data = extract_time_data(roi_img, display_rois, debug, zero_time_met, roi.measurement_unit)
        elif roi.vehicle:
            vehicle = roi.vehicle
            if roi.id == "speed":
                data = extract_values_from_roi(roi_img, mode="speed", display_transformed=display_rois, debug=debug)
                value = data.get("value")
                if value is not None and roi.measurement_unit != "km/h":
                    value = convert_measurement(value, "speed", roi.measurement_unit)
                vehicles_data[vehicle]["speed"] = value
            elif roi.id == "altitude":
                data = extract_values_from_roi(roi_img, mode="altitude", display_transformed=display_rois, debug=debug)
                value = data.get("value")
                if value is not None and roi.measurement_unit != "km":
                    value = convert_measurement(value, "altitude", roi.measurement_unit)
                vehicles_data[vehicle]["altitude"] = value
            elif roi.id == "engines":
                # Engine detection using roi.points
                engines = detect_engine_status(roi.points, image) if roi.points else {}
                vehicles_data[vehicle]["engines"] = engines
            elif roi.id == "fuel" and not fuel_extracted:
                # Extract fuel levels only once when encountering a fuel ROI
                try:
                    fuel_data = extract_fuel_levels(image, debug)
                    for vehicle in mgr.vehicles:
                        vehicles_data[vehicle]["fuel"] = fuel_data.get(vehicle, {"lox": {"fullness": 0}, "ch4": {"fullness": 0}})
                    fuel_extracted = True
                    logger.debug("Fuel levels extracted for active fuel ROI")
                except Exception as e:
                    logger.error(f"Error extracting fuel levels: {str(e)}")
                    if debug:
                        logger.debug(traceback.format_exc())

    # No longer need the separate fuel extraction block at the end

    if debug:
        logger.debug("Data extraction complete")
        for vehicle, data in vehicles_data.items():
            logger.debug(f"Final data - {vehicle}: speed={data['speed']}, altitude={data['altitude']}")
        if time_data:
            sign = time_data.get("sign", "")
            h = time_data.get("hours", 0)
            m = time_data.get("minutes", 0)
            s = time_data.get("seconds", 0)
            logger.debug(f"Final data - Time: {sign} {h:02}:{m:02}:{s:02}")
        else:
            logger.debug("Final data - Time: None")
    
    return {"vehicles": vehicles_data, "time": time_data}
