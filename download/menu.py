"""
Menu interfaces for download operations.
"""
import inquirer
from download.utils import get_downloaded_launches, get_launch_data
from utils.logger import get_logger
from .downloader import download_twitter_broadcast, download_youtube_video
from utils.terminal import clear_screen
from utils.validators import validate_number, validate_url

logger = get_logger(__name__)

def download_media_menu():
    """Combined menu for downloading media from different sources."""
    clear_screen()
    logger.debug("Starting media download menu")
    
    menu_options = [
        'Download from launch list',
        'Download from custom URL',
        'Back to main menu'
    ]
    
    menu_answer = prompt_menu_options("Select download option:", menu_options)
    
    if menu_answer == 'Back to main menu':
        clear_screen()
        return True
    
    if menu_answer == 'Download from launch list':
        return download_from_launch_list()
    else:  # Download from custom URL
        return download_from_custom_url()

def prompt_menu_options(message, options):
    """Show a menu with the given options and return the selected option."""
    menu_question = [
        inquirer.List(
            'option',
            message=message,
            choices=options,
        ),
    ]
    
    menu_answer = inquirer.prompt(menu_question)
    return menu_answer['option']

def download_from_launch_list():
    """Download video from the GitHub flight list with hierarchical selection."""
    clear_screen()
    logger.debug("Downloading from flight list")
    
    flight_data = get_flight_data()
    if not flight_data:
        return handle_error("Could not retrieve flight data. Please try again later.")
    
    # Step 1: Select company
    company = select_company(flight_data)
    if company == 'Back to download menu':
        clear_screen()
        return download_media_menu()
    
    # Step 2: Select vehicle
    vehicle = select_vehicle(flight_data, company)
    if vehicle == 'Back to company selection':
        clear_screen()
        return download_from_launch_list()
    
    # Step 3: Select flight
    selected_unique_key = select_flight(flight_data, company, vehicle)
    if selected_unique_key == 'Back to vehicle selection':
        clear_screen()
        return download_from_launch_list()
    
    download_status = download_selected_flight(flight_data, selected_unique_key)
    
    return prompt_continue_after_download(download_status, selected_unique_key)

def get_flight_data():
    """Retrieve flight data from repository."""
    data = get_launch_data()
    if not data:
        return None
    return flatten_flight_data(data)

def flatten_flight_data(data):
    """Flatten the nested flight data structure into a flat dict."""
    flat_data = {}
    for company, vehicles in data.items():
        for vehicle, flights in vehicles.items():
            for flight_key, flight_info in flights.items():
                # Create a unique key
                unique_key = f"{company}_{vehicle}_{flight_key}"
                flat_data[unique_key] = {
                    "company": company,
                    "vehicle": vehicle,
                    "flight_key": flight_key,
                    "type": flight_info.get("type"),
                    "url": flight_info.get("url")
                }
    return flat_data

def get_available_companies(flight_data):
    """Get list of available companies."""
    companies = set()
    for unique_key, info in flight_data.items():
        companies.add(info["company"])
    return sorted(list(companies))

def get_available_vehicles(flight_data, company):
    """Get list of available vehicles for a company."""
    vehicles = set()
    for unique_key, info in flight_data.items():
        if info["company"] == company:
            vehicles.add(info["vehicle"])
    return sorted(list(vehicles))

def get_available_flights_for_vehicle(flight_data, company, vehicle):
    """Create a list of flights for a specific company and vehicle that haven't been downloaded yet."""
    downloaded_flights = get_downloaded_launches()
    
    available_flights = []
    for unique_key, info in flight_data.items():
        if info["company"] == company and info["vehicle"] == vehicle:
            try:
                flight_num = int(info["flight_key"].split("_")[1])
                if flight_num not in downloaded_flights:
                    flight_type = "YouTube" if info["type"] == "youtube" else "Twitter/X"
                    label = f"Flight {flight_num} ({flight_type})"
                    available_flights.append((label, unique_key))
            except (IndexError, ValueError, KeyError):
                logger.warning(f"Skipping malformed flight entry: {unique_key}")
                continue
    
    # Sort by flight number
    available_flights.sort(key=lambda x: int(x[1].split("flight_")[1]))
    return available_flights

def display_flight_selection_menu(choices):
    """Display menu for flight selection and return selected flight number."""
    flight_question = [
        inquirer.List(
            'selected_flight',
            message="Select a flight to download:",
            choices=choices,
        ),
    ]
    
    flight_answer = inquirer.prompt(flight_question)
    return flight_answer['selected_flight']

def select_company(flight_data):
    """Select a company from available companies."""
    companies = get_available_companies(flight_data)
    if not companies:
        print("No companies available.")
        input("\nPress Enter to continue...")
        return 'Back to download menu'
    
    choices = companies + ['Back to download menu']
    
    return prompt_menu_options("Select a company:", choices)

def select_vehicle(flight_data, company):
    """Select a vehicle for the given company."""
    vehicles = get_available_vehicles(flight_data, company)
    if not vehicles:
        print(f"No vehicles available for {company}.")
        input("\nPress Enter to continue...")
        return 'Back to company selection'
    
    vehicle_choices = [vehicle.replace('_', ' ').title() for vehicle in vehicles]
    choices = vehicle_choices + ['Back to company selection']
    
    selected_display = prompt_menu_options(f"Select a vehicle for {company.replace('_', ' ').title()}:", choices)
    
    if selected_display == 'Back to company selection':
        return selected_display
    
    # Convert back to internal format
    return selected_display.lower().replace(' ', '_')

def select_flight(flight_data, company, vehicle):
    """Select a flight for the given company and vehicle."""
    available_flights = get_available_flights_for_vehicle(flight_data, company, vehicle)
    
    if not available_flights:
        print(f"All flights have already been downloaded for {company} {vehicle}.")
        input("\nPress Enter to continue...")
        return 'Back to vehicle selection'
    
    choices = available_flights + [("Back to vehicle selection", 'Back to vehicle selection')]
    
    return display_flight_selection_menu(choices)

def download_selected_flight(flight_data, selected_unique_key):
    """Download the selected flight."""
    flight_info = flight_data.get(selected_unique_key)
    
    if not flight_info:
        print(f"Flight information for {selected_unique_key} not found.")
        return False
    
    url = flight_info['url']
    flight_type = flight_info['type']
    flight_num = int(flight_info['flight_key'].split('_')[1])
    
    print(f"Downloading {selected_unique_key} from {url}...")
    return execute_download(flight_type, url, flight_num)

def handle_error(message):
    """Display error message and prompt to continue."""
    print(message)
    input("\nPress Enter to continue...")
    clear_screen()
    return True

def prompt_continue_after_download(success, unique_key):
    """Show download status message and prompt to continue."""
    if success:
        print(f"Download of {unique_key} completed successfully.")
    else:
        print(f"Failed to download {unique_key}.")
    
    input("\nPress Enter to continue...")
    clear_screen()
    return True

def download_from_custom_url():
    """Download media from a custom URL."""
    clear_screen()
    logger.debug("Downloading from custom URL")
    
    platform = select_platform()
    
    if platform == 'Back to download menu':
        clear_screen()
        return download_media_menu()
    
    url, flight_number = get_url_and_flight_number(platform)
    
    if not url:
        return handle_error("Download cancelled.")
    
    success = download_from_platform(platform, url, flight_number)
    
    if success:
        print("Download completed successfully.")
    
    input("\nPress Enter to continue...")
    clear_screen()
    return True

def select_platform():
    """Show menu to select download platform."""
    platform_choices = [
        'Twitter/X Broadcast',
        'YouTube Video',
        'Back to download menu'
    ]
    
    return prompt_menu_options("Select platform to download from", platform_choices)

def get_url_and_flight_number(platform):
    """Prompt for URL and flight number."""
    questions = [
        inquirer.Text('url', message=f"Enter the {platform} URL", 
                     validate=validate_url),
        inquirer.Text('flight_number', message="Enter the flight number", 
                     validate=validate_number)
    ]
    
    answers = inquirer.prompt(questions)
    
    if not answers or not answers['url'].strip():
        return None, None
    
    return answers['url'].strip(), int(answers['flight_number'])

def download_from_platform(platform, url, flight_number):
    """Execute download based on selected platform."""
    if platform == 'Twitter/X Broadcast':
        return download_twitter_broadcast(url, flight_number)
    elif platform == 'YouTube Video':
        return download_youtube_video(url, flight_number)
    return False

def execute_download(media_type, url, flight_num):
    """Execute download based on media type."""
    if media_type == "youtube":
        return download_youtube_video(url, flight_num)
    elif media_type in ["twitter/x", "twitter", "x"]:
        return download_twitter_broadcast(url, flight_num)
    return False
