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
# Use the latest available model for higher quality generation
GEMINI_MODEL_NAME = 'gemini-1.5-pro-latest' 

# --- Save Game File ---
SAVE_GAME_FILE = "savegame.json"

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
TIME_UNITS_FOR_NPC_INTERACTION_CHANCE = 15 
TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE = 5 
NPC_INTERACTION_CHANCE = 0.3 
NPC_MOVE_CHANCE = 0.7 

TIME_PERIODS = {
    "Morning": (0, 50),    
    "Afternoon": (51, 120), 
    "Evening": (121, 180),  
    "Night": (181, 240)    
}
MAX_TIME_UNITS_PER_DAY = 240

# --- Default Item Definitions ---
DEFAULT_ITEMS = {
    "worn coin": {"description": "A grimy, well-worn kopek. It's seen better days.", "takeable": True, "value": 1, "notable_threshold": 10}, # Notable if player has many
    "tattered handkerchief": {"description": "A stained and frayed piece of cloth.", "takeable": True},
    "dusty bottle": {"description": "An empty bottle covered in a thick layer of dust. Perhaps it once held vodka.", "takeable": True},
    "old newspaper": {"description": "A yellowed page from a St. Petersburg newspaper, dated some weeks ago. The print is faded.", "takeable": True},
    "Raskolnikov's axe": {
        "description": "A heavy, sharp axe, the blade still bearing almost imperceptible dark stains. It feels cold and menacing to the touch, a weight not just in hand but on the soul.", 
        "takeable": True, 
        "hidden_in_location": "Raskolnikov's Garret", # Initially hidden
        "is_notable": True # This item is always notable if carried by Raskolnikov
    }, 
    "Sonya's New Testament": {
        "description": "A small, well-thumbed copy of the New Testament. Its pages are marked and worn, a testament to Sonya's unwavering faith.", 
        "takeable": True, 
        "owner": "Sonya Marmeladova",
        "is_notable": True # Notable if, for instance, Raskolnikov is carrying it
    },
    "bloodied rag": { # Example of an item that could appear after an event
        "description": "A rag stained with dark, dried blood. A chilling piece of evidence.",
        "takeable": True,
        "is_notable": True
    },
    "mother's letter": {
        "description": "A letter from Pulcheria Alexandrovna, filled with anxious love and troubling news of Dunya.",
        "takeable": True,
        "is_notable": True,
        "owner": "Rodion Raskolnikov" # Initially in his possession or arrives via event
    }
}

# --- Input Parsing ---
COMMAND_SYNONYMS = {
    "look": ["examine", "l", "observe"],
    "talk to": ["speak to", "chat with", "ask", "question"],
    "move to": ["go to", "walk to", "travel to", "head to"],
    "objectives": ["goals", "tasks", "obj", "purpose"],
    "think": ["reflect", "ponder", "contemplate"],
    "wait": ["pass time"],
    "inventory": ["inv", "i", "possessions", "belongings"],
    "take": ["get", "pick up", "acquire"],
    "drop": ["leave", "discard"],
    "use": ["apply"], # Added "use" command
    "help": ["commands", "actions"],
    "save": ["save game"],
    "load": ["load game"],
    "quit": ["exit", "q"]
}

# --- Player States (for NPC reactions) ---
# These are examples; can be set dynamically in the game
PLAYER_APPARENT_STATES = ["normal", "agitated", "feverish", "suspiciously calm", "despondent", "injured"]

