import pandas as pd
import numpy as np
import traceback
from tqdm import tqdm
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the data in the DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame containing the data.

    Returns:
        pd.DataFrame: The cleaned DataFrame.
    """
    logger.info("Cleaning dataframe and removing outliers")

    # Detect available vehicles
    from .data_processing import detect_vehicles
    vehicles = detect_vehicles(df)
    
    # Step 1: Ensure numeric values for vehicle columns
    vehicle_columns = []
    for vehicle in vehicles:
        for data_type in ['speed', 'altitude']:
            col_name = f"{vehicle}.{data_type}"
            if col_name in df.columns:
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                vehicle_columns.append(col_name)
    
    # Log NaN values
    if vehicle_columns:
        nan_counts = df[vehicle_columns].isna().sum()
        logger.debug(f"NaN values after numeric conversion: {nan_counts.to_dict()}")

    # Step 3: Detect abrupt changes for each vehicle and data type
    change_thresholds = {
        'speed': 50,      # km/h change threshold
        'altitude': 1     # km change threshold
    }
    
    for vehicle in vehicles:
        for data_type in ['speed', 'altitude']:
            col_name = f"{vehicle}.{data_type}"
            if col_name in df.columns:
                diff_col = f"{vehicle}.{data_type}_diff"
                df[diff_col] = df[col_name].diff().abs()
                
                threshold = change_thresholds[data_type]
                abrupt_changes = (df[diff_col] > threshold).sum()
                
                if abrupt_changes > 0:
                    logger.debug(f"Detected {abrupt_changes} abrupt changes in {col_name}")
                    df.loc[df[diff_col] > threshold, col_name] = None

    logger.info("DataFrame cleaning complete")
    return df


def process_engine_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process engine data from the JSON and calculate number of active engines.

    Args:
        df (pd.DataFrame): DataFrame with raw engine data

    Returns:
        pd.DataFrame: DataFrame with processed engine data
    """
    logger.info("Processing engine data")

    # Detect available vehicles
    from .data_processing import detect_vehicles
    vehicles = detect_vehicles(df)
    
    # Define engine configurations for different vehicles
    engine_configs = {
        'superheavy': {
            'engines': {
                'central_stack': {'total': 3, 'column': 'superheavy.engines.central_stack'},
                'inner_ring': {'total': 10, 'column': 'superheavy.engines.inner_ring'},
                'outer_ring': {'total': 20, 'column': 'superheavy.engines.outer_ring'}
            }
        },
        'starship': {
            'engines': {
                'rearth': {'total': 3, 'column': 'starship.engines.rearth'},
                'rvac': {'total': 3, 'column': 'starship.engines.rvac'}
            }
        },
        'new_glenn': {
            'engines': {
                'booster': {'total': 7, 'column': 'new_glenn.engines.booster'}
            }
        }
    }
    
    # Create columns for engine counts for each detected vehicle
    for vehicle in vehicles:
        if vehicle in engine_configs:
            config = engine_configs[vehicle]
            for engine_type, engine_info in config['engines'].items():
                active_col = f"{vehicle}_{engine_type}_active"
                total_col = f"{vehicle}_{engine_type}_total"
                df[active_col] = 0
                df[total_col] = engine_info['total']
            
            # Create total active column
            all_active_col = f"{vehicle}_all_active"
            all_total_col = f"{vehicle}_all_total"
            df[all_active_col] = 0
            df[all_total_col] = sum(engine_info['total'] for engine_info in config['engines'].values())

    # Process engine data using the correct column structure
    try:
        # Process each vehicle's engine data
        for vehicle in vehicles:
            if vehicle in engine_configs:
                config = engine_configs[vehicle]
                active_cols = []
                
                for engine_type, engine_info in config['engines'].items():
                    src_col = engine_info['column']
                    dest_col = f"{vehicle}_{engine_type}_active"
                    
                    if src_col in df.columns:
                        # Sum the boolean values in each row to get active engine count
                        # Each row contains a list of boolean values (True = engine active)
                        df[dest_col] = df[src_col].apply(
                            lambda x: sum(1 for engine in x if engine) if isinstance(x, list) else 0
                        )
                        active_cols.append(dest_col)
                        logger.debug(f"Processed {src_col} to {dest_col}")
                
                # Calculate total active engines for this vehicle
                if active_cols:
                    all_active_col = f"{vehicle}_all_active"
                    df[all_active_col] = df[active_cols].sum(axis=1)
                
                # Drop the original engine columns for this vehicle
                original_cols = [engine_info['column'] for engine_info in config['engines'].values()]
                cols_to_drop = [col for col in original_cols if col in df.columns]
                if cols_to_drop:
                    df = df.drop(columns=cols_to_drop)

        logger.info("Engine data processed successfully")

    except Exception as e:
        logger.error(f"Error processing engine data: {e}")
        logger.debug(traceback.format_exc())

    return df