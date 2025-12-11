"""
Utility functions for download operations.
"""
import json
import os
import requests
from utils.logger import get_logger

logger = get_logger(__name__)

def get_launch_data():
    """
    Retrieve the flight data from local config files.
    
    Returns:
        dict: A dictionary containing flight information, or None if there was an error.
    """
    try:
        logger.info("Fetching flight data from local config files")
        
        flight_data = {}
        configs_path = "configs"
        
        if not os.path.exists(configs_path):
            logger.error(f"Configs directory not found: {configs_path}")
            return None
        
        # Walk through the configs directory
        for root, dirs, files in os.walk(configs_path):
            for file in files:
                if file.endswith("_rois.json"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            config_data = json.load(f)
                        
                        # Extract video_source
                        video_source = config_data.get("video_source")
                        if not video_source:
                            logger.warning(f"No video_source found in {file_path}")
                            continue
                        
                        # Parse the path to get company, vehicle, flight
                        # Path format: configs/company/vehicle/flight_rois.json
                        rel_path = os.path.relpath(file_path, configs_path)
                        path_parts = rel_path.split(os.sep)
                        
                        if len(path_parts) != 3:
                            logger.warning(f"Unexpected path structure for {file_path}")
                            continue
                        
                        company, vehicle, flight_file = path_parts
                        # flight_file is like "flight_10_rois.json"
                        flight_key = flight_file.replace("_rois.json", "")
                        
                        # Initialize nested structure
                        if company not in flight_data:
                            flight_data[company] = {}
                        if vehicle not in flight_data[company]:
                            flight_data[company][vehicle] = {}
                        
                        # Add the flight data
                        flight_data[company][vehicle][flight_key] = {
                            "type": video_source.get("type"),
                            "url": video_source.get("url")
                        }
                        
                        logger.debug(f"Added flight {company}/{vehicle}/{flight_key} from {file_path}")
                        
                    except (json.JSONDecodeError, KeyError, IOError) as e:
                        logger.error(f"Error reading config file {file_path}: {e}")
                        continue
        
        logger.info(f"Successfully loaded data for flights from {len(flight_data)} companies")
        return flight_data
        
    except Exception as e:
        logger.error(f"Unexpected error fetching flight data: {e}")
        print(f"Error fetching flight data: {e}")
        return None

def get_downloaded_launches(output_path="flight_recordings"):
    """
    Get a list of already downloaded flight numbers.
    
    Args:
        output_path (str): Path to check for downloaded files
        
    Returns:
        list: List of downloaded flight numbers as integers
    """
    downloaded = []
    
    if not os.path.exists(output_path):
        return downloaded
    
    # Check for files matching the pattern "flight_X.*"
    for file in os.listdir(output_path):
        if file.startswith("flight_"):
            try:
                # Extract the flight number from the filename
                flight_num = int(file.split("_")[1].split(".")[0])
                downloaded.append(flight_num)
            except (IndexError, ValueError):
                continue
    
    logger.debug(f"Found already downloaded flights: {downloaded}")
    return downloaded
