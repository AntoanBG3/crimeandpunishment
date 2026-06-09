# terminal.py
"""Single output funnel for the game.

Rich does the rendering work: word-wrapping at the terminal width (capped to
MAX_TEXT_WIDTH), parsing the ANSI color codes that call sites embed via the
Colors class, and honoring NO_COLOR / dumb terminals / piped output. The final
emit still goes through builtins.print so tests can keep patching it.
"""

import contextlib
import re
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


def write_renderable(renderable):
    """Print a Rich renderable (Panel, Table, ...) through the same funnel."""
    global _last_line_blank
    with _console.capture() as capture:
        _console.print(renderable, width=render_width())
    print(capture.get(), end="")
    _last_line_blank = False


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


def read_line(prompt_text, color=""):
    global _last_line_blank
    rich_text = _render(str(prompt_text), color)
    with _console.capture() as capture:
        _console.print(rich_text, end="", width=render_width())
    result = input(capture.get())
    _last_line_blank = False
    return result


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
