"""
Main menu interface for the application.
"""
import inquirer
from utils.logger import get_logger
from utils.terminal import clear_screen
from .video_menu import video_processing_menu
from .visualization_menu import visualization_menu
from config_gui.config_gui_menu import config_gui_menu
from download import download_media_menu

logger = get_logger(__name__)

def display_menu(debug_status) -> bool:
    """
    Display a step-by-step menu for the user to navigate and select options.
    
    Args:
        debug_status (str): Current debug mode status
        
    Returns:
        bool: True to continue the program, False to exit
    """
    clear_screen()
    questions = [
        inquirer.List(
            'action',
            message="Main Menu - Select an option:",
            choices=[
                'Video Processing',
                'Data Visualization',
                'Config Menu',
                'Download Media',
                f'Toggle Debug Mode (Currently: {debug_status})',
                'Exit'
            ],
        ),
    ]

    answers = inquirer.prompt(questions)
    
    logger.debug(f"Main menu: User selected: {answers['action']}")

    if answers['action'] == 'Video Processing':
        video_processing_menu()
        return True
    elif answers['action'] == 'Data Visualization':
        visualization_menu()
        return True
    elif answers['action'] == 'Config Menu':
        config_gui_menu()
        return True
    elif answers['action'] == 'Download Media':
        download_media_menu()
        return True
    elif answers['action'].startswith('Toggle Debug Mode'):
        return "TOGGLE_DEBUG"  # Special return value to toggle debug in main
    elif answers['action'] == 'Exit':
        clear_screen()
        print("Exiting the program.")
        return False  # Return False to break the loop in main()
    
    return True
