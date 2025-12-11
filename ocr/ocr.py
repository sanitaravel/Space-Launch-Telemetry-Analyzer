import re
import easyocr
import numpy as np
import torch
import os
import gc
import threading
from typing import Dict, Tuple, Optional
from utils import display_image
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Process-global EasyOCR reader to avoid duplicated model loads on GPU.
# One reader per process reduces GPU memory usage compared to per-thread readers.
_reader = None
_reader_lock = threading.Lock()
_device_initialized = False
_device_id: Optional[int] = None


def _init_reader(gpu: bool) -> easyocr.Reader:
    """Initialize and return the process-global EasyOCR reader.

    If GPU initialization fails, this will fall back to a CPU reader and return it.
    """
    global _reader, _device_initialized, _device_id
    pid = os.getpid()

    with _reader_lock:
        if _reader is not None:
            return _reader

        logger.info(f"Process {pid}: Initializing EasyOCR reader (gpu={gpu})")

        gpu_available = gpu and torch.cuda.is_available()
        if gpu_available:
            try:
                device_env = os.environ.get("CUDA_DEVICE")
                device_id = int(device_env) if device_env is not None else 0
                logger.debug(f"Process {pid}: Attempting to set CUDA device to {device_id}")
                torch.cuda.set_device(device_id)
                _device_id = device_id
                _device_initialized = True
                try:
                    device_name = torch.cuda.get_device_name(device_id)
                    total_memory = torch.cuda.get_device_properties(device_id).total_memory / (1024**3)
                    logger.debug(f"Process {pid}: Using GPU: {device_name} with {total_memory:.2f} GB total memory")
                    logger.debug(f"Process {pid}: CUDA version: {torch.version.cuda}")
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Process {pid}: Error setting CUDA device: {e}")
                gpu_available = False

        try:
            logger.debug(f"Process {pid}: Starting EasyOCR initialization with GPU={gpu_available}")
            _reader = easyocr.Reader(['en'], gpu=gpu_available, verbose=False)
            logger.info(f"Process {pid}: EasyOCR initialized {'with GPU' if gpu_available else 'on CPU'}")
        except Exception as e:
            logger.error(f"Process {pid}: Failed to initialize EasyOCR with GPU, falling back to CPU: {e}")
            try:
                logger.debug(f"Process {pid}: Attempting fallback to CPU mode")
                _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                logger.info(f"Process {pid}: EasyOCR initialized on CPU (fallback)")
            except Exception as e2:
                logger.critical(f"Process {pid}: Critical error initializing EasyOCR: {e2}")
                raise

    return _reader


def get_reader() -> easyocr.Reader:
    """Return the process-global EasyOCR reader, initializing it on first use."""
    global _reader
    if _reader is None:
        return _init_reader(gpu=True)
    return _reader

def extract_values_from_roi(roi: np.ndarray, mode: str = "data", display_transformed: bool = False, debug: bool = False, regex: Optional[str] = None) -> Dict:
    """
    Extract values from a region of interest (ROI) in an image.

    Args:
        roi (numpy.ndarray): The region of interest in the image.
        mode (str): The mode of extraction ("data" or "time").
        display_transformed (bool): Whether to display the transformed ROI.
        debug (bool): Whether to enable debug prints.

    Returns:
        dict: A dictionary containing the extracted values.
    """
    try:
        # Get the EasyOCR reader safely
        ocr_reader = get_reader()

        # Guard against empty or invalid ROIs
        if roi is None or roi.size == 0 or roi.shape[0] == 0 or roi.shape[1] == 0:
            if debug:
                logger.warning("Empty or invalid ROI provided to OCR")
            return {}
            
        if debug:
            logger.debug(f"Processing ROI of shape {roi.shape} in mode: {mode}")
            # Log memory usage if debug is enabled
            if torch.cuda.is_available():
                pid = os.getpid()
                device_id = torch.cuda.current_device()
                allocated = torch.cuda.memory_allocated(device_id) / (1024**2)
                reserved = torch.cuda.memory_reserved(device_id) / (1024**2)
                logger.debug(f"Process {pid}: GPU memory - Allocated: {allocated:.2f} MB, Reserved: {reserved:.2f} MB")
        
        # Use EasyOCR to extract text with appropriate parameters for each mode
        allowlist = '0123456789T+-:' if mode == "time" else '0123456789.,'
                
        # Process the image with error handling
        try:
            if debug:
                logger.debug(f"Starting OCR with allowlist: {allowlist}")
                
            results = ocr_reader.readtext(roi, detail=0, allowlist=allowlist)
            text = ''.join(results) if results else ""
            
            if debug:
                logger.debug(f"OCR results: {results}")
                
        except RuntimeError as e:
            # Handle CUDA out-of-memory errors
            if "CUDA out of memory" in str(e):
                logger.warning("CUDA out of memory error in OCR. Falling back to CPU.")
                logger.debug(f"Memory error details: {str(e)}")

                # Clean up existing GPU-backed reader and force a CPU-only reader.
                global _reader
                with _reader_lock:
                    try:
                        old_reader = _reader
                        _reader = None
                        if old_reader is not None:
                            del old_reader
                    except Exception:
                        pass

                # Force garbage collection and clear CUDA cache
                gc.collect()
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass

                logger.debug("CUDA memory cleared, reinitializing reader on CPU")
                ocr_reader = _init_reader(gpu=False)
                results = ocr_reader.readtext(roi, detail=0, allowlist=allowlist)
                text = ''.join(results) if results else ""
                logger.debug(f"CPU fallback OCR results: {results}")
            else:
                logger.error(f"RuntimeError in OCR: {str(e)}")
                raise
        
        if debug:
            logger.debug(f"Raw OCR result for {mode}: {text}")
            
    except Exception as e:
        logger.error(f"OCR error: {str(e)}")
        return {}
    
    # Use the OCR result directly since we're already using an allowlist
    if debug:
        logger.debug(f"OCR result for {mode}: {text}")
    
    # Process according to mode
    if mode == "speed":
        speed = extract_single_value(text)
        if debug:
            logger.debug(f"Extracted speed value: {speed}")
        return {"value": speed}
    elif mode == "altitude":
        altitude = extract_single_value(text)
        if debug:
            logger.debug(f"Extracted altitude value: {altitude}")
        return {"value": altitude}
    elif mode == "time":
        time = extract_time(text, regex or r'[+-]\d{2}:\d{2}:\d{2}')
        if debug:
            if time:
                logger.debug(f"Extracted time: {time['sign']} {time.get('hours', 0):02}:{time.get('minutes', 0):02}:{time.get('seconds', 0):02}")
            else:
                logger.debug("Failed to extract time")
        return time if time else {}
    else:
        if debug:
            logger.debug(f"Unknown mode: {mode}")
        return {}

def extract_single_value(text: str) -> Optional[int]:
    """
    Extract a single numeric value from the cleaned text.
    
    Args:
        text (str): The cleaned text.
        
    Returns:
        Optional[int]: The extracted numeric value, or None if no value was found.
    """
    # Remove commas as they are used as thousands separators, not decimal points
    text = text.replace(',', '')
    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    if numbers:
        return float(numbers[0])
    logger.debug(f"No numeric value found in text: '{text}'")
    return None

def extract_time(text: str, regex: str = r'[+-]\d{2}:\d{2}:\d{2}') -> Optional[Dict[str, int]]:
    """
    Extract time from the cleaned text.

    Args:
        text (str): The cleaned text.

    Returns:
        dict: A dictionary containing the extracted time.
    """
    match = re.search(regex, text)
    if match:
        time_str = match.group(0)
        sign = time_str[0]
        hours, minutes, seconds = map(int, time_str[1:].split(':'))
        return {"sign": sign, "hours": hours, "minutes": minutes, "seconds": seconds}
    logger.debug(f"No time format found in text: '{text}'")
    return None