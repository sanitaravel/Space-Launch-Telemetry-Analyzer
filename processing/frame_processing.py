import random
import os
import cv2
from typing import Optional
from ocr import extract_data
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

def process_image(image_path: str, display_rois: bool, debug: bool) -> None:
    """
    Process a single image and extract data.

    Args:
        image_path (str): The path to the image file.
        display_rois (bool): Whether to display the ROIs.
        debug (bool): Whether to enable debug prints.
    """
    logger.debug(f"Processing image from {image_path}")
    
    try:
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Failed to load image from {image_path}")
            return
            
        logger.debug(f"Image loaded successfully, shape: {image.shape}")
        
        extracted = extract_data(
            image, display_rois=display_rois, debug=debug)
        vehicles_data = extracted.get("vehicles", {})
        time_data = extracted.get("time", {})
        # For backward compatibility
        superheavy_data = vehicles_data.get("superheavy", {})
        starship_data = vehicles_data.get("starship", {})
            
        if debug:
            logger.debug(
                f"Superheavy - Speed: {superheavy_data.get('speed')}, Altitude: {superheavy_data.get('altitude')}"
            )
            logger.debug(
                f"Starship - Speed: {starship_data.get('speed')}, Altitude: {starship_data.get('altitude')}"
            )

            if time_data:
                time_str = f"{time_data['sign']} {time_data.get('hours', 0):02}:{time_data.get('minutes', 0):02}:{time_data.get('seconds', 0):02}"
                logger.debug(f"Time: {time_str}")
            else:
                logger.debug("Time: Not found")
                
            # Also output engine data if available
            if 'engines' in superheavy_data:
                sh_active = sum(sum(1 for e in engines if e) for engines in superheavy_data['engines'].values())
                sh_total = sum(len(engines) for engines in superheavy_data['engines'].values())
                logger.debug(f"Superheavy engines: {sh_active}/{sh_total} active")
                
            if 'engines' in starship_data:
                ss_active = sum(sum(1 for e in engines if e) for engines in starship_data['engines'].values())
                ss_total = sum(len(engines) for engines in starship_data['engines'].values())
                logger.debug(f"Starship engines: {ss_active}/{ss_total} active")
                
    except Exception as e:
        logger.error(f"Error processing image {image_path}: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())


def process_video_frame(video_path: str, display_rois: bool, debug: bool, start_frame: Optional[int], end_frame: Optional[int]) -> None:
    """
    Extract data from a random frame in a video within a specified timeframe.

    Args:
        video_path (str): The path to the video file.
        display_rois (bool): Whether to display the ROIs.
        debug (bool): Whether to enable debug prints.
        start_frame (int, optional): The start frame index for the timeframe.
            end_frame (int, optional): The end frame index for the timeframe. Use -1 to indicate until end.
    """
    logger.info(f"Processing random frame from {video_path}")
    logger.debug(f"Parameters: display_rois={display_rois}, debug={debug}, start_frame={start_frame}, end_frame={end_frame}")
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video file: {video_path}")
            return
            
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        logger.debug(f"Video properties: {frame_count} frames, {fps} fps")
        logger.debug(f"Video resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

        # Interpret provided frame bounds; if None, set defaults
        if start_frame is None:
            start_frame = 0

        if end_frame is None or end_frame == -1:
            end_frame = frame_count - 1

        if start_frame >= end_frame:
            logger.error(f"Start frame must be less than end frame (start={start_frame}, end={end_frame})")
            cap.release()
            return

        random_frame_number = random.randint(start_frame, end_frame)
        logger.info(f"Selected random frame number: {random_frame_number} (time: ~{random_frame_number/fps:.2f}s)")
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            logger.error(f"Failed to extract frame {random_frame_number} from video")
            return

        tmp_dir = os.path.join('.', '.tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        image_path = os.path.join(tmp_dir, "random_frame.jpg")
        
        logger.debug(f"Saving extracted frame to {image_path}")
        
        cv2.imwrite(image_path, frame)
        print(f"Extracted frame number: {random_frame_number}")
        
        logger.debug("Processing extracted frame")
        process_image(image_path, display_rois, debug)
        
    except Exception as e:
        logger.error(f"Error processing video frame: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())


def process_frame(video_path: str, frame_number: int, display_rois: bool, debug: bool, output_filename: str) -> None:
    """
    Extract data from a specified frame in a video.

    Args:
        video_path (str): The path to the video file.
        frame_number (int): The frame number to extract.
        display_rois (bool): Whether to display the ROIs.
        debug (bool): Whether to enable debug prints.
        output_filename (str): The filename to save the extracted frame as.
    """
    logger.info(f"Processing frame {frame_number} from {video_path}")
    logger.debug(f"Parameters: display_rois={display_rois}, debug={debug}, output_filename={output_filename}")
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video file: {video_path}")
            return
            
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_number >= frame_count:
            logger.error(f"Frame number {frame_number} exceeds total frames in video ({frame_count})")
            cap.release()
            return
            
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            logger.debug(f"Saving frame to {output_filename}")
            cv2.imwrite(output_filename, frame)
            image_path = output_filename
            print(f"Extracted frame number: {frame_number}")
            
            logger.debug("Processing extracted frame")
            process_image(image_path, display_rois, debug)
        else:
            logger.error(f"Failed to extract frame {frame_number} from video")
    except Exception as e:
        logger.error(f"Error in process_frame: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
