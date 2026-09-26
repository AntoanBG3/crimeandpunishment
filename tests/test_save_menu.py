import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from game_engine.game_state import Game
from game_engine import terminal


class TestSaveMenu(unittest.TestCase):
    def test_invalid_metadata_is_renderable(self):
        game = Game()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'savegame.json'
            path.write_text(json.dumps({'player_character_name': [], 'current_location_name': 42}))
            with patch.object(game, '_list_save_slots', return_value=[(None, str(path))]), patch.object(
                game, '_print_renderable'
            ) as output:
                self.assertTrue(game._handle_saves_command())
                self.assertIn('Saved Games', terminal.renderable_to_text(output.call_args.args[0]))

    def test_disappearing_slot_does_not_crash_picker(self):
        game = Game()
        with patch.object(game, '_list_save_slots', return_value=[('gone', '/missing/save.json')]), patch.object(
            game, '_print_renderable'
        ), patch.object(game, '_print_color'):
            self.assertTrue(game._handle_saves_command(numbered=True))

    def test_empty_picker_clears_previous_selection(self):
        game = Game()
        game.numbered_actions_context = [{'type': 'load_slot', 'target': 'gone'}]
        with patch.object(game, '_list_save_slots', return_value=[]), patch.object(game, '_print_color'):
            self.assertFalse(game._handle_saves_command(numbered=True))
        self.assertEqual(game.numbered_actions_context, [])
