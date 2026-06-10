# main.py
import importlib.util
import os
import sys

if importlib.util.find_spec("google.genai") is None:
    print("\n[WARNING] 'google-genai' package is not installed.")
    print("[WARNING] The game will run in fallback deterministic mode without AI features.\n")


def _tui_requested():
    if "--tui" in sys.argv:
        return True
    return os.environ.get("CRIME_TUI") == "1"


if __name__ == "__main__":
    if _tui_requested():
        if importlib.util.find_spec("textual") is None:
            print("[WARNING] 'textual' is not installed; starting in classic console mode.")
        else:
            from game_engine.tui_app import run_tui

            run_tui()
            raise SystemExit(0)
    from game_engine.game_state import Game

    game_instance = Game()
    try:
        game_instance.run()
    except (KeyboardInterrupt, EOFError):
        print("\nFarewell. St. Petersburg will wait.")
