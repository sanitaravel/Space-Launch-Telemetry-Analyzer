"""
Main entry point for the Starship Analyzer application.
"""
import argparse
import io
import logging
import cProfile
import pstats
from typing import Optional

from utils.logger import start_new_session, get_logger, set_global_log_level
from utils.terminal import clear_screen
from ui import display_menu
from utils.suppress_warnings import suppress_ffmpeg_warnings

# Call this early in your application startup
suppress_ffmpeg_warnings()

# Ensure watermarking is applied globally for all plots
import utils.watermark

# Initialize logger
logger = get_logger(__name__)

# Global debug state - kept in main as requested
DEBUG_MODE = False

def toggle_debug_mode():
    """Toggle debug mode on/off and set appropriate log levels."""
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    
    if DEBUG_MODE:
        logger.info("Debug mode enabled")
        set_global_log_level(logging.DEBUG)
    else:
        logger.info("Debug mode disabled")
        set_global_log_level(logging.INFO)
    
    return True

def main() -> None:
    """
    Main function to handle the step-by-step menu and run the application.
    """
    # Clear screen at startup
    clear_screen()
    
    # Start a new logging session
    root_logger = start_new_session()
    logger.info("Starting Starship Analyzer application")
    
    try:
        menu_result = True
        while menu_result:
            debug_status = "Enabled" if DEBUG_MODE else "Disabled"
            menu_result = display_menu(debug_status)
            
            # Special return value to toggle debug mode
            if menu_result == "TOGGLE_DEBUG":
                toggle_debug_mode()
                menu_result = True
                
        logger.info("Application exiting normally")
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        print(f"An error occurred: {str(e)}")
    finally:
        logger.info("Application shutdown complete")

def _run_with_cprofile(output_path: str, print_top: bool, top_n: int = 50) -> None:
    """Run the main() under cProfile and save stats to output_path.

    If print_top is True, print the top_n functions by cumulative time to stdout.
    """
    profiler = cProfile.Profile()
    try:
        profiler.enable()
        main()
    finally:
        profiler.disable()
        try:
            profiler.dump_stats(output_path)
            print(f"Profile saved to: {output_path}")
        except Exception as e:
            print(f"Failed to write profile to {output_path}: {e}")

        if print_top:
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats("cumtime")
            ps.print_stats(top_n)
            print(s.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Starship Analyzer")
    parser.add_argument(
        "--profile",
        "-p",
        nargs="?",
        const="profile.stats",
        default=None,
        help="Enable cProfile and write stats to the given file (default: profile.stats if flag provided without path)",
    )
    parser.add_argument(
        "--profile-print",
        action="store_true",
        help="If set when profiling, print top functions to stdout after run",
    )
    parser.add_argument(
        "--profile-top",
        type=int,
        default=50,
        help="Number of top functions to print when --profile-print is used (default: 50)",
    )

    args = parser.parse_args()

    if args.profile:
        out = args.profile if isinstance(args.profile, str) and args.profile != "profile.stats" else "profile.stats"
        _run_with_cprofile(out, args.profile_print, args.profile_top)
    else:
        main()
