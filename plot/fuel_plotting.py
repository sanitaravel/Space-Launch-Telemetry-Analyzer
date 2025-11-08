import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from .plot_utils import maximize_figure_window
from utils.constants import FUEL_LEVEL_PLOT_PARAMS, FIGURE_SIZE, TITLE_FONT_SIZE, LABEL_FONT_SIZE, LEGEND_FONT_SIZE, TICK_FONT_SIZE, MARKER_SIZE, LINE_WIDTH, LINE_ALPHA
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


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