"""
Visualization menu and related functionality.
"""
import inquirer
import os
from pathlib import Path
from utils.logger import get_logger
from utils.terminal import clear_screen
from utils.validators import validate_number
from plot import plot_flight_data, compare_multiple_launches

logger = get_logger(__name__)

def get_results_providers():
    """Get list of available launch providers from results folder."""
    results_folder = Path('results')
    if not results_folder.exists():
        return []
    return [d.name for d in results_folder.iterdir() if d.is_dir()]

def get_results_rockets(provider):
    """Get list of available rockets for a provider from results folder."""
    provider_path = Path('results') / provider
    if not provider_path.exists():
        return []
    return [d.name for d in provider_path.iterdir() if d.is_dir()]

def get_results_launches(provider, rocket):
    """Get list of available launches for a provider and rocket from results folder."""
    rocket_path = Path('results') / provider / rocket
    if not rocket_path.exists():
        return []
    launches = []
    for launch_dir in rocket_path.iterdir():
        if launch_dir.is_dir() and launch_dir.name.startswith('launch_'):
            results_json = launch_dir / 'results.json'
            if results_json.exists():
                launches.append((launch_dir.name, str(results_json)))
    return launches

def visualization_menu():
    """Submenu for data visualization options."""
    clear_screen()
    questions = [
        inquirer.List(
            'action',
            message="Visualization Options:",
            choices=[
                'Visualize flight data',
                'Visualize multiple launches data',
                'Back to main menu'
            ],
        ),
    ]
    
    answers = inquirer.prompt(questions)
    
    logger.debug(f"Visualization menu: User selected: {answers['action']}")
    
    if answers['action'] == 'Visualize flight data':
        visualize_flight_data()
        return visualization_menu()
    elif answers['action'] == 'Visualize multiple launches data':
        compare_multiple_launches_menu()
        return visualization_menu()
    elif answers['action'] == 'Back to main menu':
        clear_screen()
        return True
    
    clear_screen()
    return True

def visualize_flight_data():
    """Handle the visualize flight data menu option."""
    clear_screen()
    
    # Get hierarchical selection
    providers = get_results_providers()
    if not providers:
        print("No launch providers found in results folder.")
        input("\nPress Enter to continue...")
        clear_screen()
        return True
    
    provider_question = [
        inquirer.List(
            'provider',
            message="Select a launch provider",
            choices=providers,
        )
    ]
    provider_answer = inquirer.prompt(provider_question)
    provider = provider_answer['provider']
    
    rockets = get_results_rockets(provider)
    if not rockets:
        print(f"No rockets found for provider {provider}.")
        input("\nPress Enter to continue...")
        clear_screen()
        return True
    
    rocket_question = [
        inquirer.List(
            'rocket',
            message="Select a rocket",
            choices=rockets,
        )
    ]
    rocket_answer = inquirer.prompt(rocket_question)
    rocket = rocket_answer['rocket']
    
    launches = get_results_launches(provider, rocket)
    if not launches:
        print(f"No launches found for {provider}/{rocket}.")
        input("\nPress Enter to continue...")
        clear_screen()
        return True
    
    launch_question = [
        inquirer.List(
            'launch',
            message="Select a launch",
            choices=[name for name, path in launches],
        )
    ]
    launch_answer = inquirer.prompt(launch_question)
    selected_name = launch_answer['launch']
    
    # Find the corresponding path
    json_path = None
    for name, path in launches:
        if name == selected_name:
            json_path = path
            break
    
    if not json_path:
        print("Error: Could not find selected launch.")
        input("\nPress Enter to continue...")
        clear_screen()
        return True
    
    # Continue with time selection and plotting
    questions = [
        inquirer.Text(
            'start_time', message="Start time in seconds (default: 0)", validate=validate_number),
        inquirer.Text(
            'end_time', message="End time in seconds (default: -1 for all data)", validate=validate_number),
        inquirer.Confirm(
            'show_figures', message="Display figures interactively?", default=True)
    ]
    answers = inquirer.prompt(questions)

    start_time = int(answers['start_time']) if answers['start_time'] else 0
    end_time = int(answers['end_time']) if answers['end_time'] else -1
    
    logger.debug(f"Visualizing flight data from {json_path} with time window {start_time} to {end_time}")
    plot_flight_data(json_path, start_time, end_time, show_figures=answers['show_figures'])
    input("\nPress Enter to continue...")
    clear_screen()
    return True

def compare_multiple_launches_menu():
    """Handle the compare multiple launches menu option."""
    clear_screen()
    launch_folders = get_launch_folders()
    
    if not validate_available_launches(launch_folders):
        return True
    
    answers = prompt_for_comparison_options(launch_folders)
    
    if not validate_selected_launches(answers['launches']):
        return True
    
    execute_launch_comparison(
        answers['launches'], 
        answers['start_time'], 
        answers['end_time'], 
        answers['show_figures'],
        launch_folders
    )
    
    input("\nPress Enter to continue...")
    clear_screen()
    return True

def get_launch_folders():
    """Get available launch folders from results directory with full paths."""
    launches = []
    providers = get_results_providers()
    
    for provider in providers:
        rockets = get_results_rockets(provider)
        for rocket in rockets:
            launch_list = get_results_launches(provider, rocket)
            for launch_name, json_path in launch_list:
                # Create a display name that includes provider/rocket info
                display_name = f"{provider}/{rocket}/{launch_name}"
                launches.append((display_name, json_path))
    
    logger.debug(f"Found {len(launches)} launch folders for comparison")
    return launches

def validate_available_launches(launch_folders):
    """Validate that there are enough launch folders to compare."""
    if len(launch_folders) < 2:
        print("Need at least two launch folders in ./results directory to compare.")
        input("\nPress Enter to continue...")
        clear_screen()
        return False
    return True

def prompt_for_comparison_options(launch_folders):
    """Prompt user for comparison options."""
    # Extract display names for the choices
    display_names = [display_name for display_name, json_path in launch_folders]
    
    questions = [
        inquirer.Checkbox(
            'launches',
            message="Select the launches to compare (press space to select)",
            choices=display_names,
        ),
        inquirer.Text(
            'start_time', message="Start time in seconds (default: 0)", validate=validate_number),
        inquirer.Text(
            'end_time', message="End time in seconds (default: -1 for all data)", validate=validate_number),
        inquirer.Confirm(
            'show_figures', message="Display figures interactively?", default=True)
    ]
    return inquirer.prompt(questions)

def validate_selected_launches(selected_launches):
    """Validate that user selected enough launches to compare."""
    if len(selected_launches) < 2:
        print("Please select at least two launches to compare.")
        input("\nPress Enter to continue...")
        clear_screen()
        return False
    return True

def execute_launch_comparison(launches, start_time_input, end_time_input, show_figures, launch_folders):
    """Execute the launch comparison with the provided parameters."""
    # Map selected display names back to json paths
    selected_paths = []
    display_to_path = {display_name: json_path for display_name, json_path in launch_folders}
    
    for display_name in launches:
        if display_name in display_to_path:
            selected_paths.append(display_to_path[display_name])
        else:
            logger.warning(f"Could not find path for launch: {display_name}")
    
    if len(selected_paths) < 2:
        print("Error: Could not resolve paths for selected launches.")
        return
    
    start_time = int(start_time_input) if start_time_input else 0
    end_time = int(end_time_input) if end_time_input else -1
    
    logger.debug(f"Comparing launches: {', '.join(launches)}")
    logger.debug(f"Time window: {start_time} to {end_time}")
    
    compare_multiple_launches(start_time, end_time, *selected_paths, show_figures=show_figures)
