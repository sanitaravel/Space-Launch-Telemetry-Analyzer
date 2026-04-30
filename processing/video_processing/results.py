"""
Functions for handling video processing results.
"""
import os
import json
from typing import List, Dict, Optional, Union
from utils.logger import get_logger

logger = get_logger(__name__)


def calculate_real_times(results: List[Dict], zero_time_frame: Optional[int], fps: float) -> List[Dict]:
    """
    Calculate real time for each frame.

    Args:
        results (List[Dict]): The processing results.
        zero_time_frame (Optional[int]): The frame number with time 0:0:0.
        fps (float): The frames per second of the video.

    Returns:
        List[Dict]: The updated results with real time calculations.
    """
    if zero_time_frame is None:
        return results
        
    for frame_result in results:
        frame_number = frame_result["frame_number"]
        if "error" in frame_result:
            continue
            
        if "time" in frame_result:
            seconds_from_zero = (frame_number - zero_time_frame) / fps
            frame_result["real_time_seconds"] = seconds_from_zero
            
            # Calculate time components
            hours = int(seconds_from_zero // 3600)
            minutes = int((seconds_from_zero % 3600) // 60)
            seconds = int(seconds_from_zero % 60)
            milliseconds = int((seconds_from_zero % 1) * 1000)
            
            frame_result["real_time"] = {
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
                "milliseconds": milliseconds
            }
    
    return results


def save_results(results: List[Dict], provider: str, vehicle_type: str, launch_identifier: Union[int, str]) -> None:
    """
    Save the processing results to a file using a mission/launch identifier.

    Args:
        results (List[Dict]): The processing results.
        provider (str): The launch provider (e.g., 'spacex').
        vehicle_type (str): The vehicle type (e.g., 'starship').
        launch_identifier (int|str): The legacy numeric launch number or a mission identifier string.
            - If an int (or a numeric string) the folder will be `launch_<n>` for backward compatibility.
            - Otherwise the identifier string is used as the folder name (normalized).
    """
    # Determine destination folder while preserving legacy numeric behavior
    if isinstance(launch_identifier, int):
        folder_name = os.path.join("results", provider, vehicle_type, f"launch_{launch_identifier}")
    else:
        ident = str(launch_identifier)
        # If ident is purely numeric, treat it as legacy launch number
        if ident.isdigit():
            folder_name = os.path.join("results", provider, vehicle_type, f"launch_{ident}")
        else:
            # Normalize spaces -> underscores to create safe folder names
            safe_ident = ident.replace(' ', '_')
            folder_name = os.path.join("results", provider, vehicle_type, safe_ident)
    
    os.makedirs(folder_name, exist_ok=True)

    result_path = os.path.join(folder_name, "results.json")
    try:
        with open(result_path, "w") as f:
            json.dump(results, f, indent=4)
        logger.info(f"Results saved to {result_path}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

        # Try to save to a backup location using a safe identifier
        try:
            safe_ident = str(launch_identifier).replace(' ', '_')
            backup_path = os.path.join("results", f"backup_results_{provider}_{vehicle_type}_{safe_ident}.json")
            with open(backup_path, "w") as f:
                json.dump(results, f, indent=4)
            logger.info(f"Results saved to backup location: {backup_path}")
        except Exception as backup_error:
            logger.error(f"Failed to save results to backup location: {str(backup_error)}")
