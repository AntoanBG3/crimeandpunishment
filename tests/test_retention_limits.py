import unittest
from unittest.mock import patch

from game_engine.tui_app import CommandInput, MAX_HISTORY_ENTRIES
from scripts.audit_scenarios import build_game


class TestRetentionLimits(unittest.TestCase):
    def test_command_history_keeps_recent_entries(self):
        with patch('game_engine.terminal.load_history_lines', return_value=[]), patch(
            'game_engine.terminal.append_history_line'
        ):
            widget = CommandInput()
            for index in range(500):
                widget.record_submitted(str(index))
        self.assertEqual(len(widget.history), MAX_HISTORY_ENTRIES)
        self.assertEqual(widget.history[-1], '499')

    def test_new_days_do_not_grow_recent_event_buffer(self):
        from game_engine.game_config import MAX_TIME_UNITS_PER_DAY

        game = build_game('Porfiry Petrovich', 1729)
        for _ in range(50):
            game.world_manager.advance_time(MAX_TIME_UNITS_PER_DAY)
        self.assertLessEqual(len(game.key_events_occurred), 10)
