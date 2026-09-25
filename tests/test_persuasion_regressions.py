import unittest
from unittest.mock import MagicMock, patch

from game_engine.game_state import Game
from game_engine.game_config import TIME_UNITS_PER_PLAYER_ACTION


class TestPersuasionRegressions(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.world_manager.load_all_characters()
        self.game.player_character = self.game.all_character_objects['Porfiry Petrovich']
        self.game.player_character.is_player = True
        self.game.current_location_name = "Raskolnikov's Garret"
        self.game.npcs_in_current_location = [self.game.all_character_objects['Rodion Raskolnikov']]
        self.game._print_color = MagicMock()
        self.game._print_dialogue = MagicMock()
        self.game._print_narrative = MagicMock()

    def test_persuasion_advances_world_time_once(self):
        with patch.object(self.game.world_manager, 'advance_time') as advance:
            result = self.game.command_handler._process_command('persuade', ('Rodion', 'confess'))
            self.game.world_manager._update_world_state_after_action('persuade', result[0], result[2])
        advance.assert_called_once_with(TIME_UNITS_PER_PLAYER_ACTION)

    def test_article_and_surname_matching_and_low_ai_mode(self):
        self.game.low_ai_data_mode = True
        self.game.gemini_api.model = object()
        self.game.gemini_api.get_npc_dialogue_persuasion_attempt = MagicMock(return_value='API text')
        result = self.game._handle_persuade_command(('the Raskolnikov', 'confess'))
        self.assertTrue(result[0])
        self.game.gemini_api.get_npc_dialogue_persuasion_attempt.assert_not_called()
