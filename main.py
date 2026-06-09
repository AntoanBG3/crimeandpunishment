# main.py
import importlib.util

from game_engine.game_state import Game

if importlib.util.find_spec("google.genai") is None:
    print("\n[WARNING] 'google-genai' package is not installed.")
    print("[WARNING] The game will run in fallback deterministic mode without AI features.\n")

if __name__ == "__main__":
    game_instance = Game()
    try:
        game_instance.run()
    except (KeyboardInterrupt, EOFError):
        print("\nFarewell. St. Petersburg will wait.")
