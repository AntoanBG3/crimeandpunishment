# main.py
import logging
import traceback
from game_engine.game_state import Game

try:
    import google.genai
except ImportError:
    print("\n[WARNING] 'google-genai' package is not installed.")
    print("[WARNING] The game will run in fallback deterministic mode without AI features.\n")

if __name__ == "__main__":
    game_instance = Game()
    game_instance.run()
