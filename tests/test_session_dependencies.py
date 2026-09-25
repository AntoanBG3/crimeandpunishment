import random
import unittest
from unittest.mock import MagicMock

from game_engine.game_state import Game


class TestSessionDependencies(unittest.TestCase):
    def test_state_and_seeded_randomness_are_independent(self):
        first = Game(rng=random.Random(17), terminal_io=MagicMock())
        second = Game(rng=random.Random(17), terminal_io=MagicMock())
        first.game_time = 23
        first.visited_locations.add('somewhere')
        self.assertEqual(first.state.game_time, 23)
        self.assertEqual(second.state.game_time, 0)
        self.assertEqual(second.visited_locations, set())
        self.assertEqual([first._handle_wait_command() for _ in range(20)],
                         [second._handle_wait_command() for _ in range(20)])

    def test_character_skill_checks_use_session_rng(self):
        game = Game(rng=random.Random(17), terminal_io=MagicMock())
        game.world_manager.load_all_characters()
        for character in game.all_character_objects.values():
            self.assertIs(character.rng, game.rng)

    def test_display_uses_injected_terminal(self):
        io = MagicMock()
        game = Game(terminal_io=io)
        game._print_color('isolated', '')
        io.write_line.assert_called_once()
