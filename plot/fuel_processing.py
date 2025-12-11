import pandas as pd
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


def prepare_fuel_data_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare fuel data columns to ensure they exist with proper names.

    Args:
        df (pd.DataFrame): DataFrame to prepare

    Returns:
        pd.DataFrame: DataFrame with normalized fuel column names
    """
    logger.debug("Preparing fuel data columns")

    # Detect available vehicles
    from .data_processing import detect_vehicles
    vehicles = detect_vehicles(df)
    
    # Check for nested vs flat column structure
    fuel_columns_exist = any(f"{vehicle}.fuel.lox.fullness" in df.columns for vehicle in vehicles)
    
    if not fuel_columns_exist:
        # Try to find fuel data and rename it if needed
        for vehicle in vehicles:
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

    # Detect available vehicles
    from .data_processing import detect_vehicles
    vehicles = detect_vehicles(df)
    
    # Check if we have the required columns for all vehicles
    required_cols = ['real_time_seconds']
    for vehicle in vehicles:
        required_cols.extend([
            f'{vehicle}.fuel.lox.fullness',
            f'{vehicle}.fuel.ch4.fullness'
        ])

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.warning(f"Missing required columns for fuel normalization: {missing_cols}")
        return df

    # Process each row
    normalized_count = {vehicle: 0 for vehicle in vehicles}

    for idx, row in df.iterrows():
        current_time = row['real_time_seconds']

        # Process each vehicle
        for vehicle in vehicles:
            lox_col = f'{vehicle}.fuel.lox.fullness'
            ch4_col = f'{vehicle}.fuel.ch4.fullness'
            
            lox_value = row[lox_col]
            ch4_value = row[ch4_col]

            if abs(lox_value - ch4_value) > 30:
                # Use max value in first 200s, min value after
                if current_time < 200:
                    chosen_value = max(lox_value, ch4_value)
                else:
                    chosen_value = min(lox_value, ch4_value)

                df.at[idx, lox_col] = chosen_value
                df.at[idx, ch4_col] = chosen_value
                normalized_count[vehicle] += 1

    # Log normalization results
    vehicle_counts = [f"{count} {vehicle}" for vehicle, count in normalized_count.items()]
    logger.info(f"Normalized fuel readings: {', '.join(vehicle_counts)}")
    return df