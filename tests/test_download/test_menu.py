"""
Tests for download menu interfaces in download/menu.py.
"""
import pytest
from unittest.mock import patch, MagicMock
import inquirer

from download.menu import (
    download_media_menu,
    prompt_menu_options,
    download_from_launch_list,
    get_flight_data,
    get_available_flights,
    display_flight_selection_menu,
    download_selected_flight,
    handle_error,
    prompt_continue_after_download,
    download_from_custom_url,
    select_platform,
    get_url_and_flight_number,
    download_from_platform,
    execute_download
)

class TestMainDownloadMenu:
    """Tests for the main download menu functionality."""
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.prompt_menu_options')
    @patch('download.menu.download_from_launch_list')
    @patch('download.menu.download_from_custom_url')
    def test_download_media_menu_launch_list(self, mock_custom_url, mock_launch_list, 
                                           mock_prompt, mock_clear):
        """Test download media menu when selecting to download from launch list."""
        # Setup mock responses
        mock_prompt.return_value = 'Download from launch list'
        mock_launch_list.return_value = True
        
        # Call function
        result = download_media_menu()
        
        # Verify results
        assert result is True
        mock_clear.assert_called_once()
        mock_prompt.assert_called_once_with("Select download option:", [
            'Download from launch list',
            'Download from custom URL',
            'Back to main menu'
        ])
        mock_launch_list.assert_called_once()
        mock_custom_url.assert_not_called()
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.prompt_menu_options')
    @patch('download.menu.download_from_launch_list')
    @patch('download.menu.download_from_custom_url')
    def test_download_media_menu_custom_url(self, mock_custom_url, mock_launch_list, 
                                          mock_prompt, mock_clear):
        """Test download media menu when selecting to download from custom URL."""
        # Setup mock responses
        mock_prompt.return_value = 'Download from custom URL'
        mock_custom_url.return_value = True
        
        # Call function
        result = download_media_menu()
        
        # Verify results
        assert result is True
        mock_clear.assert_called_once()
        mock_prompt.assert_called_once()
        mock_launch_list.assert_not_called()
        mock_custom_url.assert_called_once()
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.prompt_menu_options')
    def test_download_media_menu_back(self, mock_prompt, mock_clear):
        """Test download media menu when selecting to go back to main menu."""
        # Setup mock responses
        mock_prompt.return_value = 'Back to main menu'
        
        # Call function
        result = download_media_menu()
        
        # Verify results
        assert result is True
        # clear_screen should be called twice - once at the start and once for going back
        assert mock_clear.call_count == 2
        mock_prompt.assert_called_once()
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.get_flight_data')
    def test_download_from_launch_list_no_data(self, mock_get_data, mock_clear):
        """Test downloading from launch list when no flight data is available."""
        # Setup mock
        mock_get_data.return_value = None
        
        # Call function with mocked handle_error
        with patch('download.menu.handle_error') as mock_handle_error:
            mock_handle_error.return_value = True
            
            # Call function
            result = download_from_launch_list()
            
            # Verify results
            assert result is True
            mock_clear.assert_called_once()
            mock_get_data.assert_called_once()
            mock_handle_error.assert_called_once_with(
                "Could not retrieve flight data. Please try again later."
            )
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.get_flight_data')
    @patch('download.menu.get_available_flights')
    def test_download_from_launch_list_no_flights(self, mock_get_flights, mock_get_data, mock_clear):
        """Test downloading from launch list when no flights are available."""
        # Setup mocks
        mock_get_data.return_value = {"flight_1": {"url": "url1", "type": "youtube"}}
        mock_get_flights.return_value = []  # No available flights
        
        # Call function with mocked handle_error
        with patch('download.menu.handle_error') as mock_handle_error:
            mock_handle_error.return_value = True
            
            # Call function
            result = download_from_launch_list()
            
            # Verify results
            assert result is True
            mock_clear.assert_called_once()
            mock_get_data.assert_called_once()
            mock_get_flights.assert_called_once_with({"flight_1": {"url": "url1", "type": "youtube"}})
            mock_handle_error.assert_called_once_with(
                "All flights have already been downloaded or no flights are available."
            )
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.get_flight_data')
    @patch('download.menu.get_available_flights')
    @patch('download.menu.display_flight_selection_menu')
    @patch('download.menu.download_media_menu')
    def test_download_from_launch_list_back_option(self, mock_menu, mock_display, 
                                                mock_get_flights, mock_get_data, mock_clear):
        """Test downloading from launch list when selecting to go back."""
        # Setup mocks
        mock_get_data.return_value = {"flight_1": {"url": "url1", "type": "youtube"}}
        mock_get_flights.return_value = [("Flight 1 (YouTube)", 1)]
        mock_display.return_value = -1  # Back option
        mock_menu.return_value = True
        
        # Call function
        result = download_from_launch_list()
        
        # Verify results
        assert result is True
        mock_clear.assert_called()
        mock_get_data.assert_called_once()
        mock_get_flights.assert_called_once()
        mock_display.assert_called_once_with([("Flight 1 (YouTube)", 1), ("Back to download menu", -1)])
        mock_menu.assert_called_once()
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.get_flight_data')
    @patch('download.menu.get_available_flights')
    @patch('download.menu.display_flight_selection_menu')
    @patch('download.menu.download_selected_flight')
    @patch('download.menu.prompt_continue_after_download')
    def test_download_from_launch_list_success(self, mock_prompt, mock_download, mock_display,
                                             mock_get_flights, mock_get_data, mock_clear):
        """Test successful download from launch list."""
        # Setup mocks
        mock_get_data.return_value = {"flight_1": {"url": "url1", "type": "youtube"}}
        mock_get_flights.return_value = [("Flight 1 (YouTube)", 1)]
        mock_display.return_value = 1  # Selected Flight 1
        mock_download.return_value = True
        mock_prompt.return_value = True
        
        # Call function
        result = download_from_launch_list()
        
        # Verify results
        assert result is True
        mock_clear.assert_called_once()
        mock_get_data.assert_called_once()
        mock_get_flights.assert_called_once()
        mock_display.assert_called_once_with([("Flight 1 (YouTube)", 1), ("Back to download menu", -1)])
        mock_download.assert_called_once_with({"flight_1": {"url": "url1", "type": "youtube"}}, 1)
        mock_prompt.assert_called_once_with(True, 1)


class TestMenuUtilities:
    """Tests for menu utility functions."""
    
    @patch('download.menu.inquirer.prompt')
    def test_prompt_menu_options(self, mock_prompt):
        """Test prompting for menu options."""
        # Setup mock
        mock_prompt.return_value = {'option': 'Option 1'}
        
        # Call function
        result = prompt_menu_options("Select an option:", ['Option 1', 'Option 2'])
        
        # Verify results
        assert result == 'Option 1'
        mock_prompt.assert_called_once()
        
        # Verify the question was properly constructed
        args, _ = mock_prompt.call_args
        assert len(args[0]) == 1
        assert args[0][0].message == "Select an option:"
        assert args[0][0].choices == ['Option 1', 'Option 2']
    
    @patch('download.menu.input')
    @patch('download.menu.clear_screen')
    def test_prompt_continue_after_download_success(self, mock_clear, mock_input):
        """Test prompting for continuation after successful download."""
        # Call function
        with patch('builtins.print') as mock_print:
            result = prompt_continue_after_download(True, "spacex_starship_flight_5")
            
            # Verify results
            assert result is True
            mock_print.assert_called_with("Download of spacex_starship_flight_5 completed successfully.")
            mock_input.assert_called_once_with("\nPress Enter to continue...")
            mock_clear.assert_called_once()
    
    @patch('download.menu.input')
    @patch('download.menu.clear_screen')
    def test_prompt_continue_after_download_failure(self, mock_clear, mock_input):
        """Test prompting for continuation after failed download."""
        # Call function
        with patch('builtins.print') as mock_print:
            result = prompt_continue_after_download(False, "spacex_starship_flight_5")
            
            # Verify results
            assert result is True
            mock_print.assert_called_with("Failed to download spacex_starship_flight_5.")
            mock_input.assert_called_once_with("\nPress Enter to continue...")
            mock_clear.assert_called_once()


class TestFlightData:
    """Tests for flight data management functions."""
    
    @patch('download.menu.get_launch_data')
    def test_get_flight_data(self, mock_get_launch_data):
        """Test getting flight data passes through to utils."""
        # Setup mock with nested structure
        mock_get_launch_data.return_value = {
            "spacex": {
                "starship": {
                    "flight_1": {"url": "url1", "type": "youtube"}
                }
            }
        }
        
        # Call function
        result = get_flight_data()
        
        # Verify results - should be flattened
        expected = {
            "spacex_starship_flight_1": {
                "company": "spacex",
                "vehicle": "starship", 
                "flight_key": "flight_1",
                "type": "youtube",
                "url": "url1"
            }
        }
        assert result == expected
        mock_get_launch_data.assert_called_once()
    
    @patch('download.menu.get_downloaded_launches')
    def test_get_available_flights(self, mock_get_downloaded):
        """Test getting available flights."""
        # Setup mock
        mock_get_downloaded.return_value = [2, 3]
        flight_data = {
            "spacex_starship_flight_1": {
                "company": "spacex",
                "vehicle": "starship",
                "flight_key": "flight_1",
                "type": "youtube",
                "url": "url1"
            },
            "spacex_starship_flight_2": {
                "company": "spacex",
                "vehicle": "starship", 
                "flight_key": "flight_2",
                "type": "twitter/x",
                "url": "url2"
            },
            "spacex_starship_flight_4": {
                "company": "spacex",
                "vehicle": "starship",
                "flight_key": "flight_4", 
                "type": "twitter",
                "url": "url4"
            }
        }
        
        # Call function
        result = get_available_flights(flight_data)
        
        # Verify results
        assert len(result) == 2
        assert ("Flight 1 (Spacex Starship, YouTube)", "spacex_starship_flight_1") in result
        assert ("Flight 4 (Spacex Starship, Twitter/X)", "spacex_starship_flight_4") in result
        assert all(unique_key not in ["spacex_starship_flight_2", "spacex_starship_flight_3"] for _, unique_key in result)
        mock_get_downloaded.assert_called_once()
        
    @patch('download.menu.logger')
    @patch('download.menu.get_downloaded_launches')
    def test_get_available_flights_with_invalid_entries(self, mock_get_downloaded, mock_logger):
        """Test handling of invalid entries in flight data."""
        # Setup mock
        mock_get_downloaded.return_value = []
        flight_data = {
            "spacex_starship_flight_1": {
                "company": "spacex",
                "vehicle": "starship",
                "flight_key": "flight_1",
                "type": "youtube",
                "url": "url1"
            },
            "invalid1": {
                "company": "spacex",
                "vehicle": "starship",
                "flight_key": "malformed",
                "type": "youtube",
                "url": "url2"
            },  # Invalid flight_key
            "invalid2": {
                "company": "spacex",
                "vehicle": "starship",
                "flight_key": "flight_abc",
                "type": "youtube",
                "url": "url3"
            }  # Non-numeric flight number
        }
        
        # Call function
        result = get_available_flights(flight_data)
        
        # Verify results
        assert len(result) == 1
        assert ("Flight 1 (Spacex Starship, YouTube)", "spacex_starship_flight_1") in result
        mock_get_downloaded.assert_called_once()
        assert mock_logger.warning.call_count == 2  # Should log warnings for the 2 invalid entries


class TestFlightSelection:
    """Tests for flight selection functionality."""
    
    @patch('download.menu.inquirer.prompt')
    def test_display_flight_selection_menu(self, mock_prompt):
        """Test displaying flight selection menu."""
        # Setup mock
        mock_prompt.return_value = {'selected_flight': "spacex_starship_flight_3"}
        choices = [("Flight 1", "spacex_starship_flight_1"), ("Flight 3", "spacex_starship_flight_3"), ("Back", -1)]
        
        # Call function
        result = display_flight_selection_menu(choices)
        
        # Verify results
        assert result == "spacex_starship_flight_3"
        mock_prompt.assert_called_once()
        
        # Check that the question was properly formed
        args, _ = mock_prompt.call_args
        assert len(args[0]) == 1
        assert args[0][0].message == "Select a flight to download:"
        assert args[0][0].choices == choices
    
    @patch('download.menu.execute_download')
    def test_download_selected_flight_success(self, mock_execute):
        """Test downloading a selected flight successfully."""
        # Setup mock
        mock_execute.return_value = True
        flight_data = {
            "spacex_starship_flight_5": {
                "company": "spacex",
                "vehicle": "starship",
                "flight_key": "flight_5",
                "type": "youtube",
                "url": "url5"
            }
        }
        
        # Call function with mocked print to capture output
        with patch('builtins.print') as mock_print:
            result = download_selected_flight(flight_data, "spacex_starship_flight_5")
            
            # Verify results
            assert result is True
            mock_execute.assert_called_once_with("youtube", "url5", 5)
            mock_print.assert_called_with("Downloading spacex_starship_flight_5 from url5...")
    
    @patch('download.menu.execute_download')
    def test_download_selected_flight_failure(self, mock_execute):
        """Test handling of failure when downloading a flight."""
        # Setup mock
        mock_execute.return_value = False
        flight_data = {
            "spacex_starship_flight_5": {
                "company": "spacex",
                "vehicle": "starship",
                "flight_key": "flight_5",
                "type": "twitter/x",
                "url": "url5"
            }
        }
        
        # Call function with mocked print
        result = download_selected_flight(flight_data, "spacex_starship_flight_5")
        
        # Verify results
        assert result is False
        mock_execute.assert_called_once_with("twitter/x", "url5", 5)
    
    def test_download_selected_flight_not_found(self):
        """Test handling of flight not found in data."""
        # Setup
        flight_data = {
            "spacex_starship_flight_5": {
                "company": "spacex",
                "vehicle": "starship",
                "flight_key": "flight_5",
                "type": "youtube",
                "url": "url5"
            }
        }
        
        # Call function with mocked print
        with patch('builtins.print') as mock_print:
            result = download_selected_flight(flight_data, "spacex_starship_flight_10")  # Flight 10 not in data
            
            # Verify results
            assert result is False
            mock_print.assert_called_with("Flight information for spacex_starship_flight_10 not found.")


class TestErrorHandling:
    """Tests for error handling utilities."""
    
    @patch('download.menu.input')
    @patch('download.menu.clear_screen')
    def test_handle_error(self, mock_clear, mock_input):
        """Test handling of errors with user prompt."""
        # Call function
        with patch('builtins.print') as mock_print:
            result = handle_error("Test error message")
            
            # Verify results
            assert result is True
            mock_print.assert_called_with("Test error message")
            mock_input.assert_called_once_with("\nPress Enter to continue...")
            mock_clear.assert_called_once()


class TestCustomUrlDownloads:
    """Tests for custom URL download functionality."""
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.select_platform')
    @patch('download.menu.download_media_menu')
    def test_download_from_custom_url_back(self, mock_menu, mock_select, mock_clear):
        """Test downloading from custom URL when selecting to go back."""
        # Setup mock
        mock_select.return_value = 'Back to download menu'
        mock_menu.return_value = True
        
        # Call function
        result = download_from_custom_url()
        
        # Verify results
        assert result is True
        # clear_screen is called twice - once at the start and once before going back
        assert mock_clear.call_count == 2
        mock_select.assert_called_once()
        mock_menu.assert_called_once()
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.select_platform')
    @patch('download.menu.get_url_and_flight_number')
    @patch('download.menu.handle_error')
    def test_download_from_custom_url_cancelled(self, mock_error, mock_get_url, mock_select, mock_clear):
        """Test downloading from custom URL when cancelled by user."""
        # Setup mocks
        mock_select.return_value = 'YouTube Video'
        mock_get_url.return_value = (None, None)  # URL is None, meaning cancelled
        mock_error.return_value = True
        
        # Call function
        result = download_from_custom_url()
        
        # Verify results
        assert result is True
        # Only called once at the start since handle_error handles the clear_screen at the end
        mock_clear.assert_called_once()
        mock_select.assert_called_once()
        mock_get_url.assert_called_once_with('YouTube Video')
        mock_error.assert_called_once_with("Download cancelled.")
    
    @patch('download.menu.clear_screen')
    @patch('download.menu.select_platform')
    @patch('download.menu.get_url_and_flight_number')
    @patch('download.menu.download_from_platform')
    @patch('download.menu.input')
    def test_download_from_custom_url_success(self, mock_input, mock_download, mock_get_url, 
                                           mock_select, mock_clear):
        """Test successfully downloading from custom URL."""
        # Setup mocks
        mock_select.return_value = 'YouTube Video'
        mock_get_url.return_value = ('https://example.com/video', 5)
        mock_download.return_value = True
        
        # Call function with mocked print
        with patch('builtins.print') as mock_print:
            result = download_from_custom_url()
            
            # Verify results
            assert result is True
            # clear_screen is called twice - once at the start and once after user input
            assert mock_clear.call_count == 2
            mock_select.assert_called_once()
            mock_get_url.assert_called_once_with('YouTube Video')
            mock_download.assert_called_once_with('YouTube Video', 'https://example.com/video', 5)
            mock_print.assert_called_with("Download completed successfully.")
            mock_input.assert_called_once_with("\nPress Enter to continue...")


class TestPlatformSelection:
    """Tests for platform selection and handling."""
    
    @patch('download.menu.prompt_menu_options')
    def test_select_platform(self, mock_prompt):
        """Test selecting a download platform."""
        # Setup mock
        mock_prompt.return_value = 'YouTube Video'
        
        # Call function
        result = select_platform()
        
        # Verify results
        assert result == 'YouTube Video'
        mock_prompt.assert_called_once_with("Select platform to download from", [
            'Twitter/X Broadcast',
            'YouTube Video',
            'Back to download menu'
        ])
    
    @patch('download.menu.inquirer.prompt')
    def test_get_url_and_flight_number_valid(self, mock_prompt):
        """Test getting a valid URL and flight number from user."""
        # Setup mock
        mock_prompt.return_value = {
            'url': 'https://example.com/video',
            'flight_number': '5'
        }
        
        # Call function
        url, flight_number = get_url_and_flight_number('YouTube Video')
        
        # Verify results
        assert url == 'https://example.com/video'
        assert flight_number == 5  # Should be converted to int
        mock_prompt.assert_called_once()
        
        # Verify the questions were properly constructed
        args, _ = mock_prompt.call_args
        assert len(args[0]) == 2
        assert args[0][0].message == "Enter the YouTube Video URL"
        assert args[0][1].message == "Enter the flight number"
    
    @patch('download.menu.inquirer.prompt')
    def test_get_url_and_flight_number_cancel(self, mock_prompt):
        """Test getting URL and flight number when user cancels."""
        # Setup mock for cancel/empty URL
        mock_prompt.return_value = {
            'url': '',
            'flight_number': '5'
        }
        
        # Call function
        url, flight_number = get_url_and_flight_number('YouTube Video')
        
        # Verify results
        assert url is None
        assert flight_number is None
        mock_prompt.assert_called_once()
    
    @patch('download.menu.inquirer.prompt')
    def test_get_url_and_flight_number_no_response(self, mock_prompt):
        """Test getting URL when user provides no response (None)."""
        # Setup mock for None response (e.g., user hits Ctrl+C)
        mock_prompt.return_value = None
        
        # Call function
        url, flight_number = get_url_and_flight_number('YouTube Video')
        
        # Verify results
        assert url is None
        assert flight_number is None
        mock_prompt.assert_called_once()
    
    @patch('download.menu.download_twitter_broadcast')
    def test_download_from_platform_twitter(self, mock_twitter):
        """Test downloading from Twitter platform."""
        # Setup mock
        mock_twitter.return_value = True
        
        # Call function
        result = download_from_platform('Twitter/X Broadcast', 'https://twitter.com/video', 5)
        
        # Verify results
        assert result is True
        mock_twitter.assert_called_once_with('https://twitter.com/video', 'flight_5')
    
    @patch('download.menu.download_youtube_video')
    def test_download_from_platform_youtube(self, mock_youtube):
        """Test downloading from YouTube platform."""
        # Setup mock
        mock_youtube.return_value = True
        
        # Call function
        result = download_from_platform('YouTube Video', 'https://youtube.com/video', 5)
        
        # Verify results
        assert result is True
        mock_youtube.assert_called_once_with('https://youtube.com/video', 'flight_5')
    
    def test_download_from_platform_unknown(self):
        """Test downloading from an unknown platform."""
        # Call function with an invalid platform
        result = download_from_platform('Unknown Platform', 'https://example.com', 5)
        
        # Should return False for unknown platform
        assert result is False


class TestDownloadOperations:
    """Tests for download execution functions."""
    
    @patch('download.menu.download_youtube_video')
    def test_execute_download_youtube(self, mock_youtube):
        """Test executing a YouTube download."""
        # Setup mock
        mock_youtube.return_value = True
        
        # Call function
        result = execute_download('youtube', 'https://youtube.com/video', 'flight_5')
        
        # Verify results
        assert result is True
        mock_youtube.assert_called_once_with('https://youtube.com/video', 'flight_5', None, None)
    
    @patch('download.menu.download_twitter_broadcast')
    def test_execute_download_twitter(self, mock_twitter):
        """Test executing a Twitter download."""
        # Setup mock
        mock_twitter.return_value = True
        
        # Test all supported Twitter media type variants
        for twitter_type in ["twitter/x", "twitter", "x"]:
            # Call function
            result = execute_download(twitter_type, 'https://twitter.com/video', 'flight_5')
            
            # Verify results
            assert result is True
            
        # Verify mock was called three times (once for each type)
        assert mock_twitter.call_count == 3
        mock_twitter.assert_called_with('https://twitter.com/video', 'flight_5', None, None)
    
    def test_execute_download_unknown(self):
        """Test executing a download with an unknown media type."""
        # Call function with an invalid media type
        result = execute_download('unknown', 'https://example.com', 'flight_5')
        
        # Should return False for unknown media type
        assert result is False
