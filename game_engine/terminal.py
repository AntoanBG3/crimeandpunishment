# terminal.py
"""Single output funnel for the game.

Rich does the rendering work: word-wrapping at the terminal width (capped to
MAX_TEXT_WIDTH), parsing the ANSI color codes that call sites embed via the
Colors class, and honoring NO_COLOR / dumb terminals / piped output. The final
emit still goes through builtins.print so tests can keep patching it.

A UI backend can be installed with set_backend() (the Textual TUI does this);
when one is active, output is handed to the backend as Rich renderables and
input blocks on the backend instead of the console. With no backend (the
default), behavior is the classic console
path described above.
"""

from collections import deque
import contextlib
from contextvars import ContextVar
from types import SimpleNamespace
import os
import re
import sys
import time

from rich.console import Console
from rich.text import Text

MAX_TEXT_WIDTH = 88
MIN_TEXT_WIDTH = 40

_console = Console(highlight=False, soft_wrap=False)

# Active UI backend; None means the classic console path. A backend must
# provide: emit(renderable), read(prompt_text, completion=True,
# secret=False) -> str, clear(), status(message) -> context manager.
_backend = None

# Tracks whether the last emitted line was blank, so blocks can guarantee a
# single separating blank line without ever stacking two.
_last_line_blank = True


def set_backend(backend):
    """Install (or with None, remove) a UI backend such as the Textual TUI."""
    _current()._backend = backend


def get_backend():
    return _current()._backend


# Optional paragraph-by-paragraph reveal for major narrative beats (dreams,
# endings). Off by default; toggled by the 'pace' command.
narrative_pace_enabled = False
NARRATIVE_PACE_DELAY_SECONDS = 0.8

# AI text sometimes carries markdown-style *emphasis*; render it as italics
# instead of leaving literal asterisks.
_EMPHASIS_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def set_narrative_pace(enabled):
    _current().narrative_pace_enabled = bool(enabled)


def render_width():
    width = _current()._console.size.width or 80
    return max(MIN_TEXT_WIDTH, min(width, MAX_TEXT_WIDTH))


def _render(text, color=""):
    body = f"{color}{text}" if color else str(text)
    body = _EMPHASIS_RE.sub("\x1b[3m\\1\x1b[23m", body)
    return Text.from_ansi(body)


def write_line(text, color="", end="\n"):
    rich_text = _render("" if text is None else str(text), color)
    if _current()._backend is not None:
        _current()._backend.emit(rich_text)
        _current()._last_line_blank = not rich_text.plain.strip()
        return
    with _current()._console.capture() as capture:
        _current()._console.print(rich_text, end=end, width=render_width())
    print(capture.get(), end="")
    if end == "\n":
        _current()._last_line_blank = not rich_text.plain.strip()


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def write_renderable(renderable, allow_paging=False):
    """Print a Rich renderable (Panel, Table, ...) through the same funnel.

    With allow_paging, output taller than the terminal goes through the
    system pager (plain text) instead of scrolling past."""
    if _current()._backend is not None:
        # The TUI log pane scrolls, so paging is unnecessary there.
        _current()._backend.emit(renderable)
        _current()._last_line_blank = False
        return
    with _current()._console.capture() as capture:
        _current()._console.print(renderable, width=render_width())
    rendered = capture.get()
    if (
        allow_paging
        and _interactive_input_supported()
        and rendered.count("\n") >= max((_current()._console.size.height or 24) - 2, 5)
    ):
        import pydoc

        pydoc.pager(_ANSI_ESCAPE_RE.sub("", rendered))
        _current()._last_line_blank = False
        return
    print(rendered, end="")
    _current()._last_line_blank = False


def clear_screen():
    if _current()._backend is not None:
        _current()._backend.clear()
        return
    if _current()._console.is_terminal:
        _current()._console.clear()


def write_narrative(text, color=""):
    """Reveal long narrative beats paragraph by paragraph when pacing is on."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", str(text)) if p.strip()]
    interactive = _current()._backend is not None or _current()._console.is_terminal
    if not (_current().narrative_pace_enabled and interactive) or len(paragraphs) <= 1:
        write_line(text, color)
        return
    for index, paragraph in enumerate(paragraphs):
        if index:
            ensure_blank_line()
            time.sleep(NARRATIVE_PACE_DELAY_SECONDS)
        write_line(paragraph, color)


DIALOGUE_HANGING_INDENT = 2


def write_dialogue(text, color=""):
    """Print a dialogue line with a hanging indent on wrapped continuation lines."""
    rich_text = _render("" if text is None else str(text), color)
    if _current()._backend is not None:
        # The log pane wraps at its own width; skip the manual indent.
        _current()._backend.emit(rich_text)
        _current()._last_line_blank = not rich_text.plain.strip()
        return
    indent = " " * DIALOGUE_HANGING_INDENT
    with _current()._console.capture() as capture:
        _current()._console.print(rich_text, end="\n", width=render_width() - DIALOGUE_HANGING_INDENT)
    lines = capture.get().splitlines()
    out = "\n".join(lines[:1] + [indent + line for line in lines[1:]])
    print(out)
    _current()._last_line_blank = not rich_text.plain.strip()


# --- Interactive input (prompt_toolkit) -------------------------------------
# In a real terminal, read_line uses a PromptSession for persistent up-arrow
# history, Tab completion, and a bottom toolbar. Everywhere else (tests, pipes,
# dumb terminals) it falls back to plain input() — the same rule the AI layer
# follows with its static fallbacks.

HISTORY_FILE = os.path.expanduser("~/.crimeandpunishment_history")

_session = None
_completer_provider = None
_toolbar_provider = None


def set_completer_provider(provider):
    """provider: zero-arg callable returning a prompt_toolkit Completer or None."""
    _current()._completer_provider = provider


def set_toolbar_provider(provider):
    """provider: zero-arg callable returning plain toolbar text or None."""
    _current()._toolbar_provider = provider


def completion_candidates(text_before_cursor):
    """(candidate, start_position) pairs from the registered completer.

    The TUI's Tab cycling goes through here so both UIs complete from the
    same scene context. Returns [] when no provider is registered.
    """
    if _current()._completer_provider is None:
        return []
    try:
        completer = _current()._completer_provider()
        if completer is None:
            return []
        return completer.candidates(text_before_cursor)
    except Exception:
        return []


def toolbar_active():
    """True when a live status line is being shown to the player."""
    if _current()._backend is not None:
        return True
    return _current()._toolbar_provider is not None and _interactive_input_supported()


def toolbar_text():
    """Current toolbar/status-bar text, or None when no provider is set."""
    if _current()._toolbar_provider is None:
        return None
    try:
        return _current()._toolbar_provider()
    except Exception:
        return None


def _interactive_input_supported():
    try:
        return _current()._console.is_terminal and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _get_session():
    if _current()._session is None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory

        _current()._session = PromptSession(history=FileHistory(_current().HISTORY_FILE))
    return _current()._session


def load_history_lines(limit=200):
    """Entries from the shared history file, oldest first.

    Parses prompt_toolkit FileHistory's on-disk format ('# timestamp'
    comment lines, '+'-prefixed entry lines, multi-line entries as
    consecutive '+' lines) so the TUI's up-arrow history and the console's
    PromptSession share one file.
    """
    if limit <= 0:
        return []
    entries = deque(maxlen=limit)
    current = None
    try:
        with open(_current().HISTORY_FILE, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.rstrip("\r\n")
                if raw.startswith("+"):
                    current = raw[1:] if current is None else f"{current}\n{raw[1:]}"
                elif current is not None:
                    entries.append(current)
                    current = None
    except (OSError, UnicodeError):
        return []
    if current is not None:
        entries.append(current)
    return list(entries)


def append_history_line(line):
    """Append one entry to the shared history file in FileHistory's format."""
    if not str(line).strip():
        return
    import datetime

    try:
        # newline="\n" matches FileHistory's binary writes; Windows text
        # mode would otherwise write CRLF, which FileHistory reads back
        # as "command\r".
        with open(_current().HISTORY_FILE, "a", encoding="utf-8", newline="\n") as f:
            f.write(f"\n# {datetime.datetime.now()}\n")
            for part in str(line).split("\n"):
                f.write(f"+{part}\n")
    except OSError:
        pass


def read_line(prompt_text, color="", completion=True, secret=False):
    rich_text = _render(str(prompt_text), color)
    if _current()._backend is not None:
        _current()._last_line_blank = False
        return _current()._backend.read(rich_text.plain, completion=completion, secret=secret)
    with _current()._console.capture() as capture:
        _current()._console.print(rich_text, end="", width=render_width())
    rendered = capture.get()
    _current()._last_line_blank = False
    if not _interactive_input_supported():
        if secret:
            try:
                if sys.stdin.isatty():
                    import getpass

                    return getpass.getpass(rendered)
            except (AttributeError, ValueError):
                pass
        # Piped input: nothing to mask.
        return input(rendered)
    from prompt_toolkit.formatted_text import ANSI

    completer = _current()._completer_provider() if (completion and _current()._completer_provider) else None
    toolbar = _current()._toolbar_provider() if _current()._toolbar_provider else None
    return _get_session().prompt(
        ANSI(rendered),
        completer=completer,
        bottom_toolbar=toolbar,
        complete_while_typing=False,
        is_password=secret,
    )


def ensure_blank_line():
    if not _current()._last_line_blank:
        write_line("")


def separator(char="-"):
    return char * render_width()


def renderable_to_text(renderable, width=80):
    """Plain-text rendering of a Rich renderable; used by tests."""
    console = Console(width=width, force_terminal=False, highlight=False)
    with console.capture() as capture:
        console.print(renderable)
    return capture.get()


def status(message):
    """Transient spinner while the AI generates; silent when not a terminal."""
    if _current()._backend is not None:
        return _current()._backend.status(message)
    if not _current()._console.is_terminal:
        return contextlib.nullcontext()
    return _current()._console.status(f"[dim magenta]{message}[/]", spinner="dots")


_active_session = ContextVar("terminal_session", default=None)


def _current():
    """Legacy module state remains available outside an explicit UI session."""
    active = _active_session.get()
    return active if active is not None else sys.modules[__name__]


def get_narrative_pace():
    return _current().narrative_pace_enabled


class TerminalSession:
    """Own one UI's backend, providers, console and input history settings.

    Activation routes legacy module calls in the game worker to this session.
    Explicit methods also activate it, so UI callbacks can use the same state
    without changing the caller's context or another worker's backend.
    """

    def __init__(self, history_file=None):
        self._state = SimpleNamespace(
            _console=Console(highlight=False, soft_wrap=False),
            _backend=None, _last_line_blank=True, _session=None,
            _completer_provider=None, _toolbar_provider=None,
            narrative_pace_enabled=False,
            HISTORY_FILE=HISTORY_FILE if history_file is None else history_file,
        )

    @contextlib.contextmanager
    def activate(self):
        token = _active_session.set(self._state)
        try:
            yield self
        finally:
            _active_session.reset(token)

    def __getattr__(self, name):
        operation = globals().get(name)
        if name.startswith("_") or not callable(operation):
            raise AttributeError(name)

        def invoke(*args, **kwargs):
            with self.activate():
                return operation(*args, **kwargs)

        return invoke
