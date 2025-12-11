"""
Main processing functions for video analysis.
"""
import cv2
import multiprocessing
from typing import List, Dict, Optional
from utils.logger import get_logger
from .validation import validate_video
from .batch_processing import create_batches, process_video_frames, summarize_batch
from .frame_processing import process_single_frame
from .results import calculate_real_times, save_results

logger = get_logger(__name__)


def iterate_through_frames(video_path: str, provider: str, vehicle_type: str, launch_number: int, display_rois: bool = False, debug: bool = False, 
                          max_frames: Optional[int] = None, batch_size: int = 10, sample_rate: int = 1,
                          start_frame: Optional[int] = None, end_frame: Optional[int] = None) -> None:
    """
    Iterate through all frames in a video and extract data.

    Args:
        video_path (str): The path to the video file.
        provider (str): The launch provider (e.g., 'spacex').
        vehicle_type (str): The vehicle type (e.g., 'starship').
        launch_number (int): The launch number for saving results.
        display_rois (bool): Whether to display the ROIs.
        debug (bool): Whether to enable debug prints.
        max_frames (int, optional): The maximum number of frames to process. Defaults to None.
        batch_size (int): The number of frames to process in each batch.
        sample_rate (int): The sampling rate (process every Nth frame). Defaults to 1.
        start_frame (int, optional): Start frame number (overrides start_time if provided). Defaults to None.
        end_frame (int, optional): End frame number (overrides end_time if provided). Defaults to None.
    """
    logger.info(f"Starting video processing for {provider}/{vehicle_type} launch {launch_number}")
    logger.info(f"Video path: {video_path}, batch size: {batch_size}, sample rate: 1/{sample_rate}")
    
    if debug:
        logger.debug("Debug mode is enabled for video processing")
    
    # Ensure spawn method is used
    if multiprocessing.get_start_method() != 'spawn':
        try:
            multiprocessing.set_start_method('spawn', force=True)
            logger.debug("Set multiprocessing start method to 'spawn'")
        except RuntimeError:
            logger.warning("Could not set multiprocessing start method to 'spawn'")
            logger.warning("Processing will continue with current method, but may encounter CUDA issues")

    # Validate video file
    if not validate_video(video_path):
        logger.error("Video validation failed, aborting processing")
        return

    # Get video properties
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Determine start and end frames (time-based selection was removed; callers should provide frames)
    if start_frame is not None:
        start_pos = max(0, min(start_frame, total_frame_count - 1))
    else:
        start_pos = 0

    if end_frame is not None:
        end_pos = max(start_pos, min(end_frame, total_frame_count))
    else:
        end_pos = total_frame_count
    
    # Apply max_frames limit if specified
    if max_frames is not None:
        end_pos = min(end_pos, start_pos + max_frames)
    
    frame_count = end_pos - start_pos
    cap.release()
    
    logger.info(f"Processing from frame {start_pos} to {end_pos} ({frame_count} frames) at {fps} fps")
    
    if debug:
        logger.debug(f"Video processing borders: start_frame={start_pos}, end_frame={end_pos}")
        
        # Get additional video properties for debugging
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.debug(f"Video resolution: {width}x{height}")
            video_codec = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec_str = "".join([chr((video_codec >> 8 * i) & 0xFF) for i in range(4)])
            logger.debug(f"Video codec: {codec_str}")
            cap.release()
    
    # Create batches with sampling, ensuring we respect the start and end positions
    frame_range = range(start_pos, end_pos, sample_rate)
    batches = [list(frame_range[i:i + batch_size]) for i in range(0, len(frame_range), batch_size)]
    logger.info(f"Created {len(batches)} batches of max size {batch_size} with sampling rate 1/{sample_rate}")
    
    if debug and len(batches) > 0:
        logger.debug(f"First batch frame numbers: {batches[0]}")
        logger.debug(f"Last batch frame numbers: {batches[-1]}")

    # Process video frames
    logger.debug("Starting parallel video frame processing")
    results, zero_time_frame = process_video_frames(batches, video_path, display_rois, debug)
    logger.info(f"Processing complete. Analyzed {len(results)} frames successfully.")
    
    if debug:
        successful_frames = sum(1 for r in results if "error" not in r)
        failed_frames = sum(1 for r in results if "error" in r)
        logger.debug(f"Frame processing statistics: {successful_frames} successful, {failed_frames} failed")
    
    if zero_time_frame:
        logger.info(f"Zero time frame identified at frame {zero_time_frame}")
    else:
        logger.warning("No zero time frame was identified. Time calculations may be inaccurate.")
    
    # Calculate real time for each frame
    logger.debug("Starting real-time calculations")
    results = calculate_real_times(results, zero_time_frame, fps)
    logger.info(f"Time calculations complete.")

    # Save results
    logger.debug(f"Saving results to {provider}/{vehicle_type}/launch_{launch_number}")
    save_results(results, provider, vehicle_type, launch_number)
    logger.info(f"Video processing for {provider}/{vehicle_type} launch {launch_number} completed successfully")


def process_frames(video_path, batch_size=30, start_time=None, end_time=None, start_frame=None, end_frame=None):
    """
    Process frames from a video file.
    
    Args:
        video_path (str): Path to the video file
        batch_size (int): Number of frames to process in each batch
        start_time (float, optional): Start time in seconds
        end_time (float, optional): End time in seconds
        start_frame (int, optional): Start frame number (overrides start_time if provided)
        end_frame (int, optional): End frame number (overrides end_time if provided)
        
    Returns:
        dict: Results of the processing
    """
    if not validate_video(video_path):
        return None
        
    cap = cv2.VideoCapture(video_path)
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Determine start and end frames
    if start_frame is not None:
        start_pos = max(0, min(start_frame, frame_count-1))
    elif start_time is not None:
        start_pos = max(0, min(int(start_time * fps), frame_count-1))
    else:
        start_pos = 0
        
    if end_frame is not None:
        end_pos = max(start_pos, min(end_frame, frame_count))
    elif end_time is not None:
        end_pos = max(start_pos, min(int(end_time * fps), frame_count))
    else:
        end_pos = frame_count
    
    # Set the starting position
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_pos)
    
    # Calculate the number of frames to process
    frames_to_process = end_pos - start_pos
    num_batches = (frames_to_process + batch_size - 1) // batch_size  # Ceiling division
    
    logger.info(f"Processing video from frame {start_pos} to {end_pos} ({frames_to_process} frames)")
    logger.info(f"Using batch size: {batch_size}, total batches: {num_batches}")
    
    results = []
    current_frame = start_pos
    
    for batch_idx in range(num_batches):
        batch_results = []
        batch_start_frame = current_frame
        batch_end_frame = min(batch_start_frame + batch_size, end_pos)
        batch_size_actual = batch_end_frame - batch_start_frame
        
        logger.info(f"Processing batch {batch_idx+1}/{num_batches} (frames {batch_start_frame}-{batch_end_frame-1})")
        
        # Process frames in this batch
        for i in range(batch_size_actual):
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Failed to read frame at position {current_frame}")
                break
                
            # Process the frame
            frame_result = process_single_frame(current_frame, frame, False, False, False)
            if frame_result:
                batch_results.append(frame_result)
            
            current_frame += 1
        
        # Batch progression
        progress = (batch_idx + 1) / num_batches * 100
        logger.info(f"Batch progress: {progress:.1f}% ({batch_idx+1}/{num_batches})")
        
        # Add batch results to overall results
        if batch_results:
            batch_summary = summarize_batch(batch_results, batch_start_frame, batch_end_frame)
            results.append(batch_summary)
        
        # Exit if we've reached the end position
        if current_frame >= end_pos:
            break
    
    cap.release()
    return results
