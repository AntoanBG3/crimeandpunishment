import unittest
from unittest.mock import MagicMock, patch

from prompt_toolkit.document import Document

from game_engine import terminal
from game_engine.completion import GameCompleter
from game_engine.game_state import Game


def _completions(completer, text):
    document = Document(text=text, cursor_position=len(text))
    return [c.text for c in completer.get_completions(document, None)]


class TestGameCompleter(unittest.TestCase):
    def setUp(self):
        self.context = {
            "npcs": ["Sonya Marmeladova", "Porfiry Petrovich"],
            "items": ["old newspaper", "raskolnikov's axe"],
            "inventory": ["mother's letter", "worn coin"],
            "exits": [{"name": "Haymarket Square", "description": "down the stairs"}],
        }
        self.completer = GameCompleter(lambda: self.context)

    def test_verb_completion(self):
        results = _completions(self.completer, "ta")
        self.assertIn("take", results)
        self.assertIn("talk to", results)
        self.assertNotIn("look", results)

    def test_npc_argument_completion(self):
        results = _completions(self.completer, "talk to so")
        self.assertEqual(results, ["Sonya Marmeladova"])

    def test_alias_argument_completion(self):
        # 'speak to' is an alias of 'talk to' and completes the same pool.
        results = _completions(self.completer, "speak to por")
        self.assertEqual(results, ["Porfiry Petrovich"])

    def test_exit_argument_completion(self):
        results = _completions(self.completer, "move to hay")
        self.assertEqual(results, ["Haymarket Square"])

    def test_take_completes_scene_items_only(self):
        results = _completions(self.completer, "take ")
        self.assertIn("old newspaper", results)
        self.assertNotIn("mother's letter", results)

    def test_read_completes_inventory_and_scene(self):
        results = _completions(self.completer, "read ")
        self.assertIn("mother's letter", results)
        self.assertIn("old newspaper", results)

    def test_unknown_verb_yields_nothing(self):
        self.assertEqual(_completions(self.completer, "dance with so"), [])

    def test_broken_context_provider_is_silent(self):
        completer = GameCompleter(MagicMock(side_effect=RuntimeError("boom")))
        self.assertEqual(_completions(completer, "talk to so"), [])


class TestInteractiveInputWiring(unittest.TestCase):
    def test_read_line_falls_back_to_input_when_not_a_tty(self):
        with patch("builtins.input", return_value="look") as mock_input:
            result = terminal.read_line("> ")
        self.assertEqual(result, "look")
        mock_input.assert_called_once()

    def test_game_registers_providers(self):
        game = Game()
        self.assertIsNotNone(terminal._completer_provider)
        self.assertIsNotNone(terminal._toolbar_provider)
        completer = terminal._completer_provider()
        self.assertIsInstance(completer, GameCompleter)
        # No player character yet -> toolbar stays hidden.
        self.assertIsNone(terminal._toolbar_provider())
        game.player_character = MagicMock()
        game.player_character.apparent_state = "calm"
        game.current_location_name = "Somewhere"
        self.assertIn("Somewhere", terminal._toolbar_provider())


if __name__ == "__main__":
    unittest.main()
