# tui_app.py
"""Textual TUI (Tier 3B).

The blocking game loop runs unchanged in a daemon worker thread. All of its
I/O already funnels through game_engine/terminal.py, so the TUI is a backend
installed there: output is posted to a scrollable RichLog pane via
call_from_thread, input blocks the game thread on a queue fed by the Input
widget, and the persistent status bar replaces the prompt_toolkit bottom
toolbar (terminal.toolbar_active() reports True, which also suppresses the
per-turn header).

Classic console mode remains the default; this module is only imported when
the player opts in (``python main.py --tui`` or ``CRIME_TUI=1``).
"""

import contextlib
import queue
import threading

from rich.rule import Rule
from rich.text import Text
from textual.app import App
from textual.binding import Binding
from textual.widgets import Input, RichLog, Static

from game_engine import terminal

# Sentinel pushed onto the input queue at shutdown so a game thread blocked
# in read() wakes up and unwinds via EOFError.
_QUIT = object()


class TextualBackend:
    """terminal.py backend that bridges the game thread and the Textual app."""

    def __init__(self, app):
        self.app = app
        self.input_queue = queue.Queue()

    def _post(self, callback, *args):
        # The app may already be shutting down while the game thread is still
        # unwinding; dropped output at that point is acceptable.
        with contextlib.suppress(Exception):
            self.app.call_from_thread(callback, *args)

    def emit(self, renderable):
        self._post(self.app.write_log, renderable)

    def read(self, prompt_text, completion=True):
        self._post(self.app.show_prompt, prompt_text, completion)
        line = self.input_queue.get()
        if line is _QUIT:
            raise EOFError
        return line

    def clear(self):
        # A rule in the log stands in for clearing the screen on move.
        self._post(self.app.write_log, Rule(style="dim"))

    @contextlib.contextmanager
    def status(self, message):
        self._post(self.app.set_status_message, message)
        try:
            yield
        finally:
            self._post(self.app.set_status_message, None)


def _default_runner():
    from game_engine.game_state import Game

    Game().run()


class CommandInput(Input):
    """Input with Tab-cycling completion fed by the game's scene context.

    First Tab completes from terminal.completion_candidates (the same
    provider the console's prompt_toolkit completer uses); repeated Tabs
    cycle through the candidates; any other key resets the cycle. The
    conversation loop disables completion via completion_enabled (the
    read(..., completion=False) flag crossing the backend seam).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.completion_enabled = True
        self._cycle_base = None
        self._cycle_candidates = []
        self._cycle_index = -1

    def on_key(self, event):
        if event.key == "tab" and self.completion_enabled:
            event.stop()
            event.prevent_default()
            self._cycle_completion()
            return
        self._reset_cycle()

    def _cycle_completion(self):
        if self._cycle_base is None:
            candidates = terminal.completion_candidates(self.value)
            if not candidates:
                return
            self._cycle_base = self.value
            self._cycle_candidates = candidates
            self._cycle_index = -1
        self._cycle_index = (self._cycle_index + 1) % len(self._cycle_candidates)
        candidate, start = self._cycle_candidates[self._cycle_index]
        # prompt_toolkit semantics: the candidate replaces the last -start
        # characters of the original input.
        cut = len(self._cycle_base) + start
        self.value = self._cycle_base[:cut] + candidate
        self.cursor_position = len(self.value)

    def _reset_cycle(self):
        self._cycle_base = None
        self._cycle_candidates = []
        self._cycle_index = -1


class CrimeAndPunishmentApp(App):
    TITLE = "Crime and Punishment"

    CSS = """
    Screen { layout: vertical; }
    #log { height: 1fr; padding: 0 1; }
    #statusbar { height: 1; padding: 0 1; color: $text-muted; background: $panel; }
    """

    BINDINGS = [Binding("ctrl+q", "quit", "Quit", priority=True)]

    def __init__(self, game_runner=None):
        super().__init__()
        self._game_runner = game_runner or _default_runner
        self._game_thread = None
        self.backend = TextualBackend(self)

    def compose(self):
        yield RichLog(wrap=True, markup=False, highlight=False, min_width=20, id="log")
        yield Static("", id="statusbar")
        yield CommandInput(placeholder="What do you do?", id="commandline")

    def on_mount(self):
        terminal.set_backend(self.backend)
        self.query_one(Input).focus()
        self._game_thread = threading.Thread(target=self._run_game, daemon=True)
        self._game_thread.start()

    def _run_game(self):
        try:
            self._game_runner()
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            terminal.set_backend(None)
            with contextlib.suppress(Exception):
                self.call_from_thread(self.exit)

    def write_log(self, renderable):
        self.query_one("#log", RichLog).write(renderable)

    def show_prompt(self, prompt_text, completion=True):
        self.refresh_status_bar()
        prompt = str(prompt_text).strip() or ">"
        command_input = self.query_one(CommandInput)
        command_input.placeholder = prompt
        command_input.completion_enabled = completion

    def refresh_status_bar(self):
        status_text = terminal.toolbar_text()
        if status_text:
            self.query_one("#statusbar", Static).update(status_text)

    def set_status_message(self, message):
        if message:
            self.query_one("#statusbar", Static).update(str(message))
        else:
            self.query_one("#statusbar", Static).update(terminal.toolbar_text() or "")

    def on_input_submitted(self, event):
        line = event.value
        event.input.value = ""
        self.write_log(Text(f"> {line}", style="dim"))
        self.backend.input_queue.put(line)

    def on_unmount(self):
        terminal.set_backend(None)
        self.backend.input_queue.put(_QUIT)


def run_tui():
    CrimeAndPunishmentApp().run()
