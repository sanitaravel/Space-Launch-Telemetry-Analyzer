import json
import pandas as pd
import numpy as np
import traceback
from tqdm import tqdm
from .data_validation import validate_json
from .data_cleaning import clean_dataframe, process_engine_data
from .data_computation import compute_acceleration, compute_g_force
from .fuel_processing import prepare_fuel_data_columns, normalize_fuel_levels
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def detect_vehicles(df: pd.DataFrame) -> list:
    """
    Detect available vehicles in the DataFrame based on column patterns.
    
    Args:
        df (pd.DataFrame): DataFrame with vehicle data
        
    Returns:
        list: List of detected vehicle names
    """
    vehicles = set()
    
    # Look for columns that represent vehicle data
    for col in df.columns:
        if '.' in col:
            parts = col.split('.')
            prefix = parts[0]
            
            # Check if this looks like vehicle data (has speed, altitude, fuel, or engines)
            if len(parts) >= 2 and parts[1] in ['speed', 'altitude', 'fuel', 'engines']:
                vehicles.add(prefix)
            # Also check for nested fuel/engine data
            elif len(parts) >= 3 and (parts[1] in ['fuel', 'engines'] or (parts[1] == 'fuel' and parts[2] in ['lox', 'ch4'])):
                vehicles.add(prefix)
    
    # Convert to sorted list
    vehicle_list = sorted(list(vehicles))
    
    # Filter out non-vehicle prefixes that might have slipped through
    non_vehicle_prefixes = {'real_time', 'time', 'frame_number', 'fuel'}
    vehicle_list = [v for v in vehicle_list if v not in non_vehicle_prefixes]
    
    logger.info(f"Detected vehicles: {vehicle_list}")
    return vehicle_list


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
        
        # Normalize data structure - extract vehicles to top level
        if data_structure == "universal":
            # Convert universal vehicles structure to flat structure for compatibility
            for entry in data:
                if "vehicles" in entry:
                    vehicles = entry["vehicles"]
                    # Extract vehicle data to top level
                    for vehicle_name, vehicle_data in vehicles.items():
                        entry[vehicle_name] = vehicle_data
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
        # Check if we need to rename columns
        vehicles = detect_vehicles(df)
        if not any(f"{vehicle}.speed" in df.columns for vehicle in vehicles):
            logger.debug("Vehicle data need extraction from nested columns")
            # Extract speed and altitude from nested dictionaries if needed
            for column in tqdm(vehicles, desc="Separating columns"):
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
