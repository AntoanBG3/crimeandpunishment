import unittest
from unittest.mock import patch, mock_open
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_engine.game_state import Game  # noqa: E402
from game_engine.character_module import Character  # noqa: E402
from game_engine.game_config import Colors, TIME_UNITS_PER_PLAYER_ACTION  # noqa: E402


class TestGameState(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.player_character = Character(
            "Test Player",
            "A brave adventurer.",
            "Hello!",
            "start_location",
            ["start_location"],
        )
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
            "visited_locations": [],
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
            "low_ai_data_mode": False,
            "player_action_count": 0,
            "color_theme": "default",
            "verbosity_level": "brief",
            "turn_headers_enabled": True,
            "command_history": [],
        }

        mock_json_dump.assert_called_once()
        args, kwargs = mock_json_dump.call_args
        self.assertEqual(args[0], expected_save_data)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("json.load")
    def test_load_game_success(self, mock_json_load, mock_open, mock_exists):
        mock_save_data = {
            "player_character_name": "Test Player",
            "current_location_name": "start_location",
            "visited_locations": [],
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
            "low_ai_data_mode": False,
            "player_action_count": 0,
            "color_theme": "default",
            "verbosity_level": "standard",
            "turn_headers_enabled": True,
            "command_history": [],
        }
        mock_json_load.return_value = mock_save_data

        with patch.dict(
            "game_engine.character_module.CHARACTERS_DATA",
            {
                "Test Player": {
                    "persona": "A brave adventurer.",
                    "greeting": "Hello!",
                    "default_location": "start_location",
                    "accessible_locations": ["start_location"],
                }
            },
            clear=True,
        ):
            result = self.game.load_game()

        self.assertTrue(result)
        self.assertEqual(self.game.game_time, 100)
        self.assertEqual(self.game.current_day, 1)
        self.assertEqual(self.game.current_location_name, "start_location")

    def test_advance_time(self):
        initial_time = self.game.game_time
        self.game.world_manager.advance_time(10)
        self.assertEqual(self.game.game_time, initial_time + 10)

    @patch("random.random", return_value=0.1)
    def test_update_npc_locations_by_schedule(self, mock_random):
        npc = Character(
            "Test NPC",
            "A scheduled NPC.",
            "Greetings.",
            "loc_A",
            ["loc_A", "loc_B"],
            schedule={"Morning": "loc_B"},
        )
        self.game.all_character_objects["Test NPC"] = npc
        self.game.game_time = 0  # Morning
        with patch.dict(
            "game_engine.location_module.LOCATIONS_DATA",
            {"loc_A": {}, "loc_B": {}},
            clear=True,
        ):
            self.game.world_manager.update_npc_locations_by_schedule()
        self.assertEqual(npc.current_location, "loc_B")

    @patch("game_engine.game_state.random.randint", return_value=5)
    def test_handle_wait_command(self, mock_randint):
        time_advanced = self.game._handle_wait_command()
        self.assertEqual(time_advanced, TIME_UNITS_PER_PLAYER_ACTION * 5)

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_game_with_slot(self, mock_json_dump, mock_open_file):
        self.game.save_game("slot1")
        mock_open_file.assert_called_once_with("savegame_slot1.json", "w")

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("json.load")
    def test_load_game_with_slot(self, mock_json_load, mock_open_file, mock_exists):
        mock_json_load.return_value = {
            "player_character_name": "Test Player",
            "current_location_name": "start_location",
            "visited_locations": [],
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
            "low_ai_data_mode": False,
            "player_action_count": 0,
            "color_theme": "default",
            "verbosity_level": "standard",
            "turn_headers_enabled": True,
            "command_history": [],
        }
        with patch.dict(
            "game_engine.character_module.CHARACTERS_DATA",
            {
                "Test Player": {
                    "persona": "A brave adventurer.",
                    "greeting": "Hello!",
                    "default_location": "start_location",
                    "accessible_locations": ["start_location"],
                }
            },
            clear=True,
        ):
            result = self.game.load_game("slot1")

        self.assertTrue(result)
        mock_exists.assert_called_once_with("savegame_slot1.json")

    def test_autosave_after_threshold_actions(self):
        self.game.autosave_interval_actions = 1
        self.game.actions_since_last_autosave = 0
        with patch.object(self.game, "save_game") as mock_save:
            self.game.world_manager._update_world_state_after_action(
                "look", True, TIME_UNITS_PER_PLAYER_ACTION
            )
        mock_save.assert_called_once_with("autosave", is_autosave=True)

    def test_get_contextual_command_examples_includes_context(self):
        self.game.npcs_in_current_location = [
            Character("Sonya", "", "", "start_location", ["start_location"])
        ]
        self.game.dynamic_location_items = {"start_location": [{"name": "coin"}]}
        with patch.dict(
            "game_engine.location_module.LOCATIONS_DATA",
            {"start_location": {"exits": {"street": "A street"}}},
            clear=True,
        ):
            examples = self.game.command_handler._get_contextual_command_examples()
        self.assertIn("look", examples)
        self.assertIn("talk to Sonya", examples)

    def test_display_help_with_category(self):
        with patch.object(self.game, "_print_color") as mock_print:
            self.game.display_help("movement")
        printed = "\n".join(call.args[0] for call in mock_print.call_args_list if call.args)
        self.assertIn("Category: movement", printed)
        self.assertIn("move to", printed)

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("json.load")
    def test_load_game_displays_recap(self, mock_json_load, mock_open_file, mock_exists):
        mock_save_data = {
            "player_character_name": "Test Player",
            "current_location_name": "start_location",
            "visited_locations": [],
            "game_time": 100,
            "current_day": 1,
            "all_character_objects_state": {"Test Player": self.game.player_character.to_dict()},
            "dynamic_location_items": {"start_location": []},
            "triggered_events": ["event1"],
            "last_significant_event_summary": "Something happened.",
            "player_notoriety_level": 1,
            "known_facts_about_crime": ["A crime was committed."],
            "key_events_occurred": ["The game started.", "Found clue", "Met inspector"],
            "current_location_description_shown_this_visit": True,
            "chosen_gemini_model": "test_model",
            "low_ai_data_mode": False,
            "player_action_count": 0,
            "color_theme": "default",
            "verbosity_level": "standard",
            "turn_headers_enabled": True,
            "command_history": [],
        }
        mock_json_load.return_value = mock_save_data

        with patch.dict(
            "game_engine.character_module.CHARACTERS_DATA",
            {
                "Test Player": {
                    "persona": "A brave adventurer.",
                    "greeting": "Hello!",
                    "default_location": "start_location",
                    "accessible_locations": ["start_location"],
                }
            },
            clear=True,
        ), patch.object(self.game, "_display_load_recap") as mock_recap:
            result = self.game.load_game()

        self.assertTrue(result)
        mock_recap.assert_called_once()

    def test_handle_status_command(self):
        with patch.object(self.game, "_print_color") as mock_print:
            self.game._handle_status_command()
            mock_print.assert_any_call(
                f"Name: {Colors.GREEN}Test Player{Colors.RESET}", Colors.WHITE
            )

    def test_get_player_input_repeat_last_command(self):
        self.game.command_history = ["look"]
        with patch.object(self.game, "_input_color", return_value="!!"), patch.object(
            self.game, "_print_color"
        ):
            command, argument = self.game.command_handler._get_player_input()
        self.assertEqual(command, "look")
        self.assertIsNone(argument)

    def test_get_player_input_repeat_without_history(self):
        self.game.command_history = []
        with patch.object(self.game, "_input_color", return_value="!!"), patch.object(
            self.game, "_print_color"
        ) as mock_print:
            command, argument = self.game.command_handler._get_player_input()
        self.assertIsNone(command)
        self.assertIsNone(argument)
        mock_print.assert_any_call("No previous command to repeat yet.", Colors.YELLOW)

    def test_process_history_command(self):
        self.game.command_history = ["look", "inventory"]
        with patch.object(self.game, "_print_color") as mock_print:
            action_taken, show_atmospherics, _, _ = self.game.command_handler._process_command(
                "history", None
            )
        self.assertFalse(action_taken)
        self.assertFalse(show_atmospherics)
        printed = "\n".join(call.args[0] for call in mock_print.call_args_list if call.args)
        self.assertIn("Recent Commands", printed)

    def test_theme_and_verbosity_commands(self):
        self.game.command_handler._process_command("theme", "mono")
        self.assertEqual(self.game.color_theme, "mono")
        self.game.command_handler._process_command("verbosity", "brief")
        self.assertEqual(self.game.verbosity_level, "brief")
        self.game.command_handler._process_command("theme", "default")


if __name__ == "__main__":
    unittest.main()
