"""Independent UI contexts must not replace each other's services or settings."""

import tempfile
import threading
import unittest
from pathlib import Path

from game_engine import terminal
from game_engine.game_state import Game
from tests.test_tui import FakeBackend


class TestTerminalSessions(unittest.TestCase):
    def test_workers_keep_backends_and_settings_separate(self):
        sessions = [terminal.TerminalSession(), terminal.TerminalSession()]
        backends = [FakeBackend(), FakeBackend()]
        barrier = threading.Barrier(2)
        results = []

        def worker(index):
            with sessions[index].activate():
                terminal.set_backend(backends[index])
                terminal.set_narrative_pace(bool(index))
                terminal.set_toolbar_provider(lambda: str(index))
                barrier.wait(timeout=5)
                terminal.write_line(str(index))
                results.append((index, terminal.get_narrative_pace(), terminal.toolbar_text()))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(results), [(0, False, '0'), (1, True, '1')])
        for index, backend in enumerate(backends):
            self.assertEqual([line.plain for line in backend.emitted], [str(index)])
        self.assertIsNone(terminal.get_backend())

    def test_nested_context_restores_outer_session_even_after_failure(self):
        first, second = terminal.TerminalSession(), terminal.TerminalSession()
        first.set_toolbar_provider(lambda: 'first')
        second.set_toolbar_provider(lambda: 'second')
        with first.activate():
            with self.assertRaises(ValueError), second.activate():
                self.assertEqual(terminal.toolbar_text(), 'second')
                raise ValueError('test')
            self.assertEqual(terminal.toolbar_text(), 'first')

    def test_games_use_their_own_pacing_and_history(self):
        with tempfile.TemporaryDirectory() as directory:
            first = terminal.TerminalSession(Path(directory) / 'first')
            second = terminal.TerminalSession(Path(directory) / 'second')
            game = Game(terminal_io=first)
            first.set_backend(FakeBackend())
            game.command_handler._handle_pace_command('on')
            self.assertTrue(first.get_narrative_pace())
            self.assertFalse(second.get_narrative_pace())
            first.append_history_line('look')
            self.assertEqual(first.load_history_lines(), ['look'])
            self.assertEqual(second.load_history_lines(), [])
