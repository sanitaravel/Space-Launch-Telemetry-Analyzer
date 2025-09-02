import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess
from .data_processing import load_and_clean_data, compute_acceleration, compute_g_force, prepare_fuel_data_columns
from utils.constants import (PLOT_MULTIPLE_LAUNCHES_PARAMS, COMPARE_FUEL_LEVEL_PARAMS,
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


def plot_multiple_launches(df_list: list, x: str, y: str, title: str, filename: str, folder: str,
                           labels: list[str], x_axis: str = None, y_axis: str = None, show_figures: bool = True) -> None:
    """
    Plot a comparison of multiple dataframes using seaborn.

    Args:
        df_list (list): List of dataframes to compare.
        x (str): The column name for the x-axis.
        y (str): The column name for the y-axis.
        labels (list): List of labels for the dataframes.
        title (str): The title of the graph.
        filename (str): The filename to save the graph as.
        folder (str): The folder to save the graph in.
        x_axis (str): The label for the x-axis.
        y_axis (str): The label for the y-axis.
        show_figures (bool): Whether to show figures or just save them.
    """
    logger.info(f"Creating multi-launch comparison plot: {title}")
    logger.debug(f"Comparing {len(df_list)} launches: {', '.join(labels)}")
    
    # Create figure (fullscreen)
    fig = plt.figure(figsize=FIGURE_SIZE)

    # Custom color palette with distinct colors for each launch
    palette = sns.color_palette("husl", len(df_list))

    # Plot each dataset with appropriate styling
    for i, (df, label) in enumerate(zip(df_list, labels)):
        color = palette[i]
        
        # Log data points per launch
        data_count = df[y].notna().sum()
        logger.debug(f"Launch {label}: {data_count} data points for {y}")

        # Add scatter plot with seaborn
        scatter = sns.scatterplot(
            x=x,
            y=y,
            data=df,
            label=f"{label}",
            color=color,
            alpha=MARKER_ALPHA,
            s=MARKER_SIZE
        )

        # Add trendline only for acceleration and g-force plots
        if ('acceleration' in y or 'g_force' in y) and len(df[[x, y]].dropna()) > 10:
            # Only use non-null values for the trendline
            valid_data = df[[x, y]].dropna()
            logger.debug(f"Launch {label}: Adding 10-point rolling window trendline")

            # Sort data by x-axis value to ensure proper rolling window calculation
            valid_data = valid_data.sort_values(by=x)
            
            # Use pandas rolling window (10 points) instead of LOWESS smoothing
            valid_data['trend'] = valid_data[y].rolling(window=10, center=True, min_periods=5).mean()

            # Plot the rolling average trendline
            plt.plot(valid_data[x], valid_data['trend'], '-', linewidth=LINE_WIDTH,
                     label=f"{label} (10-point Rolling Avg)", color=color)

    # Set labels with consistent styling
    plt.xlabel(x_axis, fontsize=LABEL_FONT_SIZE)
    plt.ylabel(y_axis, fontsize=LABEL_FONT_SIZE)
    plt.title(title, fontsize=TITLE_FONT_SIZE)
    plt.tick_params(labelsize=TICK_FONT_SIZE)

    # Add legend with improved visibility
    plt.legend(frameon=True, fontsize=LEGEND_FONT_SIZE)

    # Save figure with high quality
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, filename)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    logger.info(f"Saved comparison plot to {save_path}")

    # If showing figures, add to interactive viewer instead of displaying individually
    if show_figures:
        # Check if we're in interactive mode (viewer exists in the caller's context)
        from inspect import currentframe, getouterframes
        frame = currentframe().f_back
        if 'viewer' in frame.f_locals:
            # Add the figure to the viewer
            frame.f_locals['viewer'].add_figure(fig, title)
        else:
            # Fall back to regular display
            maximize_figure_window()
            plt.show()
    else:
        plt.close(fig)

 
def compare_multiple_launches(start_time: int, end_time: int, *json_paths: str, show_figures: bool = True) -> None:
    """
    Plot multiple launches on the same plot with a specified time window.

    Args:
        start_time (int): Minimum time in seconds to include in plots.
        end_time (int): Maximum time in seconds to include in plots. Use -1 for all data.
        *json_paths (str): Variable number of JSON file paths containing the results.
        show_figures (bool): Whether to show figures or just save them.
    """
    logger.info(f"Comparing multiple launches (time window: {start_time}s to {end_time if end_time != -1 else 'end'}s)")
    logger.debug(f"Loading data from {len(json_paths)} JSON files: {json_paths}")
    
    # Create interactive viewer if showing figures
    if show_figures:
        from .interactive_viewer import show_plots_interactively
        viewer = show_plots_interactively("Multiple Launches Comparison")
    
    df_list = []
    labels = []

    # Process each JSON file path separately
    for json_path in json_paths:
        logger.info(f"Processing JSON path: {json_path} (type: {type(json_path).__name__})")
        if not isinstance(json_path, str):
            logger.error(f"Invalid JSON path type: {type(json_path).__name__}, expected str")
            continue
            
        try:
            df = load_and_clean_data(json_path)
            if df.empty:
                logger.warning(f"Empty DataFrame for {json_path}, skipping")
                continue  # Skip if the DataFrame is empty due to JSON error

            # Filter by time window
            original_count = len(df)
            df = df[df['real_time_seconds'] >= start_time]
            if end_time != -1:
                df = df[df['real_time_seconds'] <= end_time]
            logger.debug(f"Using {len(df)} of {original_count} data points after time filtering")

            # Calculate acceleration using 30-frame distance
            sh_speed_col = 'superheavy.speed' if 'superheavy.speed' in df.columns else 'superheavy_speed'
            ss_speed_col = 'starship.speed' if 'starship.speed' in df.columns else 'starship_speed'
            
            df['superheavy_acceleration'] = compute_acceleration(df, sh_speed_col)
            df['starship_acceleration'] = compute_acceleration(df, ss_speed_col)

            # Calculate G-forces
            df['superheavy_g_force'] = compute_g_force(df['superheavy_acceleration'])
            df['starship_g_force'] = compute_g_force(df['starship_acceleration'])

            # Ensure fuel data columns exist and have proper names
            df = prepare_fuel_data_columns(df)
            
            df_list.append(df)
            launch_id = extract_launch_number(json_path)
            labels.append(f'Launch {launch_id}')  # Capitalize 'launch'
            logger.info(f"Successfully processed launch {launch_id}")
        except Exception as e:
            logger.error(f"Error processing {json_path}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())

    if not df_list:
        logger.error("No valid data available for comparison. Exiting.")
        return
    
    logger.info(f"Successfully loaded {len(df_list)} launches for comparison: {labels}")
    
    # Sort labels and create folder name
    labels_with_dfs = list(zip(labels, df_list))
    labels_with_dfs.sort(key=lambda x: x[0])
    labels = [label for label, _ in labels_with_dfs]
    df_list = [df for _, df in labels_with_dfs]
    
    folder_name = os.path.join(
        "results", "compare_launches", f"launches_{'_'.join([l.replace('Launch ', '') for l in labels])}")
    logger.info(f"Creating comparison plots in folder {folder_name}")

    # Create all comparison plots defined in constants
    logger.info(f"Creating {len(PLOT_MULTIPLE_LAUNCHES_PARAMS)} comparison plots")
    for params in PLOT_MULTIPLE_LAUNCHES_PARAMS:
        if len(params) == 4:
            plot_multiple_launches(
                df_list, *params, folder_name, labels, show_figures=show_figures)
        else:
            # Unpack: x, y, title, filename, x_axis, y_axis.
            x, y, title, filename, x_axis, y_axis = params
            plot_multiple_launches(df_list, x, y, title, filename, folder_name,
                                   labels, x_axis, y_axis, show_figures=show_figures)
    
    # Create fuel level comparison plots
    logger.info(f"Creating {len(COMPARE_FUEL_LEVEL_PARAMS)} fuel level comparison plots")
    for params in COMPARE_FUEL_LEVEL_PARAMS:
        if len(params) == 4:
            plot_multiple_launches(
                df_list, *params, folder_name, labels, show_figures=show_figures)
        else:
            # Unpack: x, y, title, filename, x_axis, y_axis.
            x, y, title, filename, x_axis, y_axis = params
            plot_multiple_launches(df_list, x, y, title, filename, folder_name,
                                   labels, x_axis, y_axis, show_figures=show_figures)
    
    logger.info("Completed all comparison plots")
    
    # Show the interactive viewer if requested
    if show_figures and 'viewer' in locals():
        viewer.show()
