import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess
from .data_processing import load_and_clean_data, compute_acceleration, compute_g_force, prepare_fuel_data_columns
from utils.constants import (ANALYZE_RESULTS_PLOT_PARAMS, FUEL_LEVEL_PLOT_PARAMS, 
                      FIGURE_SIZE, TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE, LABEL_FONT_SIZE, 
                      LEGEND_FONT_SIZE, TICK_FONT_SIZE, MARKER_SIZE, MARKER_ALPHA, 
                      LINE_WIDTH, LINE_ALPHA, ENGINE_TIMELINE_PARAMS, 
                      ENGINE_PERFORMANCE_PARAMS)
from utils import extract_launch_number
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Set seaborn style globally for all plots - slightly bigger font size
sns.set_theme(style="whitegrid", context="talk",
              palette="colorblind", font_scale=1.1)


def maximize_figure_window():
    """
    Maximize the current figure window to take all available screen space without going full screen.
    This preserves window decorations and taskbar visibility.
    """
    try:
        # Get the figure manager
        fig_manager = plt.get_current_fig_manager()
        
        # Try different approaches based on backend, prioritizing maximize over full screen
        if hasattr(fig_manager, 'window') and hasattr(fig_manager.window, 'showMaximized'):
            # Qt backend (most common)
            fig_manager.window.showMaximized()
        elif hasattr(fig_manager, 'window') and hasattr(fig_manager.window, 'state') and hasattr(fig_manager.window, 'tk'):
            # TkAgg backend
            fig_manager.window.state('zoomed')  # Windows 'zoomed' state
        elif hasattr(fig_manager, 'frame') and hasattr(fig_manager.frame, 'Maximize'):
            # WX backend
            fig_manager.frame.Maximize(True)
        elif hasattr(fig_manager, 'window') and hasattr(fig_manager.window, 'maximize'):
            # Other backends with maximize function
            fig_manager.window.maximize()
        elif hasattr(fig_manager, 'full_screen_toggle'):
            # Only use full screen as a last resort
            logger.debug("Using full_screen_toggle as fallback")
            fig_manager.full_screen_toggle()
        elif hasattr(fig_manager, 'resize'):
            # MacOSX backend
            fig_manager.resize(*fig_manager.window.get_screen().get_size())
    except Exception as e:
        logger.debug(f"Could not maximize window: {str(e)}")


def create_engine_group_plot(df: pd.DataFrame, vehicle: str, folder: str, launch_number: str, show_figures: bool = True):
    """
    Create a plot for a specific engine group (Superheavy or Starship).
    
    Args:
        df (pd.DataFrame): DataFrame with processed engine data
        vehicle (str): Either "superheavy" or "starship"
        folder (str): Folder to save the plot
        launch_number (str): Launch number to include in the title
        show_figures (bool): Whether to display the figures
    """
    vehicle_params = ENGINE_TIMELINE_PARAMS[vehicle]
    title = f"Launch {launch_number} - {vehicle_params['title']}"
    logger.info(f"Creating engine plot: {title}")
    
    # Create figure (fullscreen)
    fig = plt.figure(figsize=FIGURE_SIZE)
    
    # Plot engine data
    for group in vehicle_params["groups"]:
        sns.lineplot(x='real_time_seconds', y=group["column"], data=df,
                    label=group["label"], marker='o', 
                    alpha=MARKER_ALPHA, color=group["color"],
                    linewidth=LINE_WIDTH if "All" in group["label"] else LINE_WIDTH-0.5)

    plt.title(title, fontsize=TITLE_FONT_SIZE)
    plt.xlabel(ENGINE_TIMELINE_PARAMS["xlabel"], fontsize=LABEL_FONT_SIZE)
    plt.ylabel(vehicle_params["ylabel"], fontsize=LABEL_FONT_SIZE)
    plt.ylim(*vehicle_params["ylim"])
    plt.tick_params(labelsize=TICK_FONT_SIZE)
    plt.legend(fontsize=LEGEND_FONT_SIZE)
    plt.tight_layout()

    # Save figure
    os.makedirs(folder, exist_ok=True)
    vehicle_name = "superheavy" if vehicle == "superheavy" else "starship"
    save_path = f"{folder}/{vehicle_name}_engine_timeline.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved {vehicle} engine plot to {save_path}")

    # If we're showing figures, check for interactive viewer
    if show_figures:
        # Check if we're in interactive mode (viewer exists in the caller's context)
        from inspect import currentframe, getouterframes
        frame = currentframe().f_back
        if 'viewer' in frame.f_locals:
            frame.f_locals['viewer'].add_figure(fig, title)
        else:
            # Fall back to regular display
            maximize_figure_window()
            plt.show()
    else:
        plt.close(fig)


def create_engine_timeline_plot(df: pd.DataFrame, folder: str, launch_number: str, show_figures: bool = True):
    """
    Create separate engine activity plots for Superheavy and Starship.

    Args:
        df (pd.DataFrame): DataFrame with processed engine data
        folder (str): Folder to save the plot
        launch_number (str): Launch number to include in the title
        show_figures (bool): Whether to display the figures
    """
    logger.info(f"Creating engine timeline plots for Launch {launch_number}")
    
    # Create separate plots for Superheavy and Starship
    create_engine_group_plot(df, "superheavy", folder, launch_number, show_figures)
    create_engine_group_plot(df, "starship", folder, launch_number, show_figures)


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


def create_engine_performance_correlation(df: pd.DataFrame, vehicle: str, folder: str, launch_number: str, show_figures: bool = True) -> None:
    """
    Create a plot showing correlation between engine activity and vehicle performance using seaborn.
    
    Args:
        df (pd.DataFrame): DataFrame with processed data
        vehicle (str): Either "superheavy" or "starship"
        folder (str): Folder to save the plot
        launch_number (str): Launch number to include in the title
        show_figures (bool): Whether to display the figures
    """
    params = ENGINE_PERFORMANCE_PARAMS[vehicle]
    
    # Add launch number to the beginning of the title
    title_with_launch = f"Launch {launch_number} - {params['title']}"
    logger.info(f"Creating engine performance correlation plot: {title_with_launch}")
    
    # Create figure (fullscreen)
    fig = plt.figure(figsize=FIGURE_SIZE)

    # Create advanced scatter plot with seaborn
    data_count = df[[params['x_col'], params['y_col'], params['color_col']]].dropna().shape[0]
    logger.debug(f"Plotting {data_count} data points for correlation")
    
    scatter = sns.scatterplot(
        x=params['x_col'],
        y=params['y_col'],
        hue=params['color_col'],
        size=params['color_col'],
        sizes=(MARKER_SIZE, MARKER_SIZE*4),  # Range of point sizes
        palette=params['cmap'],     # Use colormap
        alpha=MARKER_ALPHA,  # Transparency
        data=df           # Data source
    )

    # Add a legend with custom title
    legend = scatter.legend(title=params['color_label'], fontsize=LEGEND_FONT_SIZE)
    plt.setp(legend.get_title(), fontsize=LEGEND_FONT_SIZE+1)

    # Add labels and title with consistent styling
    plt.xlabel(params['x_label'], fontsize=LABEL_FONT_SIZE)
    plt.ylabel(params['y_label'], fontsize=LABEL_FONT_SIZE)
    plt.title(title_with_launch, fontsize=TITLE_FONT_SIZE)
    plt.tick_params(labelsize=TICK_FONT_SIZE)

    # Save figure with high quality
    os.makedirs(folder, exist_ok=True)
    save_path = f"{folder}/{params['filename']}"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved correlation plot to {save_path}")

    # If showing figures, check for interactive viewer
    if show_figures:
        # Check if we're in interactive mode (viewer exists in the caller's context)
        from inspect import currentframe, getouterframes
        frame = currentframe().f_back
        if 'viewer' in frame.f_locals:
            frame.f_locals['viewer'].add_figure(fig, title_with_launch)
        else:
            # Fall back to regular display
            maximize_figure_window()
            plt.show()
    else:
        plt.close(fig)


def create_fuel_level_plot(df: pd.DataFrame, x: str, y_cols: list, title: str, filename: str, 
                           labels: list, x_axis: str, y_axis: str, folder: str, 
                           launch_number: str, show_figures: bool) -> None:
    """
    Create and save a fuel level plot showing multiple fuel types (LOX and CH4) over time.

    Args:
        df (pd.DataFrame): The DataFrame containing the data.
        x (str): The column name for the x-axis (usually time).
        y_cols (list): List of column names for the fuel levels.
        title (str): The title of the graph.
        filename (str): The filename to save the graph as.
        labels (list): Labels for each fuel type.
        x_axis (str): The label for the x-axis.
        y_axis (str): The label for the y-axis.
        folder (str): The folder to save the graph in.
        launch_number (str): Launch number to include in the title.
        show_figures (bool): Whether to display the figures.
    """
    title_with_launch = f"Launch {launch_number} - {title}"
    logger.info(f"Creating fuel level plot: {title_with_launch}")
    
    # Create plots directory if it doesn't exist
    os.makedirs(folder, exist_ok=True)

    # Create figure
    fig = plt.figure(figsize=FIGURE_SIZE)
    
    # Create a color palette for consistent colors
    colors = sns.color_palette("husl", len(y_cols))
    
    # Plot each fuel type
    for i, (y_col, label, color) in enumerate(zip(y_cols, labels, colors)):
        # Count valid data points
        data_count = df[y_col].notna().sum()
        logger.debug(f"Plotting {data_count} data points for {label}")
        
        # Plot with larger markers and line width for visibility
        sns.lineplot(
            x=x, 
            y=y_col, 
            data=df, 
            label=f"{label}", 
            marker='o', 
            markersize=MARKER_SIZE//2,
            linewidth=LINE_WIDTH, 
            alpha=LINE_ALPHA, 
            color=color
        )
    
    # Set y-axis range to 0-100% for consistency
    plt.ylim(0, 100)
    
    # Add grid for better readability
    plt.grid(True, alpha=0.3)
    
    # Set labels with consistent styling
    plt.xlabel(x_axis, fontsize=LABEL_FONT_SIZE)
    plt.ylabel(y_axis, fontsize=LABEL_FONT_SIZE)
    plt.title(title_with_launch, fontsize=TITLE_FONT_SIZE)
    plt.tick_params(labelsize=TICK_FONT_SIZE)
    
    # Add legend with improved visibility
    plt.legend(frameon=True, fontsize=LEGEND_FONT_SIZE)
    
    # Tight layout for better spacing
    plt.tight_layout()

    # Save with high quality
    save_path = f"{folder}/{filename}"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved fuel level plot to {save_path}")

    # If showing figures, add to interactive viewer instead of displaying
    if show_figures:
        # Check if we're in interactive mode (viewer exists in the caller's context)
        from inspect import currentframe, getouterframes
        frame = currentframe().f_back
        if 'viewer' in frame.f_locals:
            frame.f_locals['viewer'].add_figure(fig, title_with_launch)
        else:
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

    # Set all Superheavy's data to None after 7 minutes and 30 seconds
    seven_minutes = 7 * 60 + 30  # 7 minutes and 30 seconds in seconds
    logger.debug(f"Nullifying Superheavy data after {seven_minutes}s (post-separation)")
    
    # Check which column naming scheme is used and set values accordingly
    speed_col = 'superheavy.speed' if 'superheavy.speed' in df.columns else 'superheavy_speed'
    alt_col = 'superheavy.altitude' if 'superheavy.altitude' in df.columns else 'superheavy_altitude'
    nullified_count = df[df['real_time_seconds'] > seven_minutes].shape[0]
    df.loc[df['real_time_seconds'] > seven_minutes, [speed_col, alt_col]] = None
    logger.debug(f"Nullified {nullified_count} data points for Superheavy after separation")
    
    # Make sure to use the correct column names
    sh_speed_col = 'superheavy.speed' if 'superheavy.speed' in df.columns else 'superheavy_speed'
    ss_speed_col = 'starship.speed' if 'starship.speed' in df.columns else 'starship_speed'
    
    df['superheavy_acceleration'] = compute_acceleration(df, sh_speed_col)
    df['starship_acceleration'] = compute_acceleration(df, ss_speed_col)

    # Calculate G-forces
    df['superheavy_g_force'] = compute_g_force(df['superheavy_acceleration'])
    df['starship_g_force'] = compute_g_force(df['starship_acceleration'])
    
    # Ensure fuel data columns exist and have proper names
    df = prepare_fuel_data_columns(df)
    
    # Determine the folder name based on the launch number
    folder = os.path.join("results", f"launch_{launch_number}")
    logger.info(f"Creating plots for launch {launch_number} in folder {folder}")
    
    # Create fuel level plots
    logger.info(f"Creating {len(FUEL_LEVEL_PLOT_PARAMS)} fuel level plots")
    for params in FUEL_LEVEL_PLOT_PARAMS:
        create_fuel_level_plot(df, *params, folder, launch_number, show_figures)
    
    # Create engine timeline plots - create separately and add to viewer
    # Superheavy engine plot
    logger.info(f"Creating engine timeline plots for Launch {launch_number}")
    
    # Create Superheavy engine plot
    fig_sh = plt.figure(figsize=FIGURE_SIZE)
    vehicle_params = ENGINE_TIMELINE_PARAMS["superheavy"]
    for group in vehicle_params["groups"]:
        sns.lineplot(x='real_time_seconds', y=group["column"], data=df,
                    label=group["label"], marker='o', 
                    alpha=MARKER_ALPHA, color=group["color"],
                    linewidth=LINE_WIDTH if "All" in group["label"] else LINE_WIDTH-0.5)
    plt.title(f"Launch {launch_number} - {vehicle_params['title']}", fontsize=TITLE_FONT_SIZE)
    plt.xlabel(ENGINE_TIMELINE_PARAMS["xlabel"], fontsize=LABEL_FONT_SIZE)
    plt.ylabel(vehicle_params["ylabel"], fontsize=LABEL_FONT_SIZE)
    plt.ylim(*vehicle_params["ylim"])
    plt.tick_params(labelsize=TICK_FONT_SIZE)
    plt.legend(fontsize=LEGEND_FONT_SIZE)
    plt.tight_layout()
    
    # Save figure
    os.makedirs(folder, exist_ok=True)
    plt.savefig(f"{folder}/superheavy_engine_timeline.png", dpi=300, bbox_inches='tight')
    
    # Add to viewer if showing figures
    if show_figures and viewer:
        viewer.add_figure(fig_sh, f"Launch {launch_number} - {vehicle_params['title']}")
    plt.close(fig_sh)
    
    # Create Starship engine plot
    fig_ss = plt.figure(figsize=FIGURE_SIZE)
    vehicle_params = ENGINE_TIMELINE_PARAMS["starship"]
    for group in vehicle_params["groups"]:
        sns.lineplot(x='real_time_seconds', y=group["column"], data=df,
                    label=group["label"], marker='o', 
                    alpha=MARKER_ALPHA, color=group["color"],
                    linewidth=LINE_WIDTH if "All" in group["label"] else LINE_WIDTH-0.5)
    plt.title(f"Launch {launch_number} - {vehicle_params['title']}", fontsize=TITLE_FONT_SIZE)
    plt.xlabel(ENGINE_TIMELINE_PARAMS["xlabel"], fontsize=LABEL_FONT_SIZE)
    plt.ylabel(vehicle_params["ylabel"], fontsize=LABEL_FONT_SIZE)
    plt.ylim(*vehicle_params["ylim"])
    plt.tick_params(labelsize=TICK_FONT_SIZE)
    plt.legend(fontsize=LEGEND_FONT_SIZE)
    plt.tight_layout()
    
    # Save figure
    plt.savefig(f"{folder}/starship_engine_timeline.png", dpi=300, bbox_inches='tight')
    
    # Add to viewer if showing figures
    if show_figures and viewer:
        viewer.add_figure(fig_ss, f"Launch {launch_number} - {vehicle_params['title']}")
    plt.close(fig_ss)
    
    # Create correlation plots between engine activity and performance
    create_engine_performance_correlation(df, "superheavy", folder, launch_number, show_figures)
    create_engine_performance_correlation(df, "starship", folder, launch_number, show_figures)
    
    # Create standard plots based on parameters from constants
    logger.info(f"Creating {len(ANALYZE_RESULTS_PLOT_PARAMS)} standard plot types")
    for params in ANALYZE_RESULTS_PLOT_PARAMS:
        if len(params) == 5:
            create_scatter_plot(df, *params, folder, launch_number, show_figures)
        else:
            # Unpack: x, y, title, filename, label, x_axis, y_axis.
            create_scatter_plot(df, *params, folder, launch_number, show_figures)
    
    logger.info(f"Completed all plots for launch {launch_number}")
    
    # Show the interactive viewer if requested
    if show_figures and viewer:
        viewer.show()
