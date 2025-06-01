# location_module.py
import json
import logging # It's good practice to log errors
from .game_config import DEFAULT_ITEMS

def load_locations_data(data_path='data/locations.json'):
    """Loads location data from a JSON file."""
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: The locations data file was not found at {data_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error: The locations data file at {data_path} is not a valid JSON.")
        return {}

LOCATIONS_DATA = load_locations_data()