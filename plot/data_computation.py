import pandas as pd
import numpy as np
from utils.constants import G_FORCE_CONVERSION
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


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