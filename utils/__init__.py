"""
Utils package for the Starship Analyzer application.
Contains utility functions and constants.
"""

import cv2
import os
import numpy as np

# Import logger-related functions
from utils.logger import get_logger, start_new_session, set_global_log_level, LOG_LEVELS

# Import constants from constants.py
from utils.constants import (
    SUPERHEAVY_ENGINES, 
    STARSHIP_ENGINES,
    WHITE_THRESHOLD,
    G_FORCE_CONVERSION,
    FIGURE_SIZE,
    TITLE_FONT_SIZE,
    ENGINE_TIMELINE_PARAMS,
    ANALYZE_RESULTS_PLOT_PARAMS,
    FUEL_LEVEL_PLOT_PARAMS,
    COMPARE_FUEL_LEVEL_PARAMS,
    PLOT_MULTIPLE_LAUNCHES_PARAMS,
    ENGINE_PERFORMANCE_PARAMS
)

# Try to import other utility modules, fall back gracefully if not found
try:
    from utils.video_utils import get_video_files_from_flight_recordings, display_video_info
except ImportError:
    get_logger(__name__).warning("Could not import video_utils module")

try:
    from utils.validators import validate_number, validate_positive_number
except ImportError:
    get_logger(__name__).warning("Could not import validators module")

try:
    from utils.ui_helpers import separator
except ImportError:
    get_logger(__name__).warning("Could not import ui_helpers module")
    # Define a basic separator function as fallback
    def separator(length=50):
        return "-" * length

try:
    from utils.terminal import clear_screen
except ImportError:
    get_logger(__name__).warning("Could not import terminal module")
    # Define a basic clear_screen function as fallback
    import os
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

def display_image(image: np.ndarray, text: str) -> None:
    """
    Display an image in a window.

    Args:
        image (numpy.ndarray): The image to display.
        text (str): The text to display in the window title.
    """
    logger = get_logger(__name__)

    # Defensive: if image is None, nothing to display
    if image is None:
        logger.debug("display_image called with None image; skipping display")
        return

    try:
        # Attempt to use OpenCV GUI to display image. On headless systems
        # this will raise an error from OpenCV; catch and log a warning and
        # continue without raising so callers can remain headless-friendly.
        cv2.imshow(text, image)
        
        # Try to bring window to front (Windows-specific)
        try:
            cv2.setWindowProperty(text, cv2.WND_PROP_TOPMOST, 1)
        except:
            pass  # Ignore if not supported
        
        # Resize window if image is very small
        height, width = image.shape[:2]
        if width < 200 or height < 200:
            cv2.resizeWindow(text, max(width, 400), max(height, 300))
        
        print(f"\nDisplaying ROI: {text}")
        print("Press any key in the image window to continue...")
        
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except cv2.error as e:
        logger.warning("OpenCV GUI not available; skipping display: %s", e)
    except Exception as e:
        # Fallback for any other unexpected errors
        logger.warning("Failed to display image: %s", e)

def extract_launch_number(json_path: str) -> str:
    """
    Extract the launch number from a JSON file path.
    
    Args:
        json_path (str): Path to the JSON file
        
    Returns:
        str: The extracted launch number
    """
    return os.path.basename(os.path.dirname(json_path)).split('_')[-1]

__all__ = [
    # Functions defined in this file
    'display_image',
    'extract_launch_number',
    
    # Logger functions
    'get_logger',
    'start_new_session',
    'set_global_log_level',
    'LOG_LEVELS',
    
    # Constants
    'SUPERHEAVY_ENGINES',
    'STARSHIP_ENGINES',
    'WHITE_THRESHOLD',
    'G_FORCE_CONVERSION',
    'FIGURE_SIZE',
    'TITLE_FONT_SIZE',
    'ENGINE_TIMELINE_PARAMS',
    'ANALYZE_RESULTS_PLOT_PARAMS',
    'FUEL_LEVEL_PLOT_PARAMS',
    'COMPARE_FUEL_LEVEL_PARAMS',
    'PLOT_MULTIPLE_LAUNCHES_PARAMS',
    'ENGINE_PERFORMANCE_PARAMS',
    
    # Utility functions that might be imported
    'clear_screen',
    'separator',
]

# Dynamically add imported functions to __all__ if they exist
if 'get_video_files_from_flight_recordings' in globals():
    __all__.extend(['get_video_files_from_flight_recordings', 'display_video_info'])

if 'validate_number' in globals():
    __all__.extend(['validate_number', 'validate_positive_number'])
