"""
Config GUI menu for creating and managing ROI configurations.
"""
import inquirer
from utils.logger import get_logger
from utils.terminal import clear_screen
from .config_creator import create_new_config_cli

logger = get_logger(__name__)

def config_gui_menu():
    """Main menu for config GUI operations."""
    clear_screen()

    questions = [
        inquirer.List(
            'action',
            message="Config GUI Options:",
            choices=[
                'Create new ROI config',
                'Edit existing ROI config',
                'View config details',
                'Back to main menu'
            ],
        ),
    ]

    answers = inquirer.prompt(questions)

    logger.debug(f"Config GUI menu: User selected: {answers['action']}")

    if answers['action'] == 'Create new ROI config':
        create_new_config()
        return config_gui_menu()
    elif answers['action'] == 'Edit existing ROI config':
        edit_existing_config()
        return config_gui_menu()
    elif answers['action'] == 'View config details':
        view_config_details()
        return config_gui_menu()
    elif answers['action'] == 'Back to main menu':
        clear_screen()
        return True

    clear_screen()
    return True

def create_new_config():
    """Handle creating a new ROI config."""
    create_new_config_cli()

def edit_existing_config():
    """Handle editing an existing ROI config."""
    clear_screen()
    print("Edit existing ROI config - Feature coming soon!")
    input("\nPress Enter to continue...")
    clear_screen()

def view_config_details():
    """Handle viewing config details."""
    clear_screen()
    print("View config details - Feature coming soon!")
    input("\nPress Enter to continue...")
    clear_screen()