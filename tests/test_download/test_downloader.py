"""
Tests for download functionality in download/downloader.py.
"""
import pytest
from unittest.mock import patch, MagicMock
import os
import subprocess

from download.downloader import download_twitter_broadcast, download_youtube_video

class TestDownloader:
    """Tests for the downloader functions."""
    
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_download_twitter_broadcast_success(self, mock_run, mock_makedirs):
        """Test successful Twitter broadcast download."""
        # Setup mocks
        mock_run.return_value = MagicMock(returncode=0)
        
        # Call function
        result = download_twitter_broadcast("https://twitter.com/video", "flight_5")
        
        # Verify results
        assert result is True
        mock_makedirs.assert_called_once_with("flight_recordings", exist_ok=True)
        mock_run.assert_called_once()
        
        # Verify the subprocess.run command with video-only parameters and 1080p resolution
        args, kwargs = mock_run.call_args
        assert args[0][0] == "yt-dlp"
        assert args[0][1] == "-f"
        assert args[0][2] == "bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]/best[height<=1080]"
        assert args[0][3] == "--no-audio"
        assert args[0][4] == "-o"
        assert args[0][5] == "flight_recordings/flight_5.%(ext)s"
        assert args[0][6] == "https://twitter.com/video"
        assert kwargs.get('check') is True
    
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_download_twitter_broadcast_custom_path(self, mock_run, mock_makedirs):
        """Test Twitter broadcast download with custom output path."""
        # Setup mocks
        mock_run.return_value = MagicMock(returncode=0)
        
        # Call function
        result = download_twitter_broadcast("https://twitter.com/video", "flight_10", "custom", "path")
        
        # Verify results
        assert result is True
        mock_makedirs.assert_called_once_with("flight_recordings/custom/path", exist_ok=True)
        mock_run.assert_called_once()
        
        # Verify the subprocess.run command uses the custom path with video-only parameters
        args, kwargs = mock_run.call_args
        assert args[0][5] == "flight_recordings/custom/path/flight_10.%(ext)s"
    
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_download_twitter_broadcast_subprocess_error(self, mock_run, mock_makedirs):
        """Test handling of subprocess error during Twitter download."""
        # Setup mock to raise CalledProcessError
        mock_run.side_effect = subprocess.CalledProcessError(1, "yt-dlp")
        
        # Call function with mocked print
        with patch('builtins.print') as mock_print:
            result = download_twitter_broadcast("https://twitter.com/video", "flight_5")
            
            # Verify results
            assert result is False
            mock_makedirs.assert_called_once()
            mock_print.assert_called_with(
                "An error occurred during download: Command 'yt-dlp' returned non-zero exit status 1."
            )
    
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_download_twitter_broadcast_unexpected_error(self, mock_run, mock_makedirs):
        """Test handling of unexpected errors during Twitter download."""
        # Setup mock to raise an unexpected exception
        mock_makedirs.side_effect = Exception("Unexpected error")
        
        # Call function with mocked print
        with patch('builtins.print') as mock_print:
            result = download_twitter_broadcast("https://twitter.com/video", "flight_5")
            
            # Verify results
            assert result is False
            mock_makedirs.assert_called_once()
            mock_print.assert_called_with("An unexpected error occurred: Unexpected error")
    
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_download_youtube_video_success(self, mock_run, mock_makedirs):
        """Test successful YouTube video download."""
        # Setup mocks
        mock_run.return_value = MagicMock(returncode=0)
        
        # Call function
        result = download_youtube_video("https://youtube.com/watch", "flight_5")
        
        # Verify results
        assert result is True
        mock_makedirs.assert_called_once_with("flight_recordings", exist_ok=True)
        mock_run.assert_called_once()
        
        # Verify the subprocess.run command for YouTube with video-only parameters and 1080p resolution
        args, kwargs = mock_run.call_args
        assert args[0][0] == "yt-dlp"
        assert args[0][1] == "-f"
        assert args[0][2] == "bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]/best[height<=1080]"
        assert args[0][3] == "--no-audio"
        assert args[0][4] == "-o"
        assert args[0][5] == "flight_recordings/flight_5.%(ext)s"
        assert args[0][6] == "https://youtube.com/watch"
        assert kwargs.get('check') is True
    
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_download_youtube_video_custom_path(self, mock_run, mock_makedirs):
        """Test YouTube video download with custom output path."""
        # Setup mocks
        mock_run.return_value = MagicMock(returncode=0)
        
        # Call function
        result = download_youtube_video("https://youtube.com/watch", "flight_10", "custom", "path")
        
        # Verify results
        assert result is True
        mock_makedirs.assert_called_once_with("flight_recordings/custom/path", exist_ok=True)
        mock_run.assert_called_once()
        
        # Verify the subprocess.run command uses the custom path with video-only parameters
        args, kwargs = mock_run.call_args
        assert args[0][5] == "flight_recordings/custom/path/flight_10.%(ext)s"
    
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_download_youtube_video_subprocess_error(self, mock_run, mock_makedirs):
        """Test handling of subprocess error during YouTube download."""
        # Setup mock to raise CalledProcessError
        mock_run.side_effect = subprocess.CalledProcessError(1, "yt-dlp")
        
        # Call function with mocked print
        with patch('builtins.print') as mock_print:
            result = download_youtube_video("https://youtube.com/watch", "flight_5")
            
            # Verify results
            assert result is False
            mock_makedirs.assert_called_once()
            mock_print.assert_called_with(
                "An error occurred during YouTube download: Command 'yt-dlp' returned non-zero exit status 1."
            )
    
    @patch('os.makedirs')
    @patch('subprocess.run')
    def test_download_youtube_video_unexpected_error(self, mock_run, mock_makedirs):
        """Test handling of unexpected errors during YouTube download."""
        # Setup mock to raise an unexpected exception
        mock_makedirs.side_effect = Exception("Unexpected error")
        
        # Call function with mocked print
        with patch('builtins.print') as mock_print:
            result = download_youtube_video("https://youtube.com/watch", "flight_5")
            
            # Verify results
            assert result is False
            mock_makedirs.assert_called_once()
            mock_print.assert_called_with("An unexpected error occurred: Unexpected error")
