import os
import sys
import tempfile
import unittest
from unittest.mock import patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from rich.panel import Panel  # noqa: E402

from game_engine import terminal  # noqa: E402


class FakeBackend:
    def __init__(self):
        self.emitted = []
        self.read_prompts = []
        self.read_completion_flags = []
        self.read_secret_flags = []
        self.read_replies = []
        self.cleared = 0
        self.status_messages = []

    def emit(self, renderable):
        self.emitted.append(renderable)

    def read(self, prompt_text, completion=True, secret=False):
        self.read_prompts.append(prompt_text)
        self.read_completion_flags.append(completion)
        self.read_secret_flags.append(secret)
        return self.read_replies.pop(0) if self.read_replies else ""

    def clear(self):
        self.cleared += 1

    def status(self, message):
        self.status_messages.append(message)
        import contextlib

        return contextlib.nullcontext()


class TestTerminalBackendSeam(unittest.TestCase):
    """With a backend installed, every terminal function must route through it
    instead of printing; with none, the classic console path is untouched."""

    def setUp(self):
        self.backend = FakeBackend()
        terminal.set_backend(self.backend)
        self.addCleanup(terminal.set_backend, None)

    def test_write_line_routes_to_backend(self):
        with patch("builtins.print") as mock_print:
            terminal.write_line("hello", "")
        mock_print.assert_not_called()
        self.assertEqual(len(self.backend.emitted), 1)
        self.assertEqual(self.backend.emitted[0].plain, "hello")

    def test_write_renderable_routes_to_backend_without_paging(self):
        panel = Panel("body")
        with patch("builtins.print") as mock_print:
            terminal.write_renderable(panel, allow_paging=True)
        mock_print.assert_not_called()
        self.assertIs(self.backend.emitted[0], panel)

    def test_write_dialogue_routes_to_backend(self):
        with patch("builtins.print") as mock_print:
            terminal.write_dialogue("Sonya: 'Hello.'")
        mock_print.assert_not_called()
        self.assertEqual(self.backend.emitted[0].plain, "Sonya: 'Hello.'")

    def test_read_line_blocks_on_backend(self):
        self.backend.read_replies.append("look")
        with patch("builtins.input") as mock_input:
            result = terminal.read_line("> ", "")
        mock_input.assert_not_called()
        self.assertEqual(result, "look")
        self.assertEqual(self.backend.read_prompts, ["> "])
        self.assertEqual(self.backend.read_completion_flags, [True])

    def test_read_line_completion_flag_crosses_the_seam(self):
        self.backend.read_replies.append("hello")
        terminal.read_line("You: ", "", completion=False)
        self.assertEqual(self.backend.read_completion_flags, [False])

    def test_read_line_secret_flag_crosses_the_seam(self):
        self.backend.read_replies.append("key-123")
        result = terminal.read_line("API key: ", "", secret=True)
        self.assertEqual(result, "key-123")
        self.assertEqual(self.backend.read_secret_flags, [True])

    def test_clear_screen_routes_to_backend(self):
        terminal.clear_screen()
        self.assertEqual(self.backend.cleared, 1)

    def test_status_routes_to_backend(self):
        with terminal.status("thinking"):
            pass
        self.assertEqual(self.backend.status_messages, ["thinking"])

    def test_toolbar_active_true_with_backend(self):
        self.assertTrue(terminal.toolbar_active())

    def test_blank_line_tracking_still_works(self):
        terminal.write_line("text")
        terminal.ensure_blank_line()
        self.assertEqual(len(self.backend.emitted), 2)
        self.assertEqual(self.backend.emitted[1].plain, "")
        terminal.ensure_blank_line()
        self.assertEqual(len(self.backend.emitted), 2)

    def test_write_narrative_paces_through_backend(self):
        terminal.set_narrative_pace(True)
        self.addCleanup(terminal.set_narrative_pace, False)
        with patch("game_engine.terminal.time.sleep") as mock_sleep:
            terminal.write_narrative("First paragraph.\n\nSecond paragraph.")
        mock_sleep.assert_called()
        plains = [e.plain for e in self.backend.emitted if e.plain.strip()]
        self.assertEqual(plains, ["First paragraph.", "Second paragraph."])


class TestTerminalWithoutBackend(unittest.TestCase):
    def test_toolbar_text_without_provider(self):
        self.assertIsNone(terminal.toolbar_text())

    def test_toolbar_text_swallows_provider_errors(self):
        terminal.set_toolbar_provider(lambda: 1 / 0)
        self.addCleanup(terminal.set_toolbar_provider, None)
        self.assertIsNone(terminal.toolbar_text())

    def test_write_line_prints_when_no_backend(self):
        with patch("builtins.print") as mock_print:
            terminal.write_line("plain path")
        mock_print.assert_called_once()


class TestBackendProtocolContract(unittest.TestCase):
    """The exact backend surface terminal.py relies on. A signature change
    here must fail loudly, not as a TypeError at runtime in a thread."""

    REQUIRED = {
        "emit": ["renderable"],
        "read": ["prompt_text", "completion", "secret"],
        "clear": [],
        "status": ["message"],
    }

    def _check(self, backend_cls):
        import inspect

        for name, expected in self.REQUIRED.items():
            method = getattr(backend_cls, name)
            actual = [p for p in inspect.signature(method).parameters if p != "self"]
            self.assertEqual(actual, expected, f"{backend_cls.__name__}.{name}")

    def test_textual_backend_matches_protocol(self):
        from game_engine.tui_app import TextualBackend

        self._check(TextualBackend)

    def test_fake_backend_matches_protocol(self):
        self._check(FakeBackend)

    def test_no_backend_installed_by_default(self):
        # The whole test suite relies on the console path being the default;
        # nothing may leave a backend installed behind it.
        self.assertIsNone(terminal.get_backend())


class TestSharedHistory(unittest.TestCase):
    """terminal.load_history_lines/append_history_line must speak
    prompt_toolkit FileHistory's on-disk format exactly."""

    def test_round_trip_with_prompt_toolkit_filehistory(self):
        from prompt_toolkit.history import FileHistory

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "history")
            with patch.object(terminal, "HISTORY_FILE", path):
                history = FileHistory(path)
                history.store_string("look")
                history.store_string("move to stairwell")
                history.store_string("line one\nline two")
                self.assertEqual(
                    terminal.load_history_lines(),
                    ["look", "move to stairwell", "line one\nline two"],
                )
                terminal.append_history_line("inventory")
                newest_first = list(FileHistory(path).load_history_strings())
                self.assertEqual(newest_first[0], "inventory")
                self.assertEqual(terminal.load_history_lines()[-1], "inventory")

    def test_missing_file_and_blank_lines_are_safe(self):
        with patch.object(terminal, "HISTORY_FILE", "/nonexistent/dir/history"):
            self.assertEqual(terminal.load_history_lines(), [])
            terminal.append_history_line("ignored")  # must not raise
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "history")
            with patch.object(terminal, "HISTORY_FILE", path):
                terminal.append_history_line("   ")  # blank: not recorded
                self.assertEqual(terminal.load_history_lines(), [])


class TestTextualApp(unittest.IsolatedAsyncioTestCase):
    """Drive the real Textual app with a stub game loop via run_test()."""

    def setUp(self):
        # Never let app tests touch the user's real history file.
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        patcher = patch.object(
            terminal, "HISTORY_FILE", os.path.join(self._tmpdir.name, "history")
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_round_trip_through_the_app(self):
        from game_engine.tui_app import CrimeAndPunishmentApp

        transcript = []

        def stub_game():
            line = terminal.read_line("What do you do? ")
            transcript.append(line)
            terminal.write_line("You look around the garret.")
            terminal.read_line("> ")  # park until shutdown unblocks us

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            input_widget = app.query_one("Input")
            self.assertEqual(input_widget.placeholder, "What do you do?")
            input_widget.value = "look"
            await pilot.press("enter")
            await pilot.pause(0.2)
            log = app.query_one("RichLog")
            rendered = "\n".join(str(line) for line in log.lines)
            self.assertIn("look", rendered)
            self.assertIn("You look around the garret.", rendered)
        self.assertEqual(transcript, ["look"])
        self.assertIsNone(terminal.get_backend())

    async def test_quit_sentinel_unblocks_game_thread(self):
        from game_engine.tui_app import CrimeAndPunishmentApp

        outcome = {}

        def stub_game():
            try:
                terminal.read_line("> ")
            except EOFError:
                outcome["eof"] = True

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            await app.action_quit()
        app._game_thread.join(timeout=2)
        self.assertTrue(outcome.get("eof"))

    async def test_tab_completion_cycles_in_input(self):
        from game_engine.completion import GameCompleter
        from game_engine.tui_app import CrimeAndPunishmentApp

        terminal.set_completer_provider(
            lambda: GameCompleter(lambda: {"items": ["apple", "axe"]})
        )
        self.addCleanup(terminal.set_completer_provider, None)

        def stub_game():
            terminal.read_line("> ")  # park; completion stays enabled

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            command_input = app.query_one("CommandInput")
            command_input.value = "take a"
            command_input.cursor_position = len(command_input.value)
            await pilot.press("tab")
            self.assertEqual(command_input.value, "take apple")
            await pilot.press("tab")
            self.assertEqual(command_input.value, "take axe")
            await pilot.press("tab")  # wraps around
            self.assertEqual(command_input.value, "take apple")
            # Typing resets the cycle.
            await pilot.press("x")
            self.assertIsNone(command_input._cycle_base)

    async def test_tab_does_nothing_when_completion_disabled(self):
        from game_engine.completion import GameCompleter
        from game_engine.tui_app import CrimeAndPunishmentApp

        terminal.set_completer_provider(
            lambda: GameCompleter(lambda: {"items": ["apple"]})
        )
        self.addCleanup(terminal.set_completer_provider, None)

        def stub_game():
            terminal.read_line("You: ", completion=False)  # dialogue mode

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            command_input = app.query_one("CommandInput")
            self.assertFalse(command_input.completion_enabled)
            command_input.value = "take a"
            command_input.cursor_position = len(command_input.value)
            await pilot.press("tab")
            self.assertEqual(command_input.value, "take a")

    async def test_history_walk_with_draft_restore(self):
        from game_engine.tui_app import CrimeAndPunishmentApp

        terminal.append_history_line("look")
        terminal.append_history_line("inventory")

        def stub_game():
            terminal.read_line("> ")  # park

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            command_input = app.query_one("CommandInput")
            self.assertEqual(command_input.history, ["look", "inventory"])
            command_input.value = "dra"
            command_input.cursor_position = 3
            await pilot.press("up")
            self.assertEqual(command_input.value, "inventory")
            await pilot.press("up")
            self.assertEqual(command_input.value, "look")
            await pilot.press("up")  # clamped at the oldest entry
            self.assertEqual(command_input.value, "look")
            await pilot.press("down")
            self.assertEqual(command_input.value, "inventory")
            await pilot.press("down")  # back past the newest: draft restored
            self.assertEqual(command_input.value, "dra")

    async def test_submitted_lines_persist_to_history_file(self):
        from game_engine.tui_app import CrimeAndPunishmentApp

        def stub_game():
            terminal.read_line("> ")
            terminal.read_line("> ")  # park

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            command_input = app.query_one("CommandInput")
            command_input.value = "objectives"
            await pilot.press("enter")
            await pilot.pause(0.2)
            self.assertEqual(command_input.history[-1], "objectives")
        self.assertEqual(terminal.load_history_lines(), ["objectives"])

    async def test_secret_prompt_masks_echo_and_skips_history(self):
        from game_engine.tui_app import CrimeAndPunishmentApp

        captured = {}

        def stub_game():
            captured["key"] = terminal.read_line("API key: ", secret=True)
            terminal.read_line("> ")  # park

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            command_input = app.query_one("CommandInput")
            self.assertTrue(command_input.password)
            command_input.value = "key-secret-123"
            await pilot.press("enter")
            await pilot.pause(0.2)
            log = app.query_one("RichLog")
            rendered = "\n".join(str(line) for line in log.lines)
            self.assertIn("> ********", rendered)
            self.assertNotIn("key-secret-123", rendered)
            self.assertNotIn("key-secret-123", command_input.history)
            # The next, non-secret prompt unmasks the input.
            self.assertFalse(command_input.password)
        self.assertEqual(captured["key"], "key-secret-123")
        self.assertEqual(terminal.load_history_lines(), [])

    async def test_exit_joins_game_thread_through_in_flight_work(self):
        import threading
        import time

        from game_engine.tui_app import CrimeAndPunishmentApp

        finished_cleanly = threading.Event()

        def stub_game():
            try:
                terminal.read_line("> ")
            except EOFError:
                time.sleep(0.3)  # simulates an in-flight autosave
                finished_cleanly.set()

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            await app.action_quit()
        # on_unmount joined the thread, so the "save" completed before teardown.
        self.assertTrue(finished_cleanly.is_set())

    async def test_paced_narrative_renders_incrementally_in_log(self):
        from game_engine.tui_app import CrimeAndPunishmentApp

        def stub_game():
            terminal.set_narrative_pace(True)
            try:
                terminal.write_narrative("First beat.\n\nSecond beat.")
            finally:
                terminal.set_narrative_pace(False)
            terminal.read_line("> ")  # park

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        with patch("game_engine.terminal.time.sleep"):
            async with app.run_test() as pilot:
                await pilot.pause(0.5)
                log = app.query_one("RichLog")
                rendered = "\n".join(str(line) for line in log.lines)
                self.assertIn("First beat.", rendered)
                self.assertIn("Second beat.", rendered)

    async def test_status_message_shows_and_clears(self):
        from game_engine.tui_app import CrimeAndPunishmentApp

        import threading

        proceed = threading.Event()

        def stub_game():
            with terminal.status("The city holds its breath…"):
                proceed.wait(timeout=5)
            terminal.read_line("> ")

        app = CrimeAndPunishmentApp(game_runner=stub_game)
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            bar = app.query_one("#statusbar")
            self.assertIn("holds its breath", str(bar.render()))
            proceed.set()
            await pilot.pause(0.2)
            self.assertNotIn("holds its breath", str(bar.render()))


if __name__ == "__main__":
    unittest.main()
