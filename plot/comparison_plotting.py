import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess
from .data_processing import load_and_clean_data, compute_acceleration, compute_g_force, prepare_fuel_data_columns
from .plot_utils import maximize_figure_window
from utils.constants import (PLOT_MULTIPLE_LAUNCHES_PARAMS, COMPARE_FUEL_LEVEL_PARAMS,
                      FIGURE_SIZE, TITLE_FONT_SIZE, SUBTITLE_FONT_SIZE, LABEL_FONT_SIZE, 
                      LEGEND_FONT_SIZE, TICK_FONT_SIZE, MARKER_SIZE, MARKER_ALPHA, 
                      LINE_WIDTH, LINE_ALPHA)
from utils import extract_launch_number, extract_launch_info
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


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
    color_idx = 0
    for i, (df, label) in enumerate(zip(df_list, labels)):
        # Skip dataframes that don't have the required y-column
        if y not in df.columns:
            logger.debug(f"Skipping {label} - column '{y}' not found")
            continue
            
        color = palette[color_idx]
        color_idx += 1
        
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

 
def compare_multiple_launches(start_time: int, end_time: int, *json_paths: str, show_figures: bool = True, selected_vehicles: list[str] = None) -> None:
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

            # Detect vehicles and calculate acceleration/G-forces for all of them
            from .data_processing import detect_vehicles
            vehicles = detect_vehicles(df)
            
            for vehicle in vehicles:
                speed_col = f'{vehicle}.speed' if f'{vehicle}.speed' in df.columns else f'{vehicle}_speed'
                if speed_col in df.columns:
                    df[f'{vehicle}_acceleration'] = compute_acceleration(df, speed_col)
                    df[f'{vehicle}_g_force'] = compute_g_force(df[f'{vehicle}_acceleration'])

            # Ensure fuel data columns exist and have proper names
            df = prepare_fuel_data_columns(df)
            
            df_list.append(df)
            launch_info = extract_launch_info(json_path)
            company_name = launch_info['company'].replace('_', ' ').title()
            rocket_name = launch_info['rocket'].replace('_', ' ').title()
            launch_number = launch_info['launch_number']
            labels.append(f'{company_name} {rocket_name} Launch {launch_number}')
            logger.info(f"Successfully processed {company_name} {rocket_name} Launch {launch_number}")
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
    
    # Create a more descriptive folder name for cross-company comparisons
    companies = set()
    rockets = set()
    launch_nums = []
    for label in labels:
        parts = label.split()
        if len(parts) >= 4:
            companies.add(parts[0])
            rockets.add(parts[1])
            launch_nums.append(parts[-1])
    
    if len(companies) > 1:
        # Cross-company comparison
        folder_name = os.path.join("results", "compare_launches", f"cross_company_{'_'.join(sorted(companies))}_{'_'.join(sorted(rockets))}")
    else:
        # Same company comparison
        folder_name = os.path.join("results", "compare_launches", f"launches_{'_'.join(launch_nums)}")
    
    logger.info(f"Creating comparison plots in folder {folder_name}")

    # Create all comparison plots defined in constants (skip for cross-company, already done above)
    if len(companies) <= 1:
        logger.info(f"Creating {len(PLOT_MULTIPLE_LAUNCHES_PARAMS)} comparison plots")
        for params in PLOT_MULTIPLE_LAUNCHES_PARAMS:
            if len(params) == 4:
                x, y, title, filename = params
                x_axis, y_axis = None, None
            else:
                # Unpack: x, y, title, filename, x_axis, y_axis.
                x, y, title, filename, x_axis, y_axis = params
            
            # Check if the y-column exists in any of the dataframes
            if any(y in df.columns for df in df_list):
                plot_multiple_launches(df_list, x, y, title, filename, folder_name,
                                       labels, x_axis, y_axis, show_figures=show_figures)
            else:
                logger.debug(f"Skipping plot '{title}' - column '{y}' not found in any dataframe")
    
    # Create dynamic cross-company comparison plots
    logger.info("Creating cross-company comparison plots")
    
    # Define metric types and their corresponding column patterns
    metric_configs = [
        {
            'name': 'Velocity',
            'columns': ['speed'],
            'ylabel': 'Velocity (km/h)',
            'filename': 'velocity_comparison.png'
        },
        {
            'name': 'Altitude', 
            'columns': ['altitude'],
            'ylabel': 'Altitude (km)',
            'filename': 'altitude_comparison.png'
        },
        {
            'name': 'Acceleration',
            'columns': ['_acceleration'],
            'ylabel': 'Acceleration (m/s²)',
            'filename': 'acceleration_comparison.png'
        },
        {
            'name': 'G-Force',
            'columns': ['_g_force'],
            'ylabel': 'G-Force (g)',
            'filename': 'g_force_comparison.png'
        },
        {
            'name': 'Engine Activity',
            'columns': ['_all_active'],
            'ylabel': 'Active Engines',
            'filename': 'engine_activity_comparison.png'
        }
    ]
    
    for metric_config in metric_configs:
        logger.info(f"Creating {metric_config['name']} comparison plot")
        
        # Collect all available data for this metric
        plot_data = []
        plot_labels = []
        
        for df, launch_label in zip(df_list, labels):
            for col in df.columns:
                # Check if this column matches any of the metric patterns
                if any(col.endswith(pattern) for pattern in metric_config['columns']):
                    # Extract vehicle name from column
                    if '.' in col:
                        vehicle_name = col.split('.')[0]
                    else:
                        # For computed columns like acceleration/g-force
                        vehicle_name = col.rsplit('_', 1)[0]  # Remove _acceleration, _g_force, etc.
                    
                    # Skip if vehicle filtering is enabled and this vehicle is not selected
                    if selected_vehicles and vehicle_name not in selected_vehicles:
                        continue
                    
                    # Create a descriptive label
                    company_rocket = ' '.join(launch_label.split()[:2])  # "Blue Origin" or "Spacex Starship"
                    vehicle_display = vehicle_name.replace('_', ' ').title()
                    data_label = f"{company_rocket} {vehicle_display}"
                    
                    plot_data.append((df, col, data_label))
                    plot_labels.append(data_label)
        
        if plot_data:
            # Create the comparison plot
            fig = plt.figure(figsize=FIGURE_SIZE)
            
            # Use a larger color palette for cross-company comparisons
            num_series = len(plot_data)
            if num_series <= 10:
                palette = sns.color_palette("husl", num_series)
            else:
                palette = sns.color_palette("husl", num_series)
            
            for i, (df, col, label) in enumerate(plot_data):
                color = palette[i]
                
                # Log data points
                data_count = df[col].notna().sum()
                logger.debug(f"{label}: {data_count} data points for {col}")
                
                # Add scatter plot
                scatter = sns.scatterplot(
                    x='real_time_seconds',
                    y=col,
                    data=df,
                    label=label,
                    color=color,
                    alpha=MARKER_ALPHA,
                    s=MARKER_SIZE
                )
                
                # Add trendline for acceleration and g-force
                if any(pattern in col for pattern in ['acceleration', 'g_force']) and len(df[['real_time_seconds', col]].dropna()) > 10:
                    valid_data = df[['real_time_seconds', col]].dropna()
                    valid_data = valid_data.sort_values(by='real_time_seconds')
                    
                    valid_data['trend'] = valid_data[col].rolling(window=10, center=True, min_periods=5).mean()
                    
                    plt.plot(valid_data['real_time_seconds'], valid_data['trend'], '-', 
                           linewidth=LINE_WIDTH, label=f"{label} (10-pt Rolling Avg)", color=color)
            
            # Set labels
            plt.xlabel('Mission Time (seconds)', fontsize=LABEL_FONT_SIZE)
            plt.ylabel(metric_config['ylabel'], fontsize=LABEL_FONT_SIZE)
            plt.title(f'Cross-Company {metric_config["name"]} Comparison', fontsize=TITLE_FONT_SIZE)
            plt.tick_params(labelsize=TICK_FONT_SIZE)
            
            # Add legend
            plt.legend(frameon=True, fontsize=LEGEND_FONT_SIZE)
            
            # Save figure
            save_path = os.path.join(folder_name, metric_config['filename'])
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved cross-company {metric_config['name']} comparison to {save_path}")
            
            # Add to viewer if requested
            if show_figures:
                if 'viewer' in locals():
                    viewer.add_figure(fig, f'Cross-Company {metric_config["name"]} Comparison')
                else:
                    maximize_figure_window()
                    plt.show()
            else:
                plt.close(fig)
        else:
            logger.debug(f"No data available for {metric_config['name']} comparison")
    
    # Create cross-company fuel level comparison plots
    logger.info("Creating cross-company fuel level comparison plots")
    
    fuel_configs = [
        {
            'fuel_type': 'LOX',
            'column_pattern': '.fuel.lox.fullness',
            'ylabel': 'LOX Tank Fullness (%)',
            'filename': 'lox_fuel_comparison.png'
        },
        {
            'fuel_type': 'CH4', 
            'column_pattern': '.fuel.ch4.fullness',
            'ylabel': 'CH4 Tank Fullness (%)',
            'filename': 'ch4_fuel_comparison.png'
        }
    ]
    
    for fuel_config in fuel_configs:
        logger.info(f"Creating {fuel_config['fuel_type']} fuel level comparison plot")
        
        # Collect all available fuel data
        plot_data = []
        
        for df, launch_label in zip(df_list, labels):
            for col in df.columns:
                if col.endswith(fuel_config['column_pattern']):
                    # Extract vehicle name
                    vehicle_name = col.split('.')[0]
                    
                    # Skip if vehicle filtering is enabled and this vehicle is not selected
                    if selected_vehicles and vehicle_name not in selected_vehicles:
                        continue
                    
                    company_rocket = ' '.join(launch_label.split()[:2])
                    vehicle_display = vehicle_name.replace('_', ' ').title()
                    data_label = f"{company_rocket} {vehicle_display}"
                    
                    plot_data.append((df, col, data_label))
        
        if plot_data:
            # Create the fuel comparison plot
            fig = plt.figure(figsize=FIGURE_SIZE)
            
            num_series = len(plot_data)
            palette = sns.color_palette("husl", num_series)
            
            for i, (df, col, label) in enumerate(plot_data):
                color = palette[i]
                
                data_count = df[col].notna().sum()
                logger.debug(f"{label}: {data_count} data points for {col}")
                
                scatter = sns.scatterplot(
                    x='real_time_seconds',
                    y=col,
                    data=df,
                    label=label,
                    color=color,
                    alpha=MARKER_ALPHA,
                    s=MARKER_SIZE
                )
            
            # Set labels
            plt.xlabel('Mission Time (seconds)', fontsize=LABEL_FONT_SIZE)
            plt.ylabel(fuel_config['ylabel'], fontsize=LABEL_FONT_SIZE)
            plt.title(f'Cross-Company {fuel_config["fuel_type"]} Fuel Level Comparison', fontsize=TITLE_FONT_SIZE)
            plt.tick_params(labelsize=TICK_FONT_SIZE)
            
            # Add legend
            plt.legend(frameon=True, fontsize=LEGEND_FONT_SIZE)
            
            # Save figure
            save_path = os.path.join(folder_name, fuel_config['filename'])
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved cross-company {fuel_config['fuel_type']} fuel comparison to {save_path}")
            
            # Add to viewer if requested
            if show_figures:
                if 'viewer' in locals():
                    viewer.add_figure(fig, f'Cross-Company {fuel_config["fuel_type"]} Fuel Level Comparison')
                else:
                    maximize_figure_window()
                    plt.show()
            else:
                plt.close(fig)
        else:
            logger.debug(f"No {fuel_config['fuel_type']} fuel data available for comparison")
    
    # Create fuel level comparison plots (skip for cross-company, already done above)
    if len(companies) <= 1:
        logger.info(f"Creating {len(COMPARE_FUEL_LEVEL_PARAMS)} fuel level comparison plots")
        for params in COMPARE_FUEL_LEVEL_PARAMS:
            if len(params) == 4:
                x, y, title, filename = params
                x_axis, y_axis = None, None
            else:
                # Unpack: x, y, title, filename, x_axis, y_axis.
                x, y, title, filename, x_axis, y_axis = params
            
            # Check if the y-column exists in any of the dataframes
            if any(y in df.columns for df in df_list):
                plot_multiple_launches(df_list, x, y, title, filename, folder_name,
                                       labels, x_axis, y_axis, show_figures=show_figures)
            else:
                logger.debug(f"Skipping fuel plot '{title}' - column '{y}' not found in any dataframe")
    
    logger.info("Completed all comparison plots")
    
    # Show the interactive viewer if requested
    if show_figures and 'viewer' in locals():
        viewer.show()
