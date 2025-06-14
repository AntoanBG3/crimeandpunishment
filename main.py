# main.py
from game_engine.game_state import Game
from game_engine.logging_utility import game_logger

if __name__ == "__main__":
    try:
        raise RuntimeError("This is a test unhandled exception for logging.")
        game_instance = Game()
        game_instance.run()
    except Exception as e:
        game_logger.exception("An unhandled exception occurred in main execution loop")
        raise # Re-raise the exception to maintain original termination behavior
