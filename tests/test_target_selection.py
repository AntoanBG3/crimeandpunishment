"""Scene targets must resolve consistently and never reuse a departed scene."""

import unittest
from unittest.mock import MagicMock, patch

from game_engine.game_state import Game


class TestTargetSelection(unittest.TestCase):
    def setUp(self):
        self.game = Game(terminal_io=MagicMock())
        self.game.world_manager.load_all_characters()
        self.game.player_character = self.game.all_character_objects['Rodion Raskolnikov']
        self.game.current_location_name = self.game.player_character.current_location
        self.game.low_ai_data_mode = True

    def test_exact_item_and_exit_win_over_prefix_matches(self):
        handler = self.game.command_handler
        self.assertEqual(handler._resolve_prefix_match('the note', ['note', 'notebook'], 'item'),
                         ('note', False))
        self.assertEqual(handler._get_matching_exit('hall', {'Hall': 'east', 'Hallway': 'west'}),
                         ('Hall', False))

    def test_moving_clears_old_numbered_targets(self):
        self.game._display_scene_actions()
        self.assertTrue(self.game.numbered_actions_context)
        with patch.object(self.game.world_manager, 'update_current_location_details'):
            self.assertTrue(self.game.world_manager._handle_move_to_command('stairwell')[0])
        self.assertEqual(self.game.numbered_actions_context, [])

    def test_give_accepts_article_and_surname_with_shared_matcher(self):
        sonya = self.game.all_character_objects['Sonya Marmeladova']
        self.game.npcs_in_current_location = [sonya]
        self.game.player_character.inventory = [{'name': 'worn coin', 'quantity': 2}]
        self.assertTrue(self.game.handle_use_item('coin', 'the Marmeladova', 'give'))
        self.assertTrue(sonya.has_item('worn coin'))
