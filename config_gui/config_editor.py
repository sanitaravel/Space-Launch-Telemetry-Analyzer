"""
Config editing module for editing existing ROI configurations via CLI.
"""
import inquirer
import os
from pathlib import Path
from utils.logger import get_logger
from utils.terminal import clear_screen

logger = get_logger(__name__)

def edit_existing_config_cli():
    """CLI interface for editing an existing ROI configuration."""
    clear_screen()
    print("=== Edit Existing ROI Configuration ===\n")

    # Find all existing config files
    config_files = find_existing_configs()

    if not config_files:
        print("No existing ROI configuration files found.")
        print("Please create a new configuration first.")
        input("\nPress Enter to continue...")
        clear_screen()
        return None

    # Let user select which config to edit
    selected_config = select_config_to_edit(config_files)

    if not selected_config:
        clear_screen()
        return None

    print(f"\nSelected config: {selected_config}")

    return selected_config

def find_existing_configs():
    """Find all existing ROI config files."""
    configs_dir = Path('configs')
    config_files = []

    if configs_dir.exists():
        # Find all .json files in configs/**/
        for json_file in configs_dir.rglob('*.json'):
            if json_file.is_file():
                config_files.append(json_file)

    return config_files

def select_config_to_edit(config_files):
    """Prompt user to select a config file to edit."""
    choices = []
    for config_file in config_files:
        # Get relative path for display
        rel_path = config_file.relative_to(Path('configs'))
        # Format as provider/rocket/filename
        display_name = str(rel_path).replace('\\', '/')
        choices.append((display_name, str(config_file)))

    if not choices:
        return None

    questions = [
        inquirer.List(
            'config',
            message="Select a configuration to edit:",
            choices=choices,
        ),
    ]

    answers = inquirer.prompt(questions)

    if answers:
        return answers['config']
    else:
        return None