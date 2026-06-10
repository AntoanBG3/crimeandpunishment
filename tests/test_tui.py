import os
import sys
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
        self.read_replies = []
        self.cleared = 0
        self.status_messages = []

    def emit(self, renderable):
        self.emitted.append(renderable)

    def read(self, prompt_text):
        self.read_prompts.append(prompt_text)
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


class TestTextualApp(unittest.IsolatedAsyncioTestCase):
    """Drive the real Textual app with a stub game loop via run_test()."""

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
