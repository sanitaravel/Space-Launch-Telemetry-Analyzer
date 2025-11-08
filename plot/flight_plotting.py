import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess
from .data_processing import load_and_clean_data, compute_acceleration, compute_g_force, prepare_fuel_data_columns
from .plot_utils import maximize_figure_window
from .engine_plotting import create_engine_timeline_plot, create_engine_performance_correlation
from .fuel_plotting import create_fuel_level_plot
from utils.constants import (ANALYZE_RESULTS_PLOT_PARAMS, FUEL_LEVEL_PLOT_PARAMS, 
                      FIGURE_SIZE, TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE, LABEL_FONT_SIZE, 
                      LEGEND_FONT_SIZE, TICK_FONT_SIZE, MARKER_SIZE, MARKER_ALPHA, 
                      LINE_WIDTH, LINE_ALPHA)
from utils import extract_launch_number
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Set seaborn style globally for all plots - slightly bigger font size
sns.set_theme(style="whitegrid", context="talk",
              palette="colorblind", font_scale=1.1)


def create_scatter_plot(df: pd.DataFrame, x: str, y: str, title: str, filename: str, label: str, 
                        x_axis: str, y_axis: str, folder: str, launch_number: str, show_figures: bool) -> None:
    """
    Create and save a scatter plot for the data using seaborn.

    Args:
        df (pd.DataFrame): The DataFrame containing the data.
        x (str): The column name for the x-axis.
        y (str): The column name for the original y-axis data.
        title (str): The title of the graph.
        filename (str): The filename to save the graph as.
        label (str): The label for the scatter plot.
        x_axis (str): The label for the x-axis.
        y_axis (str): The label for the y-axis.
        folder (str): The folder to save the graph in.
        launch_number (str): Launch number to include in the title
        show_figures (bool): Whether to display the figures.
    """
    # Add launch number to the beginning of the title
    title_with_launch = f"Launch {launch_number} - {title}"
    logger.info(f"Creating scatter plot: {title_with_launch}")
    
    # Create plots directory if it doesn't exist
    os.makedirs(folder, exist_ok=True)

    # Create figure (fullscreen)
    fig = plt.figure(figsize=FIGURE_SIZE)

    # Create scatter plot with seaborn
    data_count = df[y].notna().sum()
    logger.debug(f"Plotting {data_count} data points for {y}")
    
    scatter_plot = sns.scatterplot(x=x, y=y, data=df, label=f"{label}",
                                   s=MARKER_SIZE, alpha=MARKER_ALPHA, edgecolor=None)

    # Add trendline only for acceleration and g-force plots
    if 'acceleration' in y or 'g_force' in y:
        # Only use non-null values for the trendline
        valid_data = df[[x, y]].dropna()

        if len(valid_data) > 10:  # Only add trendline if we have enough data points
            logger.debug(f"Adding 10-point rolling window trendline")
            
            # Sort data by x-axis value to ensure proper rolling window calculation
            valid_data = valid_data.sort_values(by=x)

            # Use pandas rolling window (10 points) instead of LOWESS smoothing
            valid_data['trend'] = valid_data[y].rolling(window=10, center=True, min_periods=5).mean()

            # Plot the rolling average trendline
            plt.plot(valid_data[x], valid_data['trend'], color='crimson',
                     linewidth=LINE_WIDTH, label=f"{label} (10-point Rolling Average)")

    # Set labels with consistent styling
    plt.xlabel(x_axis, fontsize=LABEL_FONT_SIZE)
    plt.ylabel(y_axis, fontsize=LABEL_FONT_SIZE)
    plt.title(title_with_launch, fontsize=TITLE_FONT_SIZE)
    plt.tick_params(labelsize=TICK_FONT_SIZE)

    # Add legend with improved visibility
    plt.legend(frameon=True, fontsize=LEGEND_FONT_SIZE)

    # Save with high quality
    save_path = f"{folder}/{filename}"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved scatter plot to {save_path}")

    # If showing figures, add to interactive viewer instead of displaying
    if show_figures:
        # Check if we're in interactive mode (viewer exists in the caller's context)
        from inspect import currentframe, getouterframes
        frame = currentframe().f_back
        if 'viewer' in frame.f_locals:
            # Add the figure to the viewer
            frame.f_locals['viewer'].add_figure(fig, title_with_launch)
        else:
            # Fall back to regular display
            maximize_figure_window()
            plt.show()
    else:
        plt.close(fig)


def plot_flight_data(json_path: str, start_time: int = 0, end_time: int = -1, show_figures: bool = True) -> None:
    """
    Plot flight data from a JSON file with optional time window limits.

    Args:
        json_path (str): Path to the JSON file containing the flight data.
        start_time (int): Minimum time in seconds to include in plots. Default is 0.
        end_time (int): Maximum time in seconds to include in plots. Use -1 for all data.
        show_figures (bool): Whether to show figures or just save them.
    """
    logger.info(f"Plotting flight data from {json_path} (time window: {start_time}s to {end_time if end_time != -1 else 'end'}s)")
    
    df = load_and_clean_data(json_path)
    if df.empty:
        logger.error("DataFrame is empty, cannot generate plots")
        return  # Exit if the DataFrame is empty due to JSON error

    # Create interactive viewer if showing figures
    launch_number = extract_launch_number(json_path)
    viewer = None
    if show_figures:
        from .interactive_viewer import show_plots_interactively
        viewer = show_plots_interactively(f"Launch {launch_number} - Flight Data Visualization")

    # Filter data by time window
    original_count = len(df)
    df = df[df['real_time_seconds'] >= start_time]
    if end_time != -1:
        df = df[df['real_time_seconds'] <= end_time]
    logger.info(f"Using {len(df)} of {original_count} data points after time filtering")

    # Detect available vehicles
    from .data_processing import detect_vehicles
    vehicles = detect_vehicles(df)
    
    # Calculate acceleration and G-forces for all vehicles
    for vehicle in vehicles:
        speed_col = f'{vehicle}.speed' if f'{vehicle}.speed' in df.columns else f'{vehicle}_speed'
        if speed_col in df.columns:
            df[f'{vehicle}_acceleration'] = compute_acceleration(df, speed_col)
            df[f'{vehicle}_g_force'] = compute_g_force(df[f'{vehicle}_acceleration'])
    
    # Ensure fuel data columns exist and have proper names
    df = prepare_fuel_data_columns(df)
    
    # Determine the folder name based on the launch number
    folder = os.path.dirname(json_path)
    logger.info(f"Creating plots for launch {launch_number} in folder {folder}")
    
    # Create fuel level plots for available vehicles
    fuel_plot_count = 0
    for vehicle in vehicles:
        lox_col = f"{vehicle}.fuel.lox.fullness"
        ch4_col = f"{vehicle}.fuel.ch4.fullness"
        if lox_col in df.columns and ch4_col in df.columns:
            # Create fuel level plot for this vehicle
            params = (
                'real_time_seconds',
                [lox_col, ch4_col],
                f'{vehicle.title()} Fuel Levels',
                f'{vehicle}_fuel_levels.png',
                ['LOX', 'CH4'],
                'Mission Time (seconds)',
                'Tank Fullness (%)',
                folder,
                launch_number,
                show_figures
            )
            create_fuel_level_plot(df, *params)
            fuel_plot_count += 1
    
    logger.info(f"Created {fuel_plot_count} fuel level plots")
    
    # Create engine timeline plots for available vehicles
    for vehicle in vehicles:
        if any(col.startswith(f"{vehicle}.") and "active" in col for col in df.columns):
            create_engine_timeline_plot(df, folder, launch_number, show_figures)
            break  # Only create once, as it handles all vehicles
    
    # Create correlation plots between engine activity and performance for each vehicle
    for vehicle in vehicles:
        if any(col.startswith(f"{vehicle}.") and "active" in col for col in df.columns):
            create_engine_performance_correlation(df, vehicle, folder, launch_number, show_figures)
    
    # Create standard plots based on detected vehicles
    plot_count = 0
    for vehicle in vehicles:
        # Speed plot
        speed_col = f'{vehicle}.speed'
        if speed_col in df.columns:
            params = (
                'real_time_seconds', speed_col,
                f'{vehicle.title()} Velocity',
                f'{vehicle}_velocity.png',
                vehicle.title(), 'Mission Time (seconds)', 'Velocity (km/h)',
                folder, launch_number, show_figures
            )
            create_scatter_plot(df, *params)
            plot_count += 1
        
        # Altitude plot
        alt_col = f'{vehicle}.altitude'
        if alt_col in df.columns:
            params = (
                'real_time_seconds', alt_col,
                f'{vehicle.title()} Altitude',
                f'{vehicle}_altitude.png',
                vehicle.title(), 'Mission Time (seconds)', 'Altitude (km)',
                folder, launch_number, show_figures
            )
            create_scatter_plot(df, *params)
            plot_count += 1
        
        # Acceleration plot
        accel_col = f'{vehicle}_acceleration'
        if accel_col in df.columns:
            params = (
                'real_time_seconds', accel_col,
                f'{vehicle.title()} Acceleration',
                f'{vehicle}_acceleration.png',
                vehicle.title(), 'Mission Time (seconds)', 'Acceleration (m/s²)',
                folder, launch_number, show_figures
            )
            create_scatter_plot(df, *params)
            plot_count += 1
        
        # G-force plot
        gforce_col = f'{vehicle}_g_force'
        if gforce_col in df.columns:
            params = (
                'real_time_seconds', gforce_col,
                f'{vehicle.title()} G-Force',
                f'{vehicle}_g_force.png',
                vehicle.title(), 'Mission Time (seconds)', 'G-Force (g)',
                folder, launch_number, show_figures
            )
            create_scatter_plot(df, *params)
            plot_count += 1
    
    logger.info(f"Created {plot_count} standard plots")
    logger.info(f"Completed all plots for launch {launch_number}")
    
    # Show the interactive viewer if requested
    if show_figures and viewer:
        viewer.show()
