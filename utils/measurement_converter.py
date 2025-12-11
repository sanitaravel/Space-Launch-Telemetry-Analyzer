"""
Measurement conversion utilities for OCR data extraction.
Converts various units to standard units: km/h for speed, km for altitude.
"""

def convert_speed(value: float, from_unit: str) -> float:
    """
    Convert speed to km/h.

    Args:
        value (float): The speed value.
        from_unit (str): The unit to convert from (e.g., 'mph').

    Returns:
        float: The speed in km/h.
    """
    if from_unit == 'km/h':
        return value
    elif from_unit == 'mph':
        return value * 1.60934  # 1 mile = 1.60934 km
    else:
        raise ValueError(f"Unsupported speed unit: {from_unit}")


def convert_altitude(value: float, from_unit: str) -> float:
    """
    Convert altitude to km.

    Args:
        value (float): The altitude value.
        from_unit (str): The unit to convert from (e.g., 'mi', 'ft').

    Returns:
        float: The altitude in km.
    """
    if from_unit == 'km':
        return value
    elif from_unit == 'mi':
        return value * 1.60934  # 1 mile = 1.60934 km
    elif from_unit == 'ft':
        return value * 0.0003048  # 1 foot = 0.0003048 km
    else:
        raise ValueError(f"Unsupported altitude unit: {from_unit}")


def convert_measurement(value: float, measurement_type: str, from_unit: str) -> float:
    """
    Convert a measurement based on type.

    Args:
        value (float): The value to convert.
        measurement_type (str): 'speed' or 'altitude'.
        from_unit (str): The unit to convert from.

    Returns:
        float: The converted value.
    """
    if measurement_type == 'speed':
        return convert_speed(value, from_unit)
    elif measurement_type == 'altitude':
        return convert_altitude(value, from_unit)
    else:
        raise ValueError(f"Unsupported measurement type: {measurement_type}")