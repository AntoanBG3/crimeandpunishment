# main.py
import importlib.util
import os
import sys


def _package_available(name):
    # find_spec raises ModuleNotFoundError (rather than returning None) when a
    # dotted name's parent package is absent — e.g. "google.genai" with no
    # "google" at all, the usual case in a frozen build without the SDK.
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


if not _package_available("google.genai"):
    print("\n[WARNING] 'google-genai' package is not installed.")
    print("[WARNING] The game will run in fallback deterministic mode without AI features.\n")

# The shipped default UI. --no-tui / CRIME_TUI=0 opts out,
# and any non-TTY stream still gets the classic console automatically.
DEFAULT_MODE = "tui"


def choose_mode(argv=None, environ=None):
    """Decide which UI to launch: "tui" or "console".

    Explicit opt-out (--no-tui / CRIME_TUI=0) wins over opt-in; any non-TTY
    stream forces the console path (Textual cannot run without a terminal,
    and piped runs rely on the plain print/input fallback); a missing
    textual package falls back to the console with a warning.
    """
    argv = sys.argv if argv is None else argv
    environ = os.environ if environ is None else environ

    if "--no-tui" in argv or environ.get("CRIME_TUI") == "0":
        return "console"
    requested = "--tui" in argv or environ.get("CRIME_TUI") == "1"
    if not requested and DEFAULT_MODE != "tui":
        return "console"
    try:
        tty = sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        tty = False
    if not tty:
        if requested:
            print("[WARNING] Not an interactive terminal; starting in classic console mode.")
        return "console"
    if not _package_available("textual"):
        print("[WARNING] 'textual' is not installed; starting in classic console mode.")
        return "console"
    return "tui"


def main():
    """Run either interface with a process-level diagnostic boundary."""
    if "--version" in sys.argv:
        from game_engine.game_config import GAME_VERSION

        print(f"Crime and Punishment {GAME_VERSION}")
        return 0
    if choose_mode() == "tui":
        from game_engine.tui_app import run_tui

        return run_tui()
    from game_engine.game_state import Game

    Game().run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nFarewell. St. Petersburg will wait.")
    except BrokenPipeError:
        # Redirect final interpreter flush too: the reader may have closed stdout.
        with open(os.devnull, "w", encoding="utf-8") as sink:
            os.dup2(sink.fileno(), sys.stdout.fileno())
        raise SystemExit(0) from None
    except Exception as error:
        from game_engine.diagnostics import failure_message, record_failure

        print(failure_message(error, record_failure(error)), file=sys.stderr)
        raise SystemExit(1) from None
