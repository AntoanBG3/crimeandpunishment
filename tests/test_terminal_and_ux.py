import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from game_engine import terminal
from game_engine.game_state import Game
from game_engine.game_config import Colors


class TestTerminal(unittest.TestCase):
    def test_write_line_wraps_long_text(self):
        long_text = ("word " * 60).strip()
        with patch("builtins.print") as mock_print:
            terminal.write_line(long_text)
        out = mock_print.call_args[0][0]
        lines = [line for line in out.splitlines() if line.strip()]
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(len(line) <= terminal.MAX_TEXT_WIDTH for line in lines))

    def test_ensure_blank_line_never_stacks(self):
        with patch("builtins.print"):
            terminal.write_line("content")
        self.assertFalse(terminal._last_line_blank)
        with patch("builtins.print") as mock_print:
            terminal.ensure_blank_line()
            terminal.ensure_blank_line()
        self.assertEqual(mock_print.call_count, 1)

    def test_markdown_emphasis_becomes_italics(self):
        rendered = terminal._render("a *strong* word")
        self.assertEqual(rendered.plain, "a strong word")

    def test_embedded_ansi_colors_are_parsed(self):
        rendered = terminal._render(f"{Colors.YELLOW}Name:{Colors.RESET} hello")
        self.assertEqual(rendered.plain, "Name: hello")

    def test_separator_is_width_bounded(self):
        sep = terminal.separator()
        self.assertGreaterEqual(len(sep), terminal.MIN_TEXT_WIDTH)
        self.assertLessEqual(len(sep), terminal.MAX_TEXT_WIDTH)

    def test_write_narrative_single_paragraph_passthrough(self):
        with patch("builtins.print") as mock_print:
            terminal.write_narrative("One paragraph only.")
        self.assertTrue(mock_print.called)

    def test_write_narrative_unpaced_prints_everything_at_once(self):
        terminal.set_narrative_pace(False)
        with patch("builtins.print") as mock_print:
            terminal.write_narrative("One para.\n\nTwo para.")
        combined = "".join(call.args[0] for call in mock_print.call_args_list)
        self.assertIn("One para.", combined)
        self.assertIn("Two para.", combined)

    def test_status_is_silent_outside_a_terminal(self):
        # Under the test runner stdout is not a tty, so status() must be a no-op
        # context manager rather than an animated spinner.
        with patch("builtins.print") as mock_print:
            with terminal.status("thinking"):
                pass
        mock_print.assert_not_called()

    def test_renderable_to_text(self):
        from rich.panel import Panel

        rendered = terminal.renderable_to_text(Panel("hello", title="Box"))
        self.assertIn("hello", rendered)
        self.assertIn("Box", rendered)

    def test_write_dialogue_hanging_indent(self):
        quote = "Speaker: " + ("word " * 40).strip()
        with patch("builtins.print") as mock_print:
            terminal.write_dialogue(quote)
        lines = mock_print.call_args[0][0].splitlines()
        self.assertGreater(len(lines), 1)
        self.assertFalse(lines[0].startswith(" "))
        for continuation in lines[1:]:
            self.assertTrue(continuation.startswith(" " * terminal.DIALOGUE_HANGING_INDENT))


class TestUXCommands(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.player_character = MagicMock()
        self.game.player_character.apparent_state = "normal"
        self.game.current_location_name = "test_loc"
        self.game._print_color = MagicMock()
        self.game._print_block = MagicMock()

    def test_more_command_without_text(self):
        self.game._handle_more_command()
        self.game._print_color.assert_called_with(
            "There is nothing more to reveal right now.", Colors.YELLOW
        )

    def test_more_command_reveals_full_text(self):
        self.game.verbosity_level = "brief"
        trimmed = self.game._apply_verbosity("One. Two. Three. Four.")
        self.assertTrue(trimmed.endswith("[…more]"))
        self.game._handle_more_command()
        self.game._print_block.assert_called_with("One. Two. Three. Four.", Colors.CYAN)

    def test_pace_command_toggles(self):
        handler = self.game.command_handler
        handler._handle_pace_command("on")
        self.assertTrue(terminal.narrative_pace_enabled)
        handler._handle_pace_command("off")
        self.assertFalse(terminal.narrative_pace_enabled)
        handler._handle_pace_command("sideways")
        self.game._print_color.assert_called_with(
            "Invalid value. Use 'pace on' or 'pace off'.", Colors.YELLOW
        )

    def test_pace_command_reports_current_state(self):
        terminal.set_narrative_pace(False)
        self.game.command_handler._handle_pace_command(None)
        message = self.game._print_color.call_args[0][0]
        self.assertIn("off", message)

    def test_saves_command_no_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            previous_dir = os.getcwd()
            os.chdir(tmp_dir)
            try:
                self.game._handle_saves_command()
            finally:
                os.chdir(previous_dir)
        self.game._print_color.assert_called_with("No saved games found.", Colors.YELLOW)

    def test_saves_command_lists_slots(self):
        self.game._print_renderable = MagicMock()
        with tempfile.TemporaryDirectory() as tmp_dir:
            previous_dir = os.getcwd()
            os.chdir(tmp_dir)
            try:
                with open("savegame_test.json", "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "player_character_name": "Sonya Marmeladova",
                            "current_day": 3,
                            "current_location_name": "Haymarket Square",
                        },
                        f,
                    )
                self.game._handle_saves_command()
            finally:
                os.chdir(previous_dir)
        rendered = terminal.renderable_to_text(
            self.game._print_renderable.call_args[0][0], width=120
        )
        self.assertIn("test", rendered)
        self.assertIn("Sonya Marmeladova", rendered)
        self.assertIn("Haymarket Square", rendered)

    def test_load_without_slot_offers_numbered_picker(self):
        self.game._print_renderable = MagicMock()
        self.game.load_game = MagicMock()
        with tempfile.TemporaryDirectory() as tmp_dir:
            previous_dir = os.getcwd()
            os.chdir(tmp_dir)
            try:
                for slot_file in ("savegame.json", "savegame_alt.json"):
                    with open(slot_file, "w", encoding="utf-8") as f:
                        json.dump({"player_character_name": "P", "current_day": 1}, f)
                result = self.game.command_handler._process_command("load", None)
            finally:
                os.chdir(previous_dir)
        self.assertEqual(result, (False, False, 0, False))
        self.game.load_game.assert_not_called()
        slots = [a for a in self.game.numbered_actions_context if a["type"] == "load_slot"]
        self.assertEqual(len(slots), 2)
        # The default slot uses "" so numeric dispatch loads it instead of re-prompting.
        self.assertIn("", [a["target"] for a in slots])
        with patch.object(self.game, "_input_color", return_value="1"):
            command, argument = self.game.command_handler._get_player_input()
        self.assertEqual(command, "load")

    def test_manual_key_input_skips_without_tty(self):
        from game_engine.gemini_interactions import GeminiAPI

        api = GeminiAPI()
        api._print_color_func = MagicMock()
        api._input_color_func = MagicMock()
        with patch("sys.stdin.isatty", return_value=False):
            result = api._handle_manual_key_input()
        self.assertEqual(result, {"api_configured": False, "low_ai_preference": False})
        api._input_color_func.assert_not_called()

    def test_look_at_strips_connective_words(self):
        self.game._handle_look_at_location_item = MagicMock(return_value=True)
        self.game._handle_look_command("at old newspaper")
        self.game._handle_look_at_location_item.assert_called_once_with("old newspaper")

    def test_targeted_look_keeps_numbered_actions_and_skips_scene_listing(self):
        self.game._handle_look_at_location_item = MagicMock(return_value=True)
        self.game.world_manager = MagicMock()
        self.game.numbered_actions_context = [{"type": "talk", "target": "X", "display": "X"}]
        self.game._handle_look_command("the axe", show_full_look_details=True)
        self.assertEqual(len(self.game.numbered_actions_context), 1)
        self.game.world_manager.update_current_location_details.assert_not_called()

    def test_prefix_match_falls_back_to_word_boundaries(self):
        handler = self.game.command_handler
        match, ambiguous = handler._resolve_prefix_match(
            "axe", ["raskolnikov's axe", "old newspaper"], "item"
        )
        self.assertEqual(match, "raskolnikov's axe")
        self.assertFalse(ambiguous)
        # No match at all stays a clean miss.
        match, ambiguous = handler._resolve_prefix_match("sled", ["old newspaper"], "item")
        self.assertIsNone(match)

    def test_atmospherics_cooldown_skips_repeat(self):
        self.game.gemini_api = MagicMock()
        self.game.gemini_api.model = None
        self.game.low_ai_data_mode = True
        self.game.world_manager = MagicMock()
        self.game.player_action_count = 0
        with patch(
            "game_engine.display_mixin.STATIC_ATMOSPHERIC_DETAILS", ["Still air."]
        ):
            self.game.display_atmospheric_details()
            calls_after_first = self.game._print_block.call_count
            self.game.display_atmospheric_details()
        self.assertEqual(self.game._print_block.call_count, calls_after_first)

    def test_full_description_not_repeated_on_immediate_look(self):
        from game_engine.world_manager import WorldManager

        game = self.game
        game.player_action_count = 0
        game.visited_locations = set()
        game.current_location_description_shown_this_visit = False
        game.npcs_in_current_location = []
        game.all_character_objects = {}
        wm = WorldManager(game)
        location_data = {
            "A": {"description": "First sentence. Second sentence.", "time_effects": {}}
        }
        game.current_location_name = "A"
        with patch("game_engine.world_manager.LOCATIONS_DATA", location_data):
            wm.update_current_location_details(from_explicit_look_cmd=False)
            full_calls = [
                c for c in game._print_color.call_args_list
                if "Second sentence." in str(c.args[0])
            ]
            self.assertEqual(len(full_calls), 1)
            # An immediate explicit look must show the brief form, not repeat the full text.
            game.current_location_description_shown_this_visit = False
            wm.update_current_location_details(from_explicit_look_cmd=True)
            full_calls = [
                c for c in game._print_color.call_args_list
                if "Second sentence." in str(c.args[0])
            ]
            self.assertEqual(len(full_calls), 1)
            brief_calls = [
                c for c in game._print_color.call_args_list
                if c.args[0] == "First sentence."
            ]
            self.assertEqual(len(brief_calls), 1)


if __name__ == "__main__":
    unittest.main()
