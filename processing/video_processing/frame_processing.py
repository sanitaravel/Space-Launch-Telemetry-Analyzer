"""
Functions for processing individual video frames.
"""
import os
import cv2
import random
import numpy as np
from typing import Dict, Optional
from utils.logger import get_logger
from ocr import extract_data
from ocr.roi_manager import ROIManager

logger = get_logger(__name__)


def process_frame(frame_number: int, frame: np.ndarray, display_rois: bool, debug: bool, zero_time_met: bool) -> Dict:
    """
    Process a single frame and extract data.

    Args:
        frame_number (int): The frame number.
        frame (numpy.ndarray): The frame to process.
        display_rois (bool): Whether to display the ROIs.
        debug (bool): Whether to enable debug prints.
        zero_time_met (bool): Whether a frame with time 0:0:0 has been met.

    Returns:
        dict: A dictionary containing the extracted data for the frame.
    """
    try:
        extracted = extract_data(
            frame, display_rois=display_rois, debug=debug, zero_time_met=zero_time_met, frame_idx=frame_number)
        vehicles_data = extracted.get("vehicles", {})
        time_data = extracted.get("time", {})
        frame_result = {
            "frame_number": frame_number,
            "vehicles": vehicles_data,
            "time": time_data
        }
        return frame_result
    except Exception as e:
        logger.error(f"Error processing frame {frame_number}: {str(e)}")
        # Return a minimal result to avoid breaking the pipeline
        return {
            "frame_number": frame_number,
            "superheavy": {},
            "starship": {},
            "time": None,
            "error": str(e)
        }


def process_single_frame(frame_idx, frame, display_rois=False, debug=False, show_progress=False):
    """
    Process a single frame in the alternative processing path.
    
    Args:
        frame_idx (int): Index of the frame
        frame (numpy.ndarray): Frame to process
        display_rois (bool): Whether to display ROIs
        debug (bool): Whether to enable debug mode
        show_progress (bool): Whether to show individual frame progress

    Returns:
        dict: Results for the frame
    """
    try:
        extracted = extract_data(
            frame, display_rois=display_rois, debug=debug, frame_idx=frame_idx)
        vehicles_data = extracted.get("vehicles", {})
        time_data = extracted.get("time", {})
        frame_result = {
            "frame_number": frame_idx,
            "vehicles": vehicles_data,
            "time": time_data
        }
        
        # Only show progress if explicitly requested (we now focus on batch progress)
        if show_progress:
            logger.debug(f"Processed frame {frame_idx}")
            
        return frame_result
    except Exception as e:
        logger.error(f"Error processing frame {frame_idx}: {str(e)}")
        # Return a minimal result to avoid breaking the pipeline
        return {
            "frame_number": frame_idx,
            "superheavy": {},
            "starship": {},
            "time": None,
            "error": str(e)
        }


def process_video_frame(video_path: str, display_rois: bool = False, debug: bool = False, 
                      start_time: int = 0, end_time: int = -1) -> Dict:
    """
    Process a random frame from a video file within a specified time range.

    Args:
        video_path (str): Path to the video file.
        display_rois (bool): Whether to display the ROIs.
        debug (bool): Whether to enable debug prints.
        start_time (int): Start time in seconds.
        end_time (int): End time in seconds (-1 for all).

    Returns:
        dict: The results of processing the frame.
    """
    logger.debug(f"Processing random frame from {video_path} (start_time={start_time}, end_time={end_time})")
    
    try:
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video file at {video_path}")
            return {"error": "Failed to open video file"}
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate frame range based on start and end times
        start_frame = start_time
        end_frame = int(frame_count - 1) if end_time < 0 else int(min(frame_count - 1, end_time))
        
        if start_frame >= end_frame:
            logger.error(f"Invalid time range: start_frame ({start_frame}) >= end_frame ({end_frame})")
            cap.release()
            return {"error": "Invalid time range"}
        
        # Choose a random frame within the range
        # If display_rois is True, try to find a frame with active ROIs
        random_frame = random.randint(start_frame, end_frame)
        
        if display_rois:
            from ocr.roi_manager import get_default_manager
            manager = get_default_manager()
            max_attempts = 10
            attempt = 0
            
            while attempt < max_attempts:
                active_rois = manager.get_active_rois(random_frame)
                if active_rois:
                    break
                # Try another random frame
                random_frame = random.randint(start_frame, end_frame)
                attempt += 1
            
            if attempt == max_attempts:
                logger.warning(f"Could not find a frame with active ROIs after {max_attempts} attempts. Using frame {random_frame} anyway.")
        
        logger.info(f"Selected random frame {random_frame} (out of {frame_count})")
        
        # Set the frame position and read the frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            logger.error(f"Failed to read frame {random_frame}")
            return {"error": f"Failed to read frame {random_frame}"}
            
        # Process the frame
        if debug:
            logger.debug(f"Processing frame {random_frame} with display_rois={display_rois}")
            
        # Initialize zero_time_met to False for a single random frame
        result = process_frame(random_frame, frame, display_rois, debug, False)
        
        if debug:
            logger.debug(f"Frame processing complete: {result}")
        
        return result
        
    except Exception as e:
        logger.exception(f"Error in process_video_frame: {str(e)}")
        return {"error": str(e)}
