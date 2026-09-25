"""Unexpected game-worker failures must remain visible and safe to report."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from game_engine import terminal
from game_engine.tui_app import CrimeAndPunishmentApp
from game_engine.diagnostics import record_failure


class TestWorkerFailures(unittest.IsolatedAsyncioTestCase):
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
