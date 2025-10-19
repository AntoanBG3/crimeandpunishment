import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.game_state import Game
from game_engine.character_module import Character
from game_engine.game_config import Colors, TIME_UNITS_PER_PLAYER_ACTION

class TestGameState(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.player_character = Character("Test Player", "A brave adventurer.", "Hello!", "start_location", ["start_location"])
        self.game.current_location_name = "start_location"
        self.game.game_time = 100
        self.game.current_day = 1
        self.game.all_character_objects = {"Test Player": self.game.player_character}
        self.game.dynamic_location_items = {"start_location": []}
        self.game.event_manager.triggered_events = {"event1"}
        self.game.last_significant_event_summary = "Something happened."
        self.game.player_notoriety_level = 1
        self.game.known_facts_about_crime = ["A crime was committed."]
        self.game.key_events_occurred = ["The game started."]
        self.game.current_location_description_shown_this_visit = True
        self.game.gemini_api.chosen_model_name = "test_model"
        self.game.low_ai_data_mode = False

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_game(self, mock_json_dump, mock_open):
        self.game.save_game()

        mock_open.assert_called_once_with("savegame.json", "w")

        expected_save_data = {
            "player_character_name": "Test Player",
            "current_location_name": "start_location",
            "game_time": 100,
            "current_day": 1,
            "all_character_objects_state": {"Test Player": self.game.player_character.to_dict()},
            "dynamic_location_items": {"start_location": []},
            "triggered_events": ["event1"],
            "last_significant_event_summary": "Something happened.",
            "player_notoriety_level": 1,
            "known_facts_about_crime": ["A crime was committed."],
            "key_events_occurred": ["The game started."],
            "current_location_description_shown_this_visit": True,
            "chosen_gemini_model": "test_model",
            "low_ai_data_mode": False
        }

        mock_json_dump.assert_called_once()
        args, kwargs = mock_json_dump.call_args
        self.assertEqual(args[0], expected_save_data)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='{}')
    @patch("json.load")
    def test_load_game_success(self, mock_json_load, mock_open, mock_exists):
        mock_save_data = {
            "player_character_name": "Test Player",
            "current_location_name": "start_location",
            "game_time": 100,
            "current_day": 1,
            "all_character_objects_state": {"Test Player": self.game.player_character.to_dict()},
            "dynamic_location_items": {"start_location": []},
            "triggered_events": ["event1"],
            "last_significant_event_summary": "Something happened.",
            "player_notoriety_level": 1,
            "known_facts_about_crime": ["A crime was committed."],
            "key_events_occurred": ["The game started."],
            "current_location_description_shown_this_visit": True,
            "chosen_gemini_model": "test_model",
            "low_ai_data_mode": False
        }
        mock_json_load.return_value = mock_save_data

        with patch('game_engine.game_state.CHARACTERS_DATA', {"Test Player": {"persona": "A brave adventurer.", "greeting": "Hello!", "default_location": "start_location", "accessible_locations": ["start_location"]}}):
            result = self.game.load_game()

        self.assertTrue(result)
        self.assertEqual(self.game.game_time, 100)
        self.assertEqual(self.game.current_day, 1)
        self.assertEqual(self.game.current_location_name, "start_location")

    def test_advance_time(self):
        initial_time = self.game.game_time
        self.game.advance_time(10)
        self.assertEqual(self.game.game_time, initial_time + 10)

    @patch('random.random', return_value=0.1)
    def test_update_npc_locations_by_schedule(self, mock_random):
        npc = Character("Test NPC", "A scheduled NPC.", "Greetings.", "loc_A", ["loc_A", "loc_B"], schedule={"Morning": "loc_B"})
        self.game.all_character_objects["Test NPC"] = npc
        self.game.game_time = 0 # Morning
        with patch('game_engine.game_state.LOCATIONS_DATA', {"loc_A": {}, "loc_B": {}}):
            self.game.update_npc_locations_by_schedule()
        self.assertEqual(npc.current_location, "loc_B")

    @patch('game_engine.game_state.random.randint', return_value=5)
    def test_handle_wait_command(self, mock_randint):
        time_advanced = self.game._handle_wait_command()
        self.assertEqual(time_advanced, TIME_UNITS_PER_PLAYER_ACTION * 5)

    def test_handle_status_command(self):
        with patch.object(self.game, '_print_color') as mock_print:
            self.game._handle_status_command()
            mock_print.assert_any_call(f"Name: {Colors.GREEN}Test Player{Colors.RESET}", Colors.WHITE)


if __name__ == '__main__':
    unittest.main()
