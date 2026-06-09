import unittest
from unittest.mock import MagicMock, patch

from game_engine import terminal
from game_engine.game_state import Game
from game_engine.game_config import Colors
from game_engine.display_mixin import DisplayMixin


class TestDisplayMixin(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.player_character = MagicMock()
        self.game.player_character.name = "Raskolnikov"
        self.game.player_character.apparent_state = "normal"
        self.game.player_character.inventory = []
        self.game.player_character.skills = {}
        self.game.player_character.objectives = []
        self.game.current_location_name = "test_loc"
        self.game.gemini_api = MagicMock()
        self.game.gemini_api.model = MagicMock()
        self.game.low_ai_data_mode = False
        self.game.verbosity_level = "standard"
        self.game.turn_headers_enabled = True
        self.game.command_history = ["look", "take axe"]
        self.game.player_action_count = 0
        self.game.tutorial_turn_limit = 5
        self.game.turn_headers_enabled = True
        self.game.player_notoriety_level = 1.0

        # Mock self.game._print_color so that we easily assert what is output
        self.mock_print_color = MagicMock()
        self.game._print_color = self.mock_print_color

    def test_print_color_real(self):
        # Unmock _print_color to test it (output is rendered by terminal.write_line)
        self.game._print_color = DisplayMixin._print_color.__get__(self.game, Game)
        with patch("builtins.print") as mock_print:
            self.game._print_color("hello", Colors.RED)
            mock_print.assert_called_once()
            self.assertIn("hello", mock_print.call_args[0][0])

    def test_input_color(self):
        with patch("builtins.input", return_value="test") as mock_input:
            res = self.game._input_color("prompt", Colors.BLUE)
            self.assertEqual(res, "test")
            mock_input.assert_called_once()
            self.assertIn("prompt", mock_input.call_args[0][0])

    def test_get_mode_label(self):
        self.assertEqual(self.game._get_mode_label(), "AI")
        self.game.low_ai_data_mode = True
        self.assertEqual(self.game._get_mode_label(), "LOW-AI")

    def test_apply_verbosity(self):
        self.assertIsNone(self.game._apply_verbosity(None))
        self.assertEqual(self.game._apply_verbosity(""), "")

        self.game.verbosity_level = "brief"
        res = self.game._apply_verbosity("One. Two. Three.")
        self.assertEqual(res, "One. Two. […more]")

        self.game.verbosity_level = "standard"
        res = self.game._apply_verbosity("Para one. More.\n\nPara two.")
        self.assertEqual(res, "Para one. More. […more]")
        # Full text is retained for the 'more' command.
        self.assertEqual(self.game._last_full_text, "Para one. More.\n\nPara two.")

        self.game.verbosity_level = "rich"
        self.assertEqual(self.game._apply_verbosity("All of it. Stays."), "All of it. Stays.")

    def test_print_turn_header(self):
        self.game.turn_headers_enabled = False
        self.game._print_turn_header()
        self.mock_print_color.assert_not_called()

        self.game.turn_headers_enabled = True
        self.game._get_current_game_time_period_str = MagicMock(return_value="Morning")
        self.game.last_turn_result_icon = "*"
        self.game._print_turn_header()
        self.mock_print_color.assert_called()

    def test_describe_item_brief(self):
        with patch.dict("game_engine.display_mixin.DEFAULT_ITEMS", {"axe": {"readable": True, "consumable": True, "value": 10, "is_notable": True}}, clear=True):
            res = self.game._describe_item_brief("axe")
            self.assertIn("readable", res)
            self.assertIn("consumable", res)
            self.assertIn("value 10", res)
            self.assertIn("notable", res)

        with patch.dict("game_engine.display_mixin.DEFAULT_ITEMS", {"stone": {}}, clear=True):
            res = self.game._describe_item_brief("stone")
            self.assertEqual(res, "common item")

    def test_describe_npc_brief(self):
        npc = MagicMock()
        npc.name = "Porfiry"
        npc.apparent_state = "thoughtful"
        self.game.npcs_in_current_location = [npc]

        self.assertEqual(self.game._describe_npc_brief("Porfiry"), "appears thoughtful")
        self.assertEqual(self.game._describe_npc_brief("Unknown"), "person here")

    def test_display_item_properties(self):
        props = {"readable": True, "consumable": True, "value": 10, "is_notable": True, "stackable": True, "owner": "me", "use_effect_player": True}
        self.game._display_item_properties(props)
        self.mock_print_color.assert_called_once_with(
            "(readable · consumable · worth 10 kopeks · notable · belongs to me · can be used)",
            Colors.DIM,
        )

        self.mock_print_color.reset_mock()
        self.game._display_item_properties({})
        self.mock_print_color.assert_not_called()

    def test_display_command_history(self):
        self.game.command_history = []
        self.game._display_command_history()
        self.mock_print_color.assert_any_call("No commands recorded yet.", Colors.DIM)

        self.game.command_history = ["look"]
        self.game._display_command_history()
        self.mock_print_color.assert_any_call("1. look", Colors.WHITE)

    def test_display_tutorial_hint(self):
        self.game.player_action_count = 0
        self.game.command_handler = MagicMock()
        self.game.command_handler._build_intent_context = MagicMock(return_value={"npcs": ["Porfiry"], "exits": [{"name": "door"}]})

        # No items in scene, so the first applicable step is 'talk'.
        self.game._display_tutorial_hint()
        self.mock_print_color.assert_called()
        self.assertIn("talk to Porfiry", self.mock_print_color.call_args[0][0])

        # Performing the step moves the hint to the next one.
        self.game._mark_tutorial_progress("talk to", "Porfiry")
        self.mock_print_color.reset_mock()
        self.game._display_tutorial_hint()
        self.assertIn("objectives", self.mock_print_color.call_args[0][0])

        self.game.player_action_count = 20  # Over limit
        self.mock_print_color.reset_mock()
        self.game._display_tutorial_hint()
        self.mock_print_color.assert_not_called()

    def test_display_atmospheric_details(self):
        self.game.gemini_api.get_atmospheric_details = MagicMock(return_value="Spooky atmosphere.")
        self.game.world_manager = MagicMock()
        self.game.display_atmospheric_details()
        self.mock_print_color.assert_any_call("Spooky atmosphere.", Colors.CYAN)

        # Test fallback (reset the per-location cooldown first)
        self.game._atmospherics_shown_at = {}
        self.game.gemini_api.model = None
        with patch("game_engine.display_mixin.STATIC_ATMOSPHERIC_DETAILS", ["Static spooky."]):
            self.game.display_atmospheric_details()
            self.mock_print_color.assert_any_call("Static spooky.", Colors.CYAN)

    def test_display_objectives(self):
        self.game.player_character.objectives = []
        self.game.display_objectives()
        self.mock_print_color.assert_any_call("You have no specific objectives at the moment.", Colors.DIM)

        self.game.player_character.objectives = [{"id": "obj1", "active": True, "completed": False, "description": "Do this"}]
        self.game.player_character.get_current_stage_for_objective = MagicMock(return_value={"description": "stage 1"})

        self.game._print_renderable = MagicMock()
        self.game.display_objectives()
        rendered = terminal.renderable_to_text(self.game._print_renderable.call_args[0][0])
        self.assertIn("Your Objectives", rendered)
        self.assertIn("Ongoing", rendered)
        self.assertIn("Do this", rendered)
        self.assertIn("Current Stage: stage 1", rendered)

    def test_display_help(self):
        self.game.color_theme = "default"
        self.game.verbosity_level = "standard"

        self.game._print_renderable = MagicMock()
        self.game.display_help("all")
        rendered = terminal.renderable_to_text(self.game._print_renderable.call_args[0][0])
        self.assertIn("Movement", rendered)
        self.assertIn("Meta", rendered)

        self.game.display_help("movement")
        rendered = terminal.renderable_to_text(self.game._print_renderable.call_args[0][0])
        self.assertIn("move to", rendered)
        self.assertNotIn("Meta", rendered)

    def test_display_load_recap(self):
        self.game.player_character.objectives = [{"id": "obj1", "active": True, "completed": False, "description": "Do this"}]
        self.game.player_character.get_current_stage_for_objective = MagicMock(return_value={"description": "stage 1"})
        self.game._get_current_game_time_period_str = MagicMock(return_value="Morning")
        self.game.key_events_occurred = ["Took the axe"]
        self.game.all_character_objects = {"Porfiry": MagicMock(is_player=False, relationship_with_player=10)}
        self.game.get_relationship_text = MagicMock(return_value="Friendly")

        self.game._display_load_recap()
        self.mock_print_color.assert_any_call("Objective: Do this (stage 1)", Colors.WHITE)
        self.mock_print_color.assert_any_call("- Took the axe", Colors.DIM)
        self.mock_print_color.assert_any_call("- Porfiry: Friendly", Colors.DIM)

    def test_display_turn_feedback(self):
        self.game.display_atmospheric_details = MagicMock()
        self.game._display_turn_feedback(True, "look")
        self.game.display_atmospheric_details.assert_called_once()

        self.game.last_significant_event_summary = "something"
        self.game._display_turn_feedback(False, "load")
        self.assertIsNone(self.game.last_significant_event_summary)

    def test_handle_status_command(self):
        self.game.all_character_objects = {"Porfiry": MagicMock(is_player=False, relationship_with_player=10)}
        self.game.get_relationship_text = MagicMock(return_value="Friendly")
        self.game.player_character.inventory = [{"name": "axe", "quantity": 1}]
        self.game.player_character.skills = {"observation": 2}
        self.game.player_notoriety_level = 1.0
        self.game.color_theme = "default"

        self.game._print_renderable = MagicMock()
        self.game._handle_status_command()
        rendered = terminal.renderable_to_text(self.game._print_renderable.call_args[0][0])
        self.assertIn("Your Status", rendered)
        self.assertIn("Observation: 2", rendered)
        self.assertIn("axe", rendered)
        self.assertIn("Porfiry: Friendly", rendered)

    def test_handle_inventory_command(self):
        self.game._print_renderable = MagicMock()
        self.game.player_character.get_inventory_description = MagicMock(return_value="You are carrying: axe")
        self.game._handle_inventory_command()
        rendered = terminal.renderable_to_text(self.game._print_renderable.call_args[0][0])
        self.assertIn("Your Inventory", rendered)
        self.assertIn("axe", rendered)

        self.game.player_character.get_inventory_description = MagicMock(return_value="You are carrying nothing.")
        self.game._handle_inventory_command()
        self.mock_print_color.assert_any_call("You are carrying nothing.", Colors.DIM)


if __name__ == "__main__":
    unittest.main()
