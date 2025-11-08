import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from .plot_utils import maximize_figure_window
from utils.constants import (ENGINE_TIMELINE_PARAMS, ENGINE_PERFORMANCE_PARAMS,
                      FIGURE_SIZE, TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE, LABEL_FONT_SIZE, 
                      LEGEND_FONT_SIZE, TICK_FONT_SIZE, MARKER_SIZE, MARKER_ALPHA, 
                      LINE_WIDTH, LINE_ALPHA)
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def create_engine_group_plot(df: pd.DataFrame, vehicle: str, folder: str, launch_number: str, show_figures: bool = True):
    """
    Create a plot for a specific vehicle's engine activity.

    Args:
        df (pd.DataFrame): DataFrame with processed engine data
        vehicle (str): Vehicle name (e.g., "superheavy", "starship")
        folder (str): Folder to save the plot
        launch_number (str): Launch number to include in the title
        show_figures (bool): Whether to display the figures
    """
    # Find all engine activity columns for this vehicle
    engine_cols = [col for col in df.columns if col.startswith(f"{vehicle}.") and "active" in col]
    
    if not engine_cols:
        logger.debug(f"No engine activity columns found for {vehicle}")
        return
    
    title = f"Launch {launch_number} - {vehicle.title()} Engine Activity"
    logger.info(f"Creating engine plot: {title}")

    # Create figure (fullscreen)
    fig = plt.figure(figsize=FIGURE_SIZE)

    # Define colors for different engine types
    colors = sns.color_palette("husl", len(engine_cols))
    
    # Plot each engine activity column
    for i, col in enumerate(engine_cols):
        # Create a readable label from the column name
        label = col.replace(f"{vehicle}.", "").replace("_", " ").title()
        if "all" in label.lower():
            label = f"All Engines ({df[col].max():.0f})"
        
        sns.lineplot(x='real_time_seconds', y=col, data=df,
                    label=label, marker='o',
                    alpha=MARKER_ALPHA, color=colors[i],
                    linewidth=LINE_WIDTH if "all" in col.lower() else LINE_WIDTH-0.5)

    plt.title(title, fontsize=TITLE_FONT_SIZE)
    plt.xlabel("Mission Time (seconds)", fontsize=LABEL_FONT_SIZE)
    plt.ylabel("Active Engines", fontsize=LABEL_FONT_SIZE)
    
    # Set y-axis limit based on max engines
    max_engines = max(df[col].max() for col in engine_cols)
    plt.ylim(0, max_engines * 1.1)  # Add 10% padding
    
    plt.tick_params(labelsize=TICK_FONT_SIZE)
    plt.legend(fontsize=LEGEND_FONT_SIZE)
    plt.tight_layout()

    # Save figure
    os.makedirs(folder, exist_ok=True)
    save_path = f"{folder}/{vehicle}_engine_timeline.png"
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
    Create engine activity plots for all detected vehicles.

    Args:
        df (pd.DataFrame): DataFrame with processed engine data
        folder (str): Folder to save the plot
        launch_number (str): Launch number to include in the title
        show_figures (bool): Whether to display the figures
    """
    logger.info(f"Creating engine timeline plots for Launch {launch_number}")

    # Detect vehicles with engine data
    from .data_processing import detect_vehicles
    vehicles = detect_vehicles(df)
    
    # Filter to vehicles that have engine activity columns
    vehicles_with_engines = []
    for vehicle in vehicles:
        engine_cols = [col for col in df.columns if col.startswith(f"{vehicle}.") and "active" in col]
        if engine_cols:
            vehicles_with_engines.append(vehicle)
    
    if not vehicles_with_engines:
        logger.info("No engine activity data found, skipping engine timeline plots")
        return
    
    # Create plots for vehicles with engine data
    for vehicle in vehicles_with_engines:
        create_engine_group_plot(df, vehicle, folder, launch_number, show_figures)


def create_engine_performance_correlation(df: pd.DataFrame, vehicle: str, folder: str, launch_number: str, show_figures: bool = True) -> None:
    """
    Create a plot showing correlation between engine activity and vehicle performance.

    Args:
        df (pd.DataFrame): DataFrame with processed data
        vehicle (str): Vehicle name (e.g., "superheavy", "starship")
        folder (str): Folder to save the plot
        launch_number (str): Launch number to include in the title
        show_figures (bool): Whether to display the figures
    """
    # Find engine activity and performance columns
    engine_cols = [col for col in df.columns if col.startswith(f"{vehicle}.") and "active" in col]
    speed_col = f"{vehicle}.speed"
    
    if not engine_cols or speed_col not in df.columns:
        logger.debug(f"Missing engine or speed data for {vehicle} correlation plot")
        return
    
    # Use the "all active" column if available, otherwise the first engine column
    all_active_col = f"{vehicle}_all_active"
    if all_active_col in df.columns:
        color_col = all_active_col
    else:
        color_col = engine_cols[0]
    
    title_with_launch = f"Launch {launch_number} - {vehicle.title()} Velocity vs Engine Activity"
    logger.info(f"Creating engine performance correlation plot: {title_with_launch}")

    # Create figure (fullscreen)
    fig = plt.figure(figsize=FIGURE_SIZE)

    # Create scatter plot
    data_count = df[[speed_col, color_col]].dropna().shape[0]
    logger.debug(f"Plotting {data_count} data points for correlation")

    scatter = sns.scatterplot(
        x="real_time_seconds",
        y=speed_col,
        hue=color_col,
        size=color_col,
        sizes=(MARKER_SIZE, MARKER_SIZE*4),  # Range of point sizes
        palette="viridis",  # Use colormap
        alpha=MARKER_ALPHA,  # Transparency
        data=df           # Data source
    )

    # Add a legend with custom title
    max_engines = df[color_col].max()
    legend_title = f"Active Engines (0-{max_engines:.0f})"
    legend = scatter.legend(title=legend_title, fontsize=LEGEND_FONT_SIZE)
    plt.setp(legend.get_title(), fontsize=LEGEND_FONT_SIZE+1)

    # Add labels and title with consistent styling
    plt.xlabel("Mission Time (seconds)", fontsize=LABEL_FONT_SIZE)
    plt.ylabel("Velocity (km/h)", fontsize=LABEL_FONT_SIZE)
    plt.title(title_with_launch, fontsize=TITLE_FONT_SIZE)
    plt.tick_params(labelsize=TICK_FONT_SIZE)

    # Save figure with high quality
    os.makedirs(folder, exist_ok=True)
    save_path = f"{folder}/{vehicle}_velocity_vs_engines.png"
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