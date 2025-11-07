"""
Functions for handling video processing results.
"""
import os
import json
from typing import List, Dict, Optional
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


def save_results(results: List[Dict], provider: str, vehicle_type: str, launch_number: int) -> None:
    """
    Save the processing results to a file.

    Args:
        results (List[Dict]): The processing results.
        provider (str): The launch provider (e.g., 'spacex').
        vehicle_type (str): The vehicle type (e.g., 'starship').
        launch_number (int): The launch number for saving results.
    """
    folder_name = os.path.join("results", provider, vehicle_type, f"launch_{launch_number}")
    os.makedirs(folder_name, exist_ok=True)

    result_path = os.path.join(folder_name, "results.json")
    try:
        with open(result_path, "w") as f:
            json.dump(results, f, indent=4)
        logger.info(f"Results saved to {result_path}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")
        
        # Try to save to a backup location
        backup_path = os.path.join("results", f"backup_results_{provider}_{vehicle_type}_{launch_number}.json")
        try:
            with open(backup_path, "w") as f:
                json.dump(results, f, indent=4)
            logger.info(f"Results saved to backup location: {backup_path}")
        except Exception as backup_error:
            logger.error(f"Failed to save results to backup location: {str(backup_error)}")
