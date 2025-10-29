"""
Video processing menu and related functionality.
"""
import inquirer
from utils.logger import get_logger
from utils.terminal import clear_screen
from utils.validators import validate_number, validate_positive_number
from utils.video_utils import get_video_files_from_flight_recordings, display_video_info
from processing import process_video_frame, iterate_through_frames
from ocr.roi_manager import set_default_manager_config, get_default_manager
from pathlib import Path

logger = get_logger(__name__)

def video_processing_menu():
    """Submenu for video processing options."""
    from main import DEBUG_MODE  # Import here to avoid circular imports
    
    clear_screen()
    debug_status = "Enabled" if DEBUG_MODE else "Disabled"
    
    questions = [
        inquirer.List(
            'action',
            message="Video Processing Options:",
            choices=[
                'Process random video frame',
                'Process complete video',
                'Back to main menu'
            ],
        ),
    ]
    
    answers = inquirer.prompt(questions)
    
    logger.debug(f"Video processing menu: User selected: {answers['action']}")
    
    if answers['action'] == 'Process random video frame':
        process_random_frame()
        return video_processing_menu()
    elif answers['action'] == 'Process complete video':
        process_complete_video()
        return video_processing_menu()
    elif answers['action'] == 'Back to main menu':
        clear_screen()
        return True
    
    clear_screen()
    return True

def process_random_frame():
    """Handle the process random video frame menu option."""
    from main import DEBUG_MODE  # Import here to avoid circular imports
    
    clear_screen()
    video_files = get_video_files_from_flight_recordings()
    if not video_files:
        return True
    
    logger.debug("Starting random frame processing")
    
    # Allow user to choose ROI config before processing
    select_roi_config_menu()

    # First, get the video path
    video_question = [
        inquirer.List(
            'video_path',
            message="Select a video file",
            choices=video_files,
        )
    ]
    video_answer = inquirer.prompt(video_question)
    
    # Display video information
    display_video_info(video_answer['video_path'])
    
    # Continue with other questions
    questions = [
        inquirer.Confirm(
            'display_rois', message="Display ROIs?", default=False),
        inquirer.Confirm(
            'debug', message="Enable debug prints?", default=False),
        inquirer.Text(
            'start_time', message="Start time in seconds (default: 0)", validate=validate_number),
        inquirer.Text(
            'end_time', message="End time in seconds (default: -1 for all)", validate=validate_number),
    ]
    answers = inquirer.prompt(questions)
    answers['video_path'] = video_answer['video_path']  # Combine answers
    
    start_time = int(answers['start_time']) if answers['start_time'] else 0
    end_time = int(answers['end_time']) if answers['end_time'] else -1

    # Convert seconds to frames using video FPS
    from utils.video_utils import get_video_fps
    fps = get_video_fps(answers['video_path'])
    start_frame = None
    end_frame = None
    if fps:
        start_frame = int(start_time * fps)
        end_frame = -1 if end_time == -1 else int(end_time * fps)

    logger.debug(f"Processing random frame from {answers['video_path']} with start_frame={start_frame}, end_frame={end_frame}")
    process_video_frame(
        answers['video_path'], answers['display_rois'], answers['debug'] or DEBUG_MODE, start_frame, end_frame)
    input("\nPress Enter to continue...")
    clear_screen()
    return True

def get_launch_providers():
    """Get list of available launch providers."""
    flight_recordings_folder = Path('flight_recordings')
    if not flight_recordings_folder.exists():
        return []
    return [d.name for d in flight_recordings_folder.iterdir() if d.is_dir()]

def get_rockets(provider):
    """Get list of available rockets for a provider."""
    provider_path = Path('flight_recordings') / provider
    if not provider_path.exists():
        return []
    return [d.name for d in provider_path.iterdir() if d.is_dir()]

def get_flights(provider, rocket):
    """Get list of available flights (video files) for a provider and rocket."""
    rocket_path = Path('flight_recordings') / provider / rocket
    if not rocket_path.exists():
        return []
    video_files = []
    for file in rocket_path.iterdir():
        if file.is_file() and file.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            video_files.append((file.name, str(file.relative_to('.'))))
    return video_files

def select_video_file():
    """Select a video file from available flight recordings."""
    providers = get_launch_providers()
    if not providers:
        print("No launch providers found.")
        return None
    
    provider_question = [
        inquirer.List(
            'provider',
            message="Select a launch provider",
            choices=providers,
        )
    ]
    provider_answer = inquirer.prompt(provider_question)
    provider = provider_answer['provider']
    
    rockets = get_rockets(provider)
    if not rockets:
        print(f"No rockets found for provider {provider}.")
        return None
    
    rocket_question = [
        inquirer.List(
            'rocket',
            message="Select a rocket",
            choices=rockets,
        )
    ]
    rocket_answer = inquirer.prompt(rocket_question)
    rocket = rocket_answer['rocket']
    
    flights = get_flights(provider, rocket)
    if not flights:
        print(f"No flights found for {provider}/{rocket}.")
        return None
    
    flight_question = [
        inquirer.List(
            'flight',
            message="Select a flight",
            choices=[name for name, path in flights],
        )
    ]
    flight_answer = inquirer.prompt(flight_question)
    selected_name = flight_answer['flight']
    
    for name, path in flights:
        if name == selected_name:
            return path
    
    return None

def get_processing_parameters():
    """Get processing parameters from user."""
    questions = [
        inquirer.Text('launch_number', message="Launch number",
                    validate=validate_number),
        inquirer.Text('batch_size', 
                     message="Batch size for processing (default: 10)", 
                     validate=validate_positive_number),
        inquirer.Text('sample_rate', 
                     message="Sample rate (process every Nth frame, default: 1)", 
                     validate=validate_positive_number),
        # Add border options
        inquirer.List(
            'border_type',
            message="How would you like to specify processing borders?",
            choices=['Time-based (seconds)', 'Frame-based', 'Process entire video'],
            default='Process entire video'
        )
    ]
    return inquirer.prompt(questions)

def get_time_based_borders():
    """Get time-based processing borders from user."""
    time_questions = [
        inquirer.Text(
            'start_time', 
            message="Start time in seconds (default: 0)", 
            validate=validate_number
        ),
        inquirer.Text(
            'end_time', 
            message="End time in seconds (default: process to end)", 
            validate=validate_number
        )
    ]
    time_answers = inquirer.prompt(time_questions)
    
    start_time = float(time_answers['start_time']) if time_answers['start_time'] else None
    end_time = float(time_answers['end_time']) if time_answers['end_time'] else None
    
    return start_time, end_time

def get_frame_based_borders():
    """Get frame-based processing borders from user."""
    frame_questions = [
        inquirer.Text(
            'start_frame', 
            message="Start frame number (default: 0)", 
            validate=validate_number
        ),
        inquirer.Text(
            'end_frame', 
            message="End frame number (default: process to end)", 
            validate=validate_number
        )
    ]
    frame_answers = inquirer.prompt(frame_questions)
    
    start_frame = int(frame_answers['start_frame']) if frame_answers['start_frame'] else 0
    end_frame = int(frame_answers['end_frame']) if frame_answers['end_frame'] else None
    
    return start_frame, end_frame

# ...process_video_with_parameters removed; its logic is now in process_complete_video

def process_video_with_parameters(video_path, launch_number, batch_size, sample_rate, 
                                 start_time=None, end_time=None, start_frame=None, end_frame=None):
    """Compatibility wrapper: convert time borders to frames and call iterate_through_frames."""
    from main import DEBUG_MODE  # Import here to avoid circular imports

    logger.debug(f"Processing complete video {video_path} with launch_number={launch_number}, "
                f"batch_size={batch_size}, sample_rate={sample_rate}")
    logger.debug(f"Borders: start_time={start_time}, end_time={end_time}, "
                f"start_frame={start_frame}, end_frame={end_frame}")

    # If time-based borders were provided, convert them to frame numbers using video FPS
    converted_start_frame = start_frame
    converted_end_frame = end_frame
    if start_frame is None and start_time is not None:
        # Need to get fps to convert time to frames
        from utils.video_utils import get_video_fps
        fps = get_video_fps(video_path)
        if fps:
            converted_start_frame = int(start_time * fps)
    if end_frame is None and end_time is not None:
        from utils.video_utils import get_video_fps
        fps = get_video_fps(video_path)
        if fps:
            converted_end_frame = int(end_time * fps)

    iterate_through_frames(
        video_path, int(launch_number), debug=DEBUG_MODE, 
        batch_size=batch_size, sample_rate=sample_rate,
        start_frame=converted_start_frame, end_frame=converted_end_frame)

def process_complete_video():
    """Handle the process complete video menu option."""
    from main import DEBUG_MODE  # Import here to avoid circular imports
    
    clear_screen()
    video_path = select_video_file()
    if not video_path:
        return True
    
    logger.debug("Starting complete video processing")
    
    # Display video information
    display_video_info(video_path)
    
    # Allow user to choose ROI config before processing
    select_roi_config_menu()

    # Get processing parameters
    answers = get_processing_parameters()
    
    batch_size = int(answers['batch_size']) if answers['batch_size'] else 10
    sample_rate = int(answers['sample_rate']) if answers['sample_rate'] else 1
    
    # Initialize borders
    start_time = None
    end_time = None
    start_frame = None
    end_frame = None
    
    # Get border information based on user's choice
    if answers['border_type'] == 'Time-based (seconds)':
        # Get times from user and convert to frame indices immediately using video FPS
        start_time, end_time = get_time_based_borders()
        try:
            from utils.video_utils import get_video_fps
            fps = get_video_fps(video_path)
            if fps:
                # start_time is always numeric (default 0); end_time may be None meaning until end
                start_frame = int(start_time * fps) if start_time is not None else None
                end_frame = None if end_time is None else int(end_time * fps)
            else:
                logger.warning('Could not determine video FPS; time-based borders will be handled later')
        except Exception:
            logger.exception('Error converting time borders to frames')
    elif answers['border_type'] == 'Frame-based':
        start_frame, end_frame = get_frame_based_borders()
    
    # After selecting ROI config, read its time_unit and per-ROI spans to set sensible defaults
    try:
        manager = get_default_manager()
        config_time_unit = manager.time_unit
        rois_list = manager.list_rois()
        # rois_list contains start_frame/end_frame because ROIManager parses start_time into start_frame
        starts = [r.get('start_frame') for r in rois_list if r.get('start_frame') is not None]
        ends = [r.get('end_frame') for r in rois_list if r.get('end_frame') is not None]
        # If the config uses seconds, those values in the json were seconds and ROIManager converted them to frames
        # but to be safe, if time_unit == 'seconds' convert using video fps
        config_start_frame = None
        config_end_frame = None
        if starts:
            config_start_frame = min(starts)
        if ends:
            config_end_frame = max(ends)
        # If config time unit is seconds, convert seconds->frames using video fps
        if config_time_unit == 'seconds':
            from utils.video_utils import get_video_fps
            fps = get_video_fps(video_path)
            if fps:
                if config_start_frame is not None:
                    config_start_frame = int(config_start_frame * fps)
                if config_end_frame is not None:
                    config_end_frame = int(config_end_frame * fps)
        logger.debug(f"Loaded ROI config: time_unit={config_time_unit}, start_frame={config_start_frame}, end_frame={config_end_frame}")
        # Apply defaults only when user didn't supply any borders
        if start_frame is None and config_start_frame is not None:
            start_frame = config_start_frame
        if end_frame is None and config_end_frame is not None:
            end_frame = config_end_frame
    except Exception:
        logger.exception("Failed to read ROI manager defaults after selecting config")

    # Inline conversion from time to frames for user-specified time borders
    converted_start_frame = start_frame
    converted_end_frame = end_frame
    if start_frame is None and start_time is not None:
        from utils.video_utils import get_video_fps
        fps = get_video_fps(video_path)
        if fps:
            converted_start_frame = int(start_time * fps)
    if end_frame is None and end_time is not None:
        from utils.video_utils import get_video_fps
        fps = get_video_fps(video_path)
        if fps:
            converted_end_frame = int(end_time * fps)

    logger.info(f"Using frames: {converted_start_frame} - {converted_end_frame}")
    iterate_through_frames(
        video_path, int(answers['launch_number']), debug=DEBUG_MODE,
        batch_size=batch_size, sample_rate=sample_rate,
        start_frame=converted_start_frame, end_frame=converted_end_frame
    )
    
    input("\nPress Enter to continue...")
    clear_screen()
    return True


def select_roi_config_menu():
    """Prompt the user to choose an ROI config from the `configs` folder and set it as default.

    If the user cancels or no configs are found, nothing changes.
    """
    try:
        configs_dir = Path('configs')
        if not configs_dir.exists():
            return None

        json_files = sorted([p.name for p in configs_dir.glob('*.json')])
        if not json_files:
            return None

        choices = json_files + ['Use current/default']
        question = [
            inquirer.List('config', message='Select ROI config (affects subsequent processing):', choices=choices)
        ]
        ans = inquirer.prompt(question)
        if not ans:
            return None
        if ans['config'] == 'Use current/default':
            return None

        selected = configs_dir / ans['config']
        # Set global default manager to use this config
        set_default_manager_config(str(selected))
        return str(selected)
    except Exception:
        logger.exception('Failed to set ROI config from menu')
        return None
