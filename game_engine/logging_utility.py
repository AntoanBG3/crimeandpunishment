import logging
import os
from logging.handlers import RotatingFileHandler

# Define the logs directory
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# General game logger
game_logger = logging.getLogger('game_logger')
game_logger.setLevel(logging.DEBUG) # Capture all levels of logs

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')

# File handler for general game logs (e.g., errors, warnings, info, debug)
# Rotates logs: 5 files, 5MB each
general_log_file = os.path.join(LOGS_DIR, 'game_activity.log')
general_handler = RotatingFileHandler(general_log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
general_handler.setLevel(logging.DEBUG) # Log debug and higher to this file
general_handler.setFormatter(formatter)
game_logger.addHandler(general_handler)

# File handler specifically for critical/crash logs
# This can be a separate file if desired, or critical logs will also go to the general_log_file
# For simplicity here, critical errors will also go to 'game_activity.log' but could be filtered
# or sent to a different handler if needed.
# If a separate critical log is desired:
# critical_log_file = os.path.join(LOGS_DIR, 'critical_crash.log')
# critical_handler = RotatingFileHandler(critical_log_file, maxBytes=1*1024*1024, backupCount=2, encoding='utf-8')
# critical_handler.setLevel(logging.CRITICAL)
# critical_handler.setFormatter(formatter)
# game_logger.addHandler(critical_handler)

# Console handler for debugging (optional, can be commented out for production)
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.INFO) # Or DEBUG
# console_handler.setFormatter(formatter)
# game_logger.addHandler(console_handler)

# Example usage (will be removed, just for initial testing if run directly)
if __name__ == '__main__':
    game_logger.debug("This is a debug message.")
    game_logger.info("This is an info message.")
    game_logger.warning("This is a warning message.")
    game_logger.error("This is an error message.")
    game_logger.critical("This is a critical message.")
    try:
        1 / 0
    except ZeroDivisionError:
        game_logger.exception("A ZeroDivisionError occurred!")
