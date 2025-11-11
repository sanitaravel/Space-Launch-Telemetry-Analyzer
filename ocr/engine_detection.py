import numpy as np
from typing import Dict, List, Union, Optional
from numba import njit
from utils.constants import WHITE_THRESHOLD
from utils.logger import get_logger
from .roi_manager import get_default_manager, ROIManager

# Initialize logger
logger = get_logger(__name__)

@njit
def check_engines_numba(image: np.ndarray, coordinates: np.ndarray, white_threshold: int) -> list:
    """
    Optimized engine status check using numba.
    
    Args:
        image: The image to process
        coordinates: NumPy array of (x, y) coordinate tuples
        white_threshold: Brightness threshold for determining engine status
        
    Returns:
        List of boolean values indicating engine status
    """
    status = []
    for x, y in coordinates:
        if 0 <= y < image.shape[0] and 0 <= x < image.shape[1]:
            pixel = image[y, x]
            is_on = True
            for channel in pixel:
                if channel < white_threshold:
                    is_on = False
                    break
            status.append(is_on)
        else:
            status.append(False)
    return status

def check_engines(image: np.ndarray, engine_coords: Dict, debug: bool, engine_type: str) -> Dict:
    """
    Check the status of engines based on pixel values at specific coordinates.
    
    Args:
        image (numpy.ndarray): The image to process.
        engine_coords (Dict): Dictionary with engine sections as keys and coordinates as values.
        debug (bool): Whether to enable debug prints.
        engine_type (str): Type of engine ('Superheavy' or 'Starship') for debug messages.
        
    Returns:
        Dict: Dictionary with engine sections as keys and lists of boolean status as values.
    """
    # Initialize results dictionary directly
    engine_status = {}
    
    if engine_coords is None:
        if debug:   
            logger.debug(f"No {engine_type} engine coordinates found.")
        return engine_status

    if debug:
        logger.debug(f"Checking {engine_type} engines with threshold: {WHITE_THRESHOLD}")
        logger.debug(f"Image shape: {image.shape}, checking {sum(len(coords) for coords in engine_coords.values())} engine points")
    
    # Check engines
    for section, coordinates in engine_coords.items():
        # Avoid unnecessary array creation if already numpy array
        coords_array = coordinates if isinstance(coordinates, np.ndarray) else np.array(coordinates)
            
        # Store results directly in dictionary without intermediate list
        engine_status[section] = check_engines_numba(image, coords_array, WHITE_THRESHOLD)
        
        if debug:
            active_count = sum(engine_status[section])
            logger.debug(f"{engine_type} {section} summary: {active_count} active engines out of {len(coords_array)}")
                    
    return engine_status


def detect_engine_status(image: np.ndarray, debug: bool = False, roi_manager: Optional[ROIManager] = None, frame_idx: Optional[int] = None) -> Dict:
    """
    Detect whether engines are turned on by checking pixel values at specific coordinates.

    Args:
        image (numpy.ndarray): The image to process.
        debug (bool): Whether to enable debug prints.

    Returns:
        dict: A dictionary containing engine statuses for Superheavy and Starship.
    """
    # Determine whether any engine ROIs are configured. If a ROI manager
    # is provided (or can be loaded), prefer it for a conservative decision
    # about whether engine detection should run. If no manager is available
    # assume no engine ROIs.
    if debug:
        logger.debug(f"Starting engine detection on image of shape {image.shape}")

    mgr = roi_manager
    if mgr is None:
        try:
            mgr = get_default_manager()
        except Exception:
            mgr = None

    has_engine_roi = False
    if mgr is not None:
        try:
            active = mgr.get_active_rois(frame_idx)
            for r in active:
                if r.id == "engines" and r.vehicle in ["superheavy", "starship"]:
                    has_engine_roi = True
                    break
        except Exception:
            has_engine_roi = False

    # Attempt to get engine coordinate points from ROI manager if present.
    # ROI entries should have a 'points' dictionary mirroring the structure
    # used by the legacy constants. If not present, fall back to constants.
    sh_points = None
    ss_points = None
    if mgr is not None and has_engine_roi:
        try:
            for r in mgr.get_active_rois(frame_idx):
                logger.debug(f"Found ROI with id: {r.id}, vehicle: {r.vehicle}, points: {getattr(r, 'points', None)}")
                if r.id == "engines" and r.vehicle == "superheavy" and getattr(r, "points", None):
                    sh_points = r.points
                if r.id == "engines" and r.vehicle == "starship" and getattr(r, "points", None):
                    ss_points = r.points
        except Exception:
            # If reading from manager fails, we'll fall back to constants below
            sh_points = None
            ss_points = None

    # Check Superheavy engines
    superheavy_engines = check_engines(image, sh_points, debug, "Superheavy")

    # Check Starship engines
    starship_engines = check_engines(image, ss_points, debug, "Starship")

    # Calculate summary statistics for debugging
    if debug:
        sh_active = sum(sum(1 for e in engines if e) for engines in superheavy_engines.values())
        sh_total = sum(len(engines) for engines in superheavy_engines.values())
        ss_active = sum(sum(1 for e in engines if e) for engines in starship_engines.values())
        ss_total = sum(len(engines) for engines in starship_engines.values())
        logger.debug(f"Engine detection summary - Superheavy: {sh_active}/{sh_total} active, Starship: {ss_active}/{ss_total} active")

    return {"superheavy": superheavy_engines, "starship": starship_engines}
