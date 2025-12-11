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

    # Check for universal structure with vehicles key
    universal_keys = {"frame_number", "vehicles", "time", "real_time_seconds"}
    if universal_keys.issubset(first_entry.keys()):
        return (True, None, "universal")

    # If structure doesn't match, return invalid
    return (False, first_entry, None)