import unittest
from unittest.mock import MagicMock

from game_engine.command_result import CommandResult, TurnOutcome
from game_engine.game_state import Game


class TestCommandResults(unittest.TestCase):
    def test_dispatch_outcomes_preserve_legacy_unpacking(self):
        game = Game()
        game._print_color = MagicMock()
        game.load_game = MagicMock(return_value=True)
        cases = [('quit', None, TurnOutcome.QUIT),
                 ('load', 'slot', TurnOutcome.LOADED),
                 ('not-a-command', None, TurnOutcome.CONTINUE)]
        for command, argument, outcome in cases:
            result = game.command_handler._process_command(command, argument)
            self.assertIsInstance(result, CommandResult)
            self.assertIs(result.outcome, outcome)
            self.assertEqual(tuple(result), (result.action_taken, result.show_atmospherics,
                                             result.time_to_advance, result.special_flag))
