"""
Config GUI menu for creating and managing ROI configurations.
"""
import inquirer
import sys
import os
from utils.logger import get_logger
from utils.terminal import clear_screen
from .config_creator import create_new_config_cli
from .config_editor import edit_existing_config_cli
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
    config_path = create_new_config_cli()
    
    # Offer to launch GUI for ROI definition
    questions = [
        inquirer.Confirm(
            'launch_gui',
            message="Would you like to launch the Interactive ROI Configurator to define ROIs now?",
            default=True,
        ),
    ]
    
    answers = inquirer.prompt(questions)
    if answers and answers['launch_gui']:
        launch_interactive_gui(str(config_path))

def edit_existing_config():
    """Handle editing an existing ROI config."""
    config_path = edit_existing_config_cli()
    
    if config_path:
        # Offer to launch GUI for ROI editing
        questions = [
            inquirer.Confirm(
                'launch_gui',
                message="Would you like to launch the Interactive ROI Configurator to edit ROIs?",
                default=True,
            ),
        ]
        
        answers = inquirer.prompt(questions)
        if answers and answers['launch_gui']:
            launch_interactive_gui(config_path)

def launch_interactive_gui(config_path=None):
    """Launch the interactive PyQt6 GUI."""
    clear_screen()

    try:
        # Launch the GUI
        if config_path:
            # Temporarily modify sys.argv to pass the config path
            original_argv = sys.argv[:]
            sys.argv = [sys.argv[0], config_path]
            launch_gui()
            sys.argv = original_argv
        else:
            launch_gui()
    except Exception as e:
        print(f"Failed to launch GUI: {e}")
        input("\nPress Enter to continue...")
        clear_screen()