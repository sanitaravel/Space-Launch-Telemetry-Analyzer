"""
Config GUI menu for creating and managing ROI configurations.
"""
import inquirer
from utils.logger import get_logger
from utils.terminal import clear_screen
from .config_creator import create_new_config_cli
from .main import main as launch_gui

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
                'Edit existing ROI config (CLI)',
                'Launch Interactive ROI Configurator (GUI)',
                'Back to main menu'
            ],
        ),
    ]

    answers = inquirer.prompt(questions)

    if answers is None:
        clear_screen()
        return True

    logger.debug(f"Config GUI menu: User selected: {answers['action']}")

    if answers['action'] == 'Create new ROI config':
        create_new_config()
        return config_gui_menu()
    elif answers['action'] == 'Edit existing ROI config (CLI)':
        edit_existing_config()
        return config_gui_menu()
    elif answers['action'] == 'Launch Interactive ROI Configurator (GUI)':
        launch_interactive_gui()
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

def launch_interactive_gui():
    """Launch the interactive PyQt6 GUI."""
    clear_screen()
    print("Launching Interactive ROI Configurator...")
    print("Note: Make sure you have a config file ready, or create one first.")
    print("The GUI will allow you to visually select ROIs on video frames.")
    input("\nPress Enter to launch GUI...")
    clear_screen()

    try:
        # Launch the GUI
        launch_gui()
    except Exception as e:
        print(f"Failed to launch GUI: {e}")
        input("\nPress Enter to continue...")
        clear_screen()