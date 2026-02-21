# main.py
from game_engine.game_state import Game
import traceback

try:
    import google.genai
except ImportError:
    pass

if __name__ == "__main__":
    game_instance = Game()
    game_instance.run()
