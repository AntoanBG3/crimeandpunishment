# terminal.py
"""Single output funnel for the game.

Rich does the rendering work: word-wrapping at the terminal width (capped to
MAX_TEXT_WIDTH), parsing the ANSI color codes that call sites embed via the
Colors class, and honoring NO_COLOR / dumb terminals / piped output. The final
emit still goes through builtins.print so tests can keep patching it.
"""

import contextlib
import os
import re
import sys
import time

from rich.console import Console
from rich.text import Text

MAX_TEXT_WIDTH = 88
MIN_TEXT_WIDTH = 40

_console = Console(highlight=False, soft_wrap=False)

# Tracks whether the last emitted line was blank, so blocks can guarantee a
# single separating blank line without ever stacking two.
_last_line_blank = True

# Optional paragraph-by-paragraph reveal for major narrative beats (dreams,
# endings). Off by default; toggled by the 'pace' command.
narrative_pace_enabled = False
NARRATIVE_PACE_DELAY_SECONDS = 0.8

# AI text sometimes carries markdown-style *emphasis*; render it as italics
# instead of leaving literal asterisks.
_EMPHASIS_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def set_narrative_pace(enabled):
    global narrative_pace_enabled
    narrative_pace_enabled = bool(enabled)


def render_width():
    width = _console.size.width or 80
    return max(MIN_TEXT_WIDTH, min(width, MAX_TEXT_WIDTH))


def _render(text, color=""):
    body = f"{color}{text}" if color else str(text)
    body = _EMPHASIS_RE.sub("\x1b[3m\\1\x1b[23m", body)
    return Text.from_ansi(body)


def write_line(text, color="", end="\n"):
    global _last_line_blank
    rich_text = _render("" if text is None else str(text), color)
    with _console.capture() as capture:
        _console.print(rich_text, end=end, width=render_width())
    print(capture.get(), end="")
    if end == "\n":
        _last_line_blank = not rich_text.plain.strip()


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def write_renderable(renderable, allow_paging=False):
    """Print a Rich renderable (Panel, Table, ...) through the same funnel.

    With allow_paging, output taller than the terminal goes through the
    system pager (plain text) instead of scrolling past."""
    global _last_line_blank
    with _console.capture() as capture:
        _console.print(renderable, width=render_width())
    rendered = capture.get()
    if (
        allow_paging
        and _interactive_input_supported()
        and rendered.count("\n") >= max((_console.size.height or 24) - 2, 5)
    ):
        import pydoc

        pydoc.pager(_ANSI_ESCAPE_RE.sub("", rendered))
        _last_line_blank = False
        return
    print(rendered, end="")
    _last_line_blank = False


def clear_screen():
    if _console.is_terminal:
        _console.clear()


def write_narrative(text, color=""):
    """Reveal long narrative beats paragraph by paragraph when pacing is on."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", str(text)) if p.strip()]
    if not (narrative_pace_enabled and _console.is_terminal) or len(paragraphs) <= 1:
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
    global _last_line_blank
    rich_text = _render("" if text is None else str(text), color)
    indent = " " * DIALOGUE_HANGING_INDENT
    with _console.capture() as capture:
        _console.print(rich_text, end="\n", width=render_width() - DIALOGUE_HANGING_INDENT)
    lines = capture.get().splitlines()
    out = "\n".join(lines[:1] + [indent + line for line in lines[1:]])
    print(out)
    _last_line_blank = not rich_text.plain.strip()


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
    global _completer_provider
    _completer_provider = provider


def set_toolbar_provider(provider):
    """provider: zero-arg callable returning plain toolbar text or None."""
    global _toolbar_provider
    _toolbar_provider = provider


def toolbar_active():
    """True when the live bottom toolbar is being shown to the player."""
    return _toolbar_provider is not None and _interactive_input_supported()


def _interactive_input_supported():
    try:
        return _console.is_terminal and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _get_session():
    global _session
    if _session is None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory

        _session = PromptSession(history=FileHistory(HISTORY_FILE))
    return _session


def read_line(prompt_text, color="", completion=True):
    global _last_line_blank
    rich_text = _render(str(prompt_text), color)
    with _console.capture() as capture:
        _console.print(rich_text, end="", width=render_width())
    rendered = capture.get()
    _last_line_blank = False
    if not _interactive_input_supported():
        return input(rendered)
    from prompt_toolkit.formatted_text import ANSI

    completer = _completer_provider() if (completion and _completer_provider) else None
    toolbar = _toolbar_provider() if _toolbar_provider else None
    return _get_session().prompt(
        ANSI(rendered),
        completer=completer,
        bottom_toolbar=toolbar,
        complete_while_typing=False,
    )


def ensure_blank_line():
    if not _last_line_blank:
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
    if not _console.is_terminal:
        return contextlib.nullcontext()
    return _console.status(f"[dim magenta]{message}[/]", spinner="dots")
