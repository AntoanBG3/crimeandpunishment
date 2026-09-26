"""Real console processes must terminate cleanly on interrupts and closed output."""

import os
import errno
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

import main


MAIN = Path(__file__).resolve().parents[1] / 'main.py'


class TestProcessShutdown(unittest.TestCase):
    def test_windows_invalid_argument_requires_broken_stdout(self):
        error = OSError(errno.EINVAL, 'invalid argument')
        output = MagicMock()
        output.isatty.return_value = False
        with patch.object(main.sys, 'platform', 'win32'), patch.object(main.sys, 'stdout', output):
            self.assertFalse(main._closed_output_pipe(error))
            output.flush.side_effect = error
            self.assertTrue(main._closed_output_pipe(error))
            self.assertFalse(main._closed_output_pipe(PermissionError('file access denied')))
            output.isatty.return_value = True
            self.assertFalse(main._closed_output_pipe(error))

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='crime shutdown ü ')
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        self.env = {key: value for key, value in os.environ.items()
                    if key not in ('GEMINI_API_KEY', 'GOOGLE_API_KEY')}
        self.env.update(HOME=self.directory, USERPROFILE=self.directory, NO_COLOR='1', PYTHONUTF8='1')

    def test_closed_output_pipe_exits_without_traceback(self):
        reader, writer = os.pipe()
        os.close(reader)
        try:
            result = subprocess.run([sys.executable, str(MAIN), '--no-tui'],
                                    input=b'', stdout=writer, stderr=subprocess.PIPE,
                                    cwd=self.directory, env=self.env, timeout=15)
        finally:
            os.close(writer)
        # Rich's documented on_broken_pipe hook exits 1; main's own boundary exits 0.
        # Both are expected shutdowns when the output consumer has gone away.
        self.assertIn(result.returncode, (0, 1), result.stderr)
        self.assertNotIn(b'Traceback', result.stderr)
        self.assertFalse(Path(self.directory, 'logs', 'crash_report.txt').exists())

    @unittest.skipIf(os.name == 'nt', 'Windows console control events require a real console')
    def test_ctrl_c_at_startup_prompt_exits_without_traceback(self):
        with subprocess.Popen([sys.executable, str(MAIN), '--no-tui'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=self.directory, env=self.env) as process:
            try:
                captured = b''
                deadline = time.monotonic() + 15
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while b'load' not in captured.lower() and time.monotonic() < deadline:
                        if selector.select(timeout=0.1):
                            chunk = os.read(process.stdout.fileno(), 4096)
                            if not chunk:
                                break
                            captured += chunk
                self.assertIn(b'load', captured.lower())
                process.send_signal(signal.SIGINT)
                _stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, stderr)
                self.assertNotIn(b'Traceback', stderr)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
