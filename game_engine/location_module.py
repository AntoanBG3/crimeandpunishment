# location_module.py
import json
import logging  # It's good practice to log errors


def load_locations_data(data_path=None):
    """Loads location data from a JSON file."""
    from .game_config import get_data_path

    if data_path is None:
        data_path = get_data_path("data/locations.json")
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: The locations data file was not found at {data_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error: The locations data file at {data_path} is not a valid JSON.")
        return {}


_LOCATIONS_DATA = None


def __getattr__(name):
    global _LOCATIONS_DATA
    if name == "LOCATIONS_DATA":
        if _LOCATIONS_DATA is None:
            _LOCATIONS_DATA = load_locations_data()
        return _LOCATIONS_DATA
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
