"""
Core download functionality for different video platforms.
"""
import subprocess
import os
from utils.logger import get_logger

logger = get_logger(__name__)

def download_twitter_broadcast(url, flight_identifier, company=None, vehicle=None):
    """
    Downloads a Twitter/X broadcast video using yt-dlp.

    Args:
        url (str): The URL of the Twitter/X broadcast.
        flight_identifier (str): The flight identifier to use in the filename.
        company (str, optional): The launch provider name for directory structure.
        vehicle (str, optional): The rocket name for directory structure.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Determine output path based on company and vehicle
        if company and vehicle:
            output_path = f"flight_recordings/{company}/{vehicle}"
        else:
            output_path = "flight_recordings"
        
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        # Define output template with flight identifier
        output_template = f"{output_path}/{flight_identifier}.%(ext)s"
        
        logger.info(f"Downloading Twitter broadcast from {url}")
        logger.info(f"Output file will be saved as: {output_template}")
        
        # Run yt-dlp to download the video only at 1080p resolution
        subprocess.run([
            "yt-dlp",
            "-f", "bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]/best[height<=1080]",
            "--no-audio",  # Explicitly disable audio download
            "-o", output_template,
            url
        ], check=True)
        
        logger.info("Download completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Download error: {e}")
        print(f"An error occurred during download: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"An unexpected error occurred: {e}")
        return False

def download_youtube_video(url, flight_identifier, company=None, vehicle=None):
    """
    Downloads a YouTube video using yt-dlp.

    Args:
        url (str): The URL of the YouTube video.
        flight_identifier (str): The flight identifier to use in the filename.
        company (str, optional): The launch provider name for directory structure.
        vehicle (str, optional): The rocket name for directory structure.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Determine output path based on company and vehicle
        if company and vehicle:
            output_path = f"flight_recordings/{company}/{vehicle}"
        else:
            output_path = "flight_recordings"
        
        # Ensure output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        # Define output template with flight identifier
        output_template = f"{output_path}/{flight_identifier}.%(ext)s"
        
        logger.info(f"Downloading YouTube video from {url}")
        logger.info(f"Output file will be saved as: {output_template}")
        
        # Run yt-dlp to download video only at 1080p resolution, without audio
        subprocess.run([
            "yt-dlp",
            "-f", "bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]/best[height<=1080]",
            "--no-audio",  # Explicitly disable audio download
            "-o", output_template,
            url
        ], check=True)
        
        logger.info("Download completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"YouTube download error: {e}")
        print(f"An error occurred during YouTube download: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"An unexpected error occurred: {e}")
        return False
