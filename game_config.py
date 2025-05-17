# game_config.py

# --- ANSI Color Codes ---
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'

# --- Configuration File for API Key ---
API_CONFIG_FILE = "gemini_config.json"
GEMINI_MODEL_NAME = 'gemini-1.5-flash-latest' # Updated to a generally available Flash model

# --- Phrases that might indicate a natural end to a conversation ---
CONCLUDING_PHRASES = [
    r"\b(goodbye|farewell|i must be going|i have to go|until next time|that is all|nothing more to say|very well then|i see)\b",
    r"^(enough|that will be all|we are done here|indeed)\.?$"
]

# --- Simplified keywords for relationship adjustments ---
POSITIVE_KEYWORDS = ["friend", "help", "thank", "agree", "understand", "kind", "sorry", "apologize", "sympathize", "comfort"]
NEGATIVE_KEYWORDS = ["hate", "stupid", "fool", "annoy", "disagree", "refuse", "threaten", "never", "accuse", "doubt"]

# --- Time System ---
TIME_UNITS_PER_PLAYER_ACTION = 1
TIME_UNITS_FOR_NPC_INTERACTION_CHANCE = 15 # How often to check for NPC-NPC interaction
NPC_INTERACTION_CHANCE = 0.3 # 30% chance if conditions met

TIME_PERIODS = {
    "Morning": (0, 50),    # Time units 0-50
    "Afternoon": (51, 120), # Time units 51-120
    "Evening": (121, 180),  # Time units 121-180
    "Night": (181, 240)    # Time units 181-240 (day resets after 240)
}
MAX_TIME_UNITS_PER_DAY = 240
