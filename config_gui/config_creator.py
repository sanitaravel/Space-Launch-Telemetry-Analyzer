"""
Config creation module for creating new ROI configurations via CLI.
"""
import inquirer
import json
import os
from pathlib import Path
from utils.logger import get_logger
from utils.terminal import clear_screen
from utils.validators import validate_number, validate_url
from download.downloader import download_twitter_broadcast, download_youtube_video

logger = get_logger(__name__)

def create_new_config_cli():
    """CLI interface for creating a new ROI configuration."""
    clear_screen()
    print("=== Create New ROI Configuration ===\n")

    # Step 1: Select or create provider
    provider = select_or_create_provider()

    # Step 2: Select or create rocket
    rocket = select_or_create_rocket(provider)

    # Step 3: Get launch number
    launch_number = get_launch_number()

    # Step 4: Get webcast URL
    webcast_url = get_webcast_url()

    # Step 5: Create basic config structure
    config_data = create_basic_config_structure(provider, rocket, launch_number, webcast_url)

    # Step 6: Save config file
    config_path = save_config_file(provider, rocket, launch_number, config_data)

    print(f"\n✅ Configuration created successfully!")
    print(f"📁 Saved to: {config_path}")

    # Step 7: Offer to download the video
    should_download = offer_to_download_video()
    if should_download:
        download_success = download_video(webcast_url, launch_number, provider, rocket)
        if download_success:
            print(f"📹 Video downloaded successfully!")
        else:
            print(f"❌ Failed to download video. You can try downloading it later from the Download Media menu.")

    return config_path

def select_or_create_provider():
    """Prompt user to select existing provider or create new one."""
    configs_dir = Path('configs')
    providers = []

    if configs_dir.exists():
        providers = [d.name for d in configs_dir.iterdir() if d.is_dir()]

    choices = providers + ['Create new provider']

    questions = [
        inquirer.List(
            'provider',
            message="Select a launch provider:",
            choices=choices,
        ),
    ]

    answers = inquirer.prompt(questions)

    if answers['provider'] == 'Create new provider':
        # Prompt for new provider name
        name_question = [
            inquirer.Text(
                'name',
                message="Enter new provider name:",
                validate=lambda _, x: len(x.strip()) > 0,
            ),
        ]
        name_answer = inquirer.prompt(name_question)
        provider = name_answer['name'].strip().lower().replace(' ', '_')
    else:
        provider = answers['provider']

    return provider

def select_or_create_rocket(provider):
    """Prompt user to select existing rocket or create new one."""
    provider_path = Path('configs') / provider
    rockets = []

    if provider_path.exists():
        rockets = [d.name for d in provider_path.iterdir() if d.is_dir()]

    choices = rockets + ['Create new rocket']

    questions = [
        inquirer.List(
            'rocket',
            message=f"Select a rocket for provider '{provider}':",
            choices=choices,
        ),
    ]

    answers = inquirer.prompt(questions)

    if answers['rocket'] == 'Create new rocket':
        # Prompt for new rocket name
        name_question = [
            inquirer.Text(
                'name',
                message="Enter new rocket name:",
                validate=lambda _, x: len(x.strip()) > 0,
            ),
        ]
        name_answer = inquirer.prompt(name_question)
        rocket = name_answer['name'].strip().lower().replace(' ', '_')
    else:
        rocket = answers['rocket']

    return rocket

def get_launch_number():
    """Prompt user for launch number."""
    questions = [
        inquirer.Text(
            'launch_number',
            message="Enter launch number:",
            validate=validate_number,
        ),
    ]

    answers = inquirer.prompt(questions)
    return int(answers['launch_number'])

def get_webcast_url():
    """Prompt user for webcast URL."""
    questions = [
        inquirer.Text(
            'url',
            message="Enter webcast URL (e.g., https://x.com/i/broadcasts/...):",
            validate=validate_url,
        ),
    ]

    answers = inquirer.prompt(questions)
    return answers['url'].strip()

def create_basic_config_structure(provider, rocket, launch_number, webcast_url):
    """Create basic config structure with metadata."""
    config_data = {
        "version": 6,
        "video_source": {
            "type": "twitter/x",
            "url": webcast_url
        },
        "time_unit": "frames",
        "vehicles": [rocket],  # Default to the rocket name as vehicle
        "rois": []
    }

    return config_data

def save_config_file(provider, rocket, launch_number, config_data):
    """Save the config file to the appropriate location."""
    # Create directory structure if it doesn't exist
    config_dir = Path('configs') / provider / rocket
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create filename
    filename = f"flight_{launch_number}_rois.json"
    config_path = config_dir / filename

    # Save the config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Created new config file: {config_path}")
    return config_path

def offer_to_download_video():
    """Ask user if they want to download the video now."""
    questions = [
        inquirer.Confirm(
            'download',
            message="Would you like to download the video now?",
            default=True,
        ),
    ]

    answers = inquirer.prompt(questions)
    return answers['download']

def download_video(url, launch_number, provider, rocket):
    """Download the video using the appropriate downloader."""
    flight_identifier = f"flight_{launch_number}"

    # Determine platform from URL
    if 'youtube.com' in url or 'youtu.be' in url:
        print(f"Downloading YouTube video...")
        return download_youtube_video(url, flight_identifier, provider, rocket)
    elif 'x.com' in url or 'twitter.com' in url:
        print(f"Downloading Twitter/X broadcast...")
        return download_twitter_broadcast(url, flight_identifier, provider, rocket)
    else:
        print(f"Unsupported URL format: {url}")
        return False