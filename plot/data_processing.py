import json
import pandas as pd
import numpy as np
import traceback
from tqdm import tqdm
from utils.constants import G_FORCE_CONVERSION
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def validate_json(data: list) -> tuple:
    """
    Validate the structure of the JSON data.

    Args:
        data (list): The JSON data to validate.

    Returns:
        tuple: (is_valid, invalid_entry, data_structure_type)
    """
    if not data:
        return (False, None, None)
    
    first_entry = data[0]
    
    # Check for SpaceX Starship structure
    spacex_keys = {"frame_number", "superheavy", "starship", "time", "real_time_seconds"}
    if spacex_keys.issubset(first_entry.keys()):
        return (True, None, "spacex_starship")
    
    # Check for Blue Origin New Glenn structure
    blue_origin_keys = {"frame_number", "vehicles", "time", "real_time_seconds"}
    if blue_origin_keys.issubset(first_entry.keys()):
        return (True, None, "blue_origin_new_glenn")
    
    # If neither structure matches, return invalid
    return (False, first_entry, None)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the data in the DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame containing the data.

    Returns:
        pd.DataFrame: The cleaned DataFrame.
    """
    logger.info("Cleaning dataframe and removing outliers")
    
    # Step 1: Ensure numeric values for existing columns
    expected_columns = ['starship.speed', 'superheavy.speed', 'starship.altitude', 'superheavy.altitude']
    for column in expected_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')
        
    # Log the number of NaN values after conversion for existing columns
    existing_columns = [col for col in expected_columns if col in df.columns]
    if existing_columns:
        nan_counts = df[existing_columns].isna().sum()
        logger.debug(f"NaN values after numeric conversion: {nan_counts.to_dict()}")

    # Step 2: Remove impossible values for existing columns
    if 'starship.speed' in df.columns:
        prev_count = (~df['starship.speed'].isna()).sum()
        df['starship.speed'] = df['starship.speed'].clip(lower=0, upper=28000)
        current_count = (~df['starship.speed'].isna()).sum()
        logger.debug(f"Clipped {prev_count - current_count} impossible values from starship.speed")
    
    if 'superheavy.speed' in df.columns:
        prev_count = (~df['superheavy.speed'].isna()).sum()
        df['superheavy.speed'] = df['superheavy.speed'].clip(lower=0, upper=6000)
        current_count = (~df['superheavy.speed'].isna()).sum()
        logger.debug(f"Clipped {prev_count - current_count} impossible values from superheavy.speed")
    
    if 'starship.altitude' in df.columns:
        prev_count = (~df['starship.altitude'].isna()).sum()
        df['starship.altitude'] = df['starship.altitude'].clip(lower=0, upper=200)
        current_count = (~df['starship.altitude'].isna()).sum()
        logger.debug(f"Clipped {prev_count - current_count} impossible values from starship.altitude")
    
    if 'superheavy.altitude' in df.columns:
        prev_count = (~df['superheavy.altitude'].isna()).sum()
        df['superheavy.altitude'] = df['superheavy.altitude'].clip(lower=0, upper=100)
        current_count = (~df['superheavy.altitude'].isna()).sum()
        logger.debug(f"Clipped {prev_count - current_count} impossible values from superheavy.altitude")

    # Step 3: Detect abrupt changes for existing columns
    if 'starship.speed' in df.columns:
        df['starship.speed_diff'] = df['starship.speed'].diff().abs()
        abrupt_changes = (df['starship.speed_diff'] > 50).sum()
        logger.debug(f"Detected {abrupt_changes} abrupt changes in starship.speed")
        df.loc[df['starship.speed_diff'] > 50, 'starship.speed'] = None
    
    if 'superheavy.speed' in df.columns:
        df['superheavy.speed_diff'] = df['superheavy.speed'].diff().abs()
        abrupt_changes = (df['superheavy.speed_diff'] > 50).sum()
        logger.debug(f"Detected {abrupt_changes} abrupt changes in superheavy.speed")
        df.loc[df['superheavy.speed_diff'] > 50, 'superheavy.speed'] = None
    
    if 'starship.altitude' in df.columns:
        df['starship.altitude_diff'] = df['starship.altitude'].diff().abs()
        abrupt_changes = (df['starship.altitude_diff'] > 1).sum()
        logger.debug(f"Detected {abrupt_changes} abrupt changes in starship.altitude")
        df.loc[df['starship.altitude_diff'] > 1, 'starship.altitude'] = None
    
    if 'superheavy.altitude' in df.columns:
        df['superheavy.altitude_diff'] = df['superheavy.altitude'].diff().abs()
        abrupt_changes = (df['superheavy.altitude_diff'] > 1).sum()
        logger.debug(f"Detected {abrupt_changes} abrupt changes in superheavy.altitude")
        df.loc[df['superheavy.altitude_diff'] > 1, 'superheavy.altitude'] = None

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
    
    # Create columns for engine counts
    df['superheavy_central_active'] = 0
    df['superheavy_central_total'] = 3
    df['superheavy_inner_active'] = 0  
    df['superheavy_inner_total'] = 10
    df['superheavy_outer_active'] = 0
    df['superheavy_outer_total'] = 20
    df['superheavy_all_active'] = 0
    df['superheavy_all_total'] = 33  # 3 + 10 + 20 = 33 engines total
    
    df['starship_rearth_active'] = 0
    df['starship_rearth_total'] = 3
    df['starship_rvac_active'] = 0
    df['starship_rvac_total'] = 3
    df['starship_all_active'] = 0
    df['starship_all_total'] = 6  # 3 + 3 = 6 engines total
    
    # Process engine data using the correct column structure
    try:
        # Check if the expected columns exist
        engine_columns = {
            'superheavy.engines.central_stack': 'superheavy_central_active',
            'superheavy.engines.inner_ring': 'superheavy_inner_active',
            'superheavy.engines.outer_ring': 'superheavy_outer_active',
            'starship.engines.rearth': 'starship_rearth_active',
            'starship.engines.rvac': 'starship_rvac_active'
        }
        
        for src_col, dest_col in tqdm(engine_columns.items(), desc="Processing engine columns"):
            if src_col in df.columns:
                # Sum the boolean values in each row to get active engine count
                # Each row contains a list of boolean values (True = engine active)
                df[dest_col] = df[src_col].apply(
                    lambda x: sum(1 for engine in x if engine) if isinstance(x, list) else 0
                )
                logger.debug(f"Processed {src_col} to {dest_col}")
                
        # Calculate total active engines
        df['superheavy_all_active'] = (
            df['superheavy_central_active'] + 
            df['superheavy_inner_active'] + 
            df['superheavy_outer_active']
        )
        
        df['starship_all_active'] = (
            df['starship_rearth_active'] + 
            df['starship_rvac_active']
        )
            
        # Drop the original engine columns as they're now processed
        for col in engine_columns.keys():
            if col in df.columns:
                df = df.drop(columns=[col])
                
        logger.info("Engine data processed successfully")
                
    except Exception as e:
        logger.error(f"Error processing engine data: {e}")
        logger.debug(traceback.format_exc())
    
    return df


def prepare_fuel_data_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare fuel data columns to ensure they exist with proper names.
    
    Args:
        df (pd.DataFrame): DataFrame to prepare
        
    Returns:
        pd.DataFrame: DataFrame with normalized fuel column names
    """
    logger.debug("Preparing fuel data columns")
    
    # Check for nested vs flat column structure
    if 'superheavy.fuel.lox.fullness' not in df.columns:
        # Try to find fuel data and rename it if needed
        for vehicle in ['superheavy', 'starship']:
            for fuel_type in ['lox', 'ch4']:
                # Check various possible column name formats
                possible_names = [
                    f'{vehicle}.fuel.{fuel_type}.fullness',
                    f'{vehicle}_fuel_{fuel_type}_fullness',
                    f'{vehicle}.{fuel_type}_fullness',
                    f'{vehicle}_{fuel_type}_fullness'
                ]
                
                # Find the first column that exists
                found = False
                for col in possible_names:
                    if col in df.columns:
                        df[f'{vehicle}.fuel.{fuel_type}.fullness'] = df[col]
                        found = True
                        logger.debug(f"Found fuel column {col}, normalized to {vehicle}.fuel.{fuel_type}.fullness")
                        break
                
                # If no column found, create it with zeros
                if not found:
                    logger.debug(f"No fuel data found for {vehicle} {fuel_type}, creating empty column")
                    df[f'{vehicle}.fuel.{fuel_type}.fullness'] = 0
    
    return df


def normalize_fuel_levels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize fuel level readings using grouping rules. For LOX and CH4 in each vehicle, 
    if difference > 30%, use max value if time < 200s, otherwise use min value.
    
    Args:
        df (pd.DataFrame): DataFrame with fuel level data
        
    Returns:
        pd.DataFrame: DataFrame with normalized fuel levels
    """
    logger.info("Normalizing fuel levels between LOX and CH4")
    
    # Check if we have the required columns
    required_cols = [
        'superheavy.fuel.lox.fullness', 'superheavy.fuel.ch4.fullness',
        'starship.fuel.lox.fullness', 'starship.fuel.ch4.fullness',
        'real_time_seconds'
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.warning(f"Missing required columns for fuel normalization: {missing_cols}")
        return df
    
    # Process each row
    normalized_count = {'superheavy': 0, 'starship': 0}
    
    for idx, row in df.iterrows():
        current_time = row['real_time_seconds']
        
        # Group 1: Superheavy LOX and CH4
        sh_lox = row['superheavy.fuel.lox.fullness']
        sh_ch4 = row['superheavy.fuel.ch4.fullness']
        
        if abs(sh_lox - sh_ch4) > 30:
            # Use max value in first 200s, min value after
            if current_time < 200:
                chosen_value = max(sh_lox, sh_ch4)
            else:
                chosen_value = min(sh_lox, sh_ch4)
                
            df.at[idx, 'superheavy.fuel.lox.fullness'] = chosen_value
            df.at[idx, 'superheavy.fuel.ch4.fullness'] = chosen_value
            normalized_count['superheavy'] += 1
        
        # Group 2: Starship LOX and CH4
        ss_lox = row['starship.fuel.lox.fullness']
        ss_ch4 = row['starship.fuel.ch4.fullness']
        
        if abs(ss_lox - ss_ch4) > 30:
            # Use max value in first 200s, min value after
            if current_time < 200:
                chosen_value = max(ss_lox, ss_ch4)
            else:
                chosen_value = min(ss_lox, ss_ch4)
                
            df.at[idx, 'starship.fuel.lox.fullness'] = chosen_value
            df.at[idx, 'starship.fuel.ch4.fullness'] = chosen_value
            normalized_count['starship'] += 1
    
    logger.info(f"Normalized {normalized_count['superheavy']} Superheavy and {normalized_count['starship']} Starship fuel readings")
    return df


def load_and_clean_data(json_path: str) -> pd.DataFrame:
    """
    Load, flatten, and clean data from a JSON file.
    
    Args:
        json_path (str): Path to the JSON file containing the data.
        
    Returns:
        pd.DataFrame: The cleaned DataFrame.
    """
    logger.info(f"Loading data from {json_path}")
    
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} records from JSON file")
        
        # Validate the JSON data structure
        is_valid, invalid_entry, data_structure = validate_json(data)
        if not is_valid:
            logger.warning(f"Invalid data structure in JSON. Example invalid entry: {invalid_entry}")
            return pd.DataFrame()
        
        logger.info(f"Detected data structure: {data_structure}")
        
        # Normalize data structure based on type
        if data_structure == "blue_origin_new_glenn":
            # Convert Blue Origin structure to SpaceX-like structure for compatibility
            for entry in data:
                if "vehicles" in entry:
                    vehicles = entry["vehicles"]
                    # Map new_glenn to superheavy and second_stage to starship
                    if "new_glenn" in vehicles:
                        entry["superheavy"] = vehicles["new_glenn"]
                    if "second_stage" in vehicles:
                        entry["starship"] = vehicles["second_stage"]
                    # Remove the vehicles key
                    del entry["vehicles"]
        
        # Use json_normalize with sep='.' to flatten nested dictionaries with dot notation
        df = pd.json_normalize(data)
        logger.debug(f"Normalized JSON to DataFrame with {len(df)} rows and {len(df.columns)} columns")
        
        # Process engine data
        df = process_engine_data(df)
        
        # Drop time column as we're using real_time_seconds
        if 'time' in df.columns:
            df.drop(columns=["time"], inplace=True)
            logger.debug("Dropped 'time' column (using 'real_time_seconds' instead)")
        
        # Clean velocity and altitude columns
        # Assuming they're now in the format 'superheavy.speed', 'starship.speed', etc.
        # Check if we need to rename columns
        if 'superheavy.speed' not in df.columns and 'superheavy.speed' not in df.columns:
            logger.debug("Superheavy and Starship data need extraction from nested columns")
            # Extract speed and altitude from nested dictionaries if needed
            for column in tqdm(["superheavy", "starship"], desc="Separating columns"):
                if column in df.columns:
                    df[[f"{column}.speed", f"{column}.altitude"]] = df[column].apply(pd.Series)
                    df.drop(columns=[column], inplace=True)
                    logger.debug(f"Extracted speed and altitude from {column} column")
                    
        # Sort by time
        df.sort_values(by="real_time_seconds", inplace=True)
        logger.debug("Sorted DataFrame by real_time_seconds")
        
        # Ensure fuel data columns are properly named
        df = prepare_fuel_data_columns(df)
        
        # Apply fuel level normalization
        df = normalize_fuel_levels(df)
        
        # Clean data
        df = clean_dataframe(df)
        
        logger.info(f"Data processing complete. Final DataFrame has {len(df)} rows and {len(df.columns)} columns")
        return df
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {json_path}: {str(e)}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error
        
    except Exception as e:
        logger.error(f"Error loading data from {json_path}: {str(e)}")
        logger.debug(traceback.format_exc())
        return pd.DataFrame()


def compute_acceleration(df: pd.DataFrame, speed_column: str, frame_distance: int = 30, max_accel: float = 100.0) -> pd.Series:
    """
    Calculate acceleration from speed data using a fixed frame distance.

    Args:
        df (pd.DataFrame): The DataFrame containing the data.
        speed_column (str): The column name for the speed data.
        frame_distance (int): Number of frames to look ahead for calculating acceleration.
        max_accel (float): Maximum allowed acceleration in m/s². Values above this will be set to None.

    Returns:
        pd.Series: The calculated acceleration.
    """
    logger.info(f"Computing acceleration from {speed_column} with {frame_distance} frame distance")
    
    # Convert speed from km/h to m/s
    speed_m_per_s = df[speed_column] * (1000 / 3600)
    
    # Pre-allocate result series with NaN values
    acceleration = pd.Series(np.nan, index=df.index)
    
    # Valid indices for calculation (those with frame_distance ahead of them)
    valid_indices = np.arange(len(df) - frame_distance)
    
    # Get current and future speeds and times in one operation
    current_speeds = speed_m_per_s.iloc[valid_indices].to_numpy()
    future_speeds = speed_m_per_s.iloc[valid_indices + frame_distance].to_numpy()
    current_times = df['real_time_seconds'].iloc[valid_indices].to_numpy()
    future_times = df['real_time_seconds'].iloc[valid_indices + frame_distance].to_numpy()
    
    # Calculate differences
    speed_diffs = future_speeds - current_speeds
    time_diffs = future_times - current_times
    
    # Create a mask for valid calculations
    valid_mask = (
        ~np.isnan(current_speeds) & 
        ~np.isnan(future_speeds) & 
        (time_diffs > 0)
    )
    
    # Initialize results array
    accel_values = np.full(len(valid_indices), np.nan)
    
    # Calculate acceleration only for valid points
    accel_values[valid_mask] = speed_diffs[valid_mask] / time_diffs[valid_mask]
    
    # Apply maximum acceleration filter
    valid_accel = np.abs(accel_values) <= max_accel
    
    # Track statistics for logging
    invalid_count = np.sum(~valid_mask)
    out_of_range_count = np.sum(valid_mask & ~valid_accel)
    
    # Assign results to output Series
    acceleration.iloc[valid_indices[valid_mask & valid_accel]] = accel_values[valid_mask & valid_accel]
    
    # Log statistics
    logger.debug(f"Acceleration computation stats: {invalid_count} invalid points, " +
                f"{out_of_range_count} out-of-range points, " +
                f"{frame_distance} trailing frames with no data")
    
    logger.info(f"Acceleration computation complete, produced {(~acceleration.isna()).sum()} valid values")
    
    return acceleration


def compute_g_force(acceleration_ms2: pd.Series, inplace: bool = False) -> pd.Series:
    """
    Convert acceleration in m/s² to G-forces.
    
    Args:
        acceleration_ms2 (pd.Series): Acceleration values in m/s²
        inplace (bool): If True, modify the input series directly (more efficient)
        
    Returns:
        pd.Series: G-force values (1G = 9.81 m/s²)
    """
    logger.debug(f"Converting acceleration values to G forces (dividing by {G_FORCE_CONVERSION})")
    
    # Use the input series directly if inplace=True
    if inplace:
        acceleration_ms2.values[:] = acceleration_ms2.values / G_FORCE_CONVERSION
        g_forces = acceleration_ms2
    else:
        # Create a new series with the calculated values
        g_forces = pd.Series(
            acceleration_ms2.values / G_FORCE_CONVERSION,
            index=acceleration_ms2.index
        )
    
    # Only calculate min/max if debug logging is enabled
    if not g_forces.isna().all():
        logger.debug(f"G-force range: {g_forces.min()} to {g_forces.max()} g")
    
    return g_forces
