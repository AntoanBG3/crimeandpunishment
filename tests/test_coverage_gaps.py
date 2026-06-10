"""Targeted tests for branches the main suites don't reach: path resolution
fallbacks, theme/data-loading error paths, and progression-rule validation."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import main  # noqa: E402
from game_engine import game_config, objective_progression  # noqa: E402


class TestPathResolution(unittest.TestCase):
    def test_get_base_path_prefers_meipass(self):
        with patch.object(sys, "_MEIPASS", "/tmp/meipass-extract", create=True):
            self.assertEqual(game_config.get_base_path(), "/tmp/meipass-extract")

    def test_get_data_path_missing_everywhere_returns_primary(self):
        with patch("builtins.print"):
            result = game_config.get_data_path("no/such/file.json")
        self.assertTrue(result.endswith(os.path.join("no", "such", "file.json")))

    def test_get_data_path_falls_back_to_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rel = "fallback_probe.json"
            with open(os.path.join(tmpdir, rel), "w", encoding="utf-8") as f:
                f.write("{}")
            with patch("os.getcwd", return_value=tmpdir), patch("builtins.print"):
                self.assertEqual(
                    game_config.get_data_path(rel), os.path.join(tmpdir, rel)
                )


class TestThemeAndDataLoading(unittest.TestCase):
    def test_apply_color_theme_rejects_unknown(self):
        self.assertIsNone(game_config.apply_color_theme("nonsense"))
        # None normalizes to the default theme; valid themes return their name.
        self.assertEqual(game_config.apply_color_theme(None), "default")
        self.assertEqual(game_config.apply_color_theme("default"), "default")

    def test_load_default_items_missing_file(self):
        self.assertEqual(game_config.load_default_items("/nonexistent/items.json"), {})

    def test_load_default_items_bad_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{not json")
            path = f.name
        try:
            self.assertEqual(game_config.load_default_items(path), {})
        finally:
            os.unlink(path)


class TestProgressionRules(unittest.TestCase):
    def test_target_matches(self):
        self.assertTrue(objective_progression._target_matches(None, "anything"))
        self.assertFalse(objective_progression._target_matches("Sonya", None))
        self.assertTrue(objective_progression._target_matches("Sonya", "sonya"))
        self.assertFalse(objective_progression._target_matches("Sonya", "Dunya"))

    def test_current_rules_validate_against_shipped_data(self):
        from game_engine.character_module import CHARACTERS_DATA
        from game_engine.location_module import LOCATIONS_DATA
        from game_engine.game_config import DEFAULT_ITEMS

        with patch("builtins.print") as mock_print:
            objective_progression.validate_rules(
                CHARACTERS_DATA, LOCATIONS_DATA, DEFAULT_ITEMS
            )
        mock_print.assert_not_called()  # no warnings: rules match shipped data

    def test_validate_rules_flags_content_drift(self):
        bad_rules = {
            "Ghost": [{"obj": "x", "from": "a", "to": "b"}],
            "Real": [
                {"obj": "missing_obj", "from": "a", "to": "b"},
                {
                    "obj": "obj",
                    "from": "nope",
                    "to": "also_nope",
                    "target": "Nobody",
                    "grant": "no item",
                },
            ],
        }
        characters_data = {
            "Real": {
                "objectives": [
                    {"id": "obj", "stages": [{"stage_id": "start"}]},
                ]
            }
        }
        with patch.object(objective_progression, "_RULES", bad_rules), patch(
            "builtins.print"
        ) as mock_print:
            objective_progression.validate_rules(characters_data, {}, {})
        text = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        self.assertIn("unknown character 'Ghost'", text)
        self.assertIn("unknown objective 'missing_obj'", text)
        self.assertIn("unknown from-stage 'nope'", text)
        self.assertIn("unknown to-stage 'also_nope'", text)
        self.assertIn("target 'Nobody'", text)
        self.assertIn("grant item 'no item'", text)

    def test_evaluate_progression_swallows_unexpected_errors(self):
        game = MagicMock()
        game.player_character.get_objective_by_id.side_effect = RuntimeError("boom")
        with patch.object(objective_progression, "DEBUG_LOGS", False):
            self.assertFalse(
                objective_progression.evaluate_player_progression(game, "talk_to", "Sonya")
            )


class TestChooseModeEdge(unittest.TestCase):
    def test_isatty_raising_forces_console(self):
        with patch.object(main, "DEFAULT_MODE", "tui"), patch.object(
            sys.stdin, "isatty", side_effect=ValueError
        ):
            self.assertEqual(main.choose_mode(argv=["main.py"], environ={}), "console")


if __name__ == "__main__":
    unittest.main()
