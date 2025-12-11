"""
Tests for download utility functions in download/utils.py.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import json
import os

from download.utils import get_launch_data, get_downloaded_launches

class TestGetLaunchData:
    """Test suite for get_launch_data function."""
    
    @patch('os.path.exists')
    @patch('os.walk')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_launch_data_success(self, mock_file, mock_walk, mock_exists):
        """Test successful retrieval of launch data from config files."""
        # Setup mocks
        mock_exists.return_value = True
        
        # Mock os.walk to return config files
        mock_walk.return_value = [
            ('configs', ['spacex', 'blue_origin'], []),
            ('configs/spacex', ['starship'], []),
            ('configs/spacex/starship', [], ['flight_1_rois.json', 'flight_2_rois.json']),
            ('configs/blue_origin', ['new_glenn'], []),
            ('configs/blue_origin/new_glenn', [], ['flight_1_rois.json'])
        ]
        
        # Mock file contents
        mock_file.return_value.read.return_value = json.dumps({
            "video_source": {
                "type": "twitter/x",
                "url": "https://example.com/video1"
            }
        })
        
        # Call the function
        result = get_launch_data()
        
        # Assert results
        assert result is not None
        assert "spacex" in result
        assert "starship" in result["spacex"]
        assert "flight_1" in result["spacex"]["starship"]
        assert result["spacex"]["starship"]["flight_1"]["type"] == "twitter/x"
        assert result["spacex"]["starship"]["flight_1"]["url"] == "https://example.com/video1"
    
    @patch('os.path.exists')
    def test_get_launch_data_configs_not_found(self, mock_exists):
        """Test when configs directory does not exist."""
        mock_exists.return_value = False
        
        # Call the function
        result = get_launch_data()
        
        # Assert results
        assert result is None
    
    @patch('os.path.exists')
    @patch('os.walk')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_launch_data_invalid_json(self, mock_file, mock_walk, mock_exists):
        """Test handling of invalid JSON in config files."""
        mock_exists.return_value = True
        mock_walk.return_value = [
            ('configs/spacex/starship', [], ['flight_1_rois.json'])
        ]
        
        # Mock invalid JSON
        mock_file.return_value.read.return_value = "invalid json"
        
        # Call the function
        result = get_launch_data()
        
        # Assert results - should return empty dict since file failed to parse
        assert result == {}
    
    @patch('os.path.exists')
    @patch('os.walk')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_launch_data_missing_video_source(self, mock_file, mock_walk, mock_exists):
        """Test handling of config files without video_source."""
        mock_exists.return_value = True
        mock_walk.return_value = [
            ('configs/spacex/starship', [], ['flight_1_rois.json'])
        ]
        
        # Mock config without video_source
        mock_file.return_value.read.return_value = json.dumps({"version": 3})
        
        # Call the function
        result = get_launch_data()
        
        # Assert results - should return empty dict since no valid video_source
        assert result == {}


class TestGetDownloadedLaunches:
    """Test suite for get_downloaded_launches function."""
    
    @patch('os.path.exists')
    def test_get_downloaded_launches_path_not_exists(self, mock_exists):
        """Test when output path does not exist."""
        # Setup mock
        mock_exists.return_value = False
        
        # Call the function
        result = get_downloaded_launches()
        
        # Assert results
        assert result == []
        mock_exists.assert_called_once_with("flight_recordings")
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_get_downloaded_launches_empty_dir(self, mock_listdir, mock_exists):
        """Test when output directory is empty."""
        # Setup mocks
        mock_exists.return_value = True
        mock_listdir.return_value = []
        
        # Call the function
        result = get_downloaded_launches()
        
        # Assert results
        assert result == []
        mock_exists.assert_called_once_with("flight_recordings")
        mock_listdir.assert_called_once_with("flight_recordings")
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_get_downloaded_launches_with_files(self, mock_listdir, mock_exists):
        """Test when output directory contains flight files."""
        # Setup mocks
        mock_exists.return_value = True
        mock_listdir.return_value = [
            "flight_1.mp4", 
            "flight_2.mp4", 
            "flight_5.mp4",
            "other_file.mp4",
            "not_a_flight.txt"
        ]
        
        # Call the function
        result = get_downloaded_launches()
        
        # Assert results
        assert sorted(result) == [1, 2, 5]
        mock_exists.assert_called_once_with("flight_recordings")
        mock_listdir.assert_called_once_with("flight_recordings")
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_get_downloaded_launches_invalid_filenames(self, mock_listdir, mock_exists):
        """Test handling of invalid filenames."""
        # Setup mocks
        mock_exists.return_value = True
        mock_listdir.return_value = [
            "flight_.mp4",  # Missing number
            "flight_abc.mp4",  # Non-numeric
            "flight_1",  # Missing extension
            "flight_2.mp4.part"  # Multiple extensions
        ]
        
        # Call the function
        result = get_downloaded_launches()
        
        # Assert results - should only get valid ones
        assert result == [1, 2]
        mock_exists.assert_called_once_with("flight_recordings")
        mock_listdir.assert_called_once_with("flight_recordings")
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_get_downloaded_launches_custom_path(self, mock_listdir, mock_exists):
        """Test using a custom output path."""
        # Setup mocks
        mock_exists.return_value = True
        mock_listdir.return_value = ["flight_1.mp4", "flight_2.mp4"]
        custom_path = "custom/path"
        
        # Call the function
        result = get_downloaded_launches(output_path=custom_path)
        
        # Assert results
        assert sorted(result) == [1, 2]
        mock_exists.assert_called_once_with(custom_path)
        mock_listdir.assert_called_once_with(custom_path)
