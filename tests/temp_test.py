import unittest
from unittest.mock import patch
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.game_state import Game

def char_side_effect(*args, **kwargs):
    print("MOCK load_characters_data CALLED")
    return {"TestPlayer": {"persona": "p", "greeting": "g", "default_location": "l", "accessible_locations": ["l"], "non_playable": False, "objectives": [], "inventory_items": [], "schedule": {}}}

def loc_side_effect(*args, **kwargs):
    print("MOCK load_locations_data CALLED")
    return {"l": {"description": "d", "exits": {}, "items_present": []}}

def item_side_effect(*args, **kwargs):
    print("MOCK load_default_items CALLED")
    return {}

class TemporaryTest(unittest.TestCase):
    @patch('game_engine.game_state.load_characters_data', side_effect=char_side_effect)
    @patch('game_engine.game_state.load_locations_data', side_effect=loc_side_effect)
    @patch('game_engine.game_state.load_default_items', side_effect=item_side_effect)
    def test_game_initialization(self, mock_load_items, mock_load_locs, mock_load_chars):
        print("--- RUNNING TEST ---")
        game = Game()
        print(f"game.all_character_objects: {game.all_character_objects}")
        self.assertIn("TestPlayer", game.all_character_objects)

if __name__ == '__main__':
    unittest.main()