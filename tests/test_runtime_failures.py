"""Unexpected game-worker failures must remain visible and safe to report."""

from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from game_engine import terminal
from game_engine.tui_app import CrimeAndPunishmentApp
from game_engine.diagnostics import record_failure


class TestWorkerFailures(unittest.IsolatedAsyncioTestCase):
    async def test_resize_and_ctrl_q_during_inflight_work(self):
        entered, release = threading.Event(), threading.Event()
        outcome = []

        def in_flight():
            terminal.write_line('Long wrapped narrative. ' * 30)
            entered.set()
            if not release.wait(timeout=5):
                raise TimeoutError('test worker release')
            try:
                terminal.read_line('late prompt')
            except EOFError:
                outcome.append('closed')

        with tempfile.TemporaryDirectory() as directory, patch.object(
            terminal, 'HISTORY_FILE', str(Path(directory) / 'history')
        ):
            app = CrimeAndPunishmentApp(game_runner=in_flight)

            def finish_after_shutdown():
                app.backend.closed.wait(timeout=5)
                release.set()

            helper = threading.Thread(target=finish_after_shutdown, daemon=True)
            helper.start()
            try:
                async with app.run_test(size=(30, 8)) as pilot:
                    await pilot.pause(0.1)
                    self.assertTrue(entered.is_set())
                    await pilot.resize_terminal(20, 5)
                    await pilot.resize_terminal(100, 30)
                    await pilot.press('ctrl+q')
            finally:
                release.set()
                helper.join(timeout=5)
            self.assertEqual(outcome, ['closed'])
            self.assertFalse(app._game_thread.is_alive())
            self.assertIsNone(app.game_error)

    async def test_busy_input_does_not_queue_extra_commands(self):
        from textual.widgets import Input
        from game_engine.tui_app import CommandInput

        def wait():
            terminal.read_line('> ')
            terminal.read_line('> ')

        with tempfile.TemporaryDirectory() as directory, patch.object(
            terminal, 'HISTORY_FILE', str(Path(directory) / 'history')
        ):
            app = CrimeAndPunishmentApp(game_runner=wait)
            async with app.run_test() as pilot:
                await pilot.pause(0.05)
                widget = app.query_one(CommandInput)
                app.on_input_submitted(Input.Submitted(widget, 'look'))
                app.on_input_submitted(Input.Submitted(widget, 'unwanted second command'))
                self.assertLessEqual(app.backend.input_queue.qsize(), 1)
                self.assertNotIn('unwanted second command', widget.history)

    async def test_worker_exception_keeps_diagnostic_visible(self):
        def fail():
            raise ValueError('private-key-should-not-be-logged')

        with tempfile.TemporaryDirectory() as directory, patch.object(
            terminal, 'HISTORY_FILE', str(Path(directory) / 'history')
        ), patch('game_engine.tui_app.record_failure', return_value=None):
            app = CrimeAndPunishmentApp(game_runner=fail)
            async with app.run_test() as pilot:
                await pilot.pause(0.1)
                self.assertTrue(app.is_running)
                self.assertIsNotNone(getattr(app, 'game_error', None))
                rendered = '\n'.join(str(line) for line in app.query_one('RichLog').lines)
                self.assertIn('stopped unexpectedly', rendered)
                self.assertNotIn('private-key', rendered)


class TestDiagnostics(unittest.TestCase):
    def test_report_has_frames_but_no_exception_message(self):
        with tempfile.TemporaryDirectory() as directory:
            try:
                raise RuntimeError('private-key-and-conversation')
            except RuntimeError as error:
                path = record_failure(error, directory)
            report = Path(path).read_text()
            self.assertIn('RuntimeError', report)
            self.assertIn('test_runtime_failures.py', report)
            self.assertNotIn('private-key', report)

    def test_unwritable_report_is_nonfatal(self):
        with patch('pathlib.Path.mkdir', side_effect=PermissionError):
            self.assertIsNone(record_failure(ValueError('secret')))


if __name__ == '__main__':
    unittest.main()
