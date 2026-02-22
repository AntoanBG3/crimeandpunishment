# game_config.py
import json
import logging
import sys
import os
import random


def get_base_path():
    try:
        base_path = sys._MEIPASS
        logging.info(f"Using MEIPASS: {base_path}")
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        logging.info(f"Using dirname: {base_path}")
    return base_path


def get_data_path(relative_path):
    p = os.path.join(get_base_path(), relative_path)
    if not os.path.exists(p):
        print(f"ERROR: Could not find data path explicitly at: {p}")
        # Try to resolve relative to CWD instead as an absolute last resort
        alt_p = os.path.join(os.getcwd(), relative_path)
        if os.path.exists(alt_p):
            print(f"Found it at alt_p: {alt_p}")
            return alt_p
    return p


# --- ANSI Color Codes ---
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"  # For less prominent text like timestamps
    UNDERLINE = "\033[4m"


COLOR_THEME_MAP = {
    "default": {
        "RESET": "\033[0m",
        "RED": "\033[91m",
        "GREEN": "\033[92m",
        "YELLOW": "\033[93m",
        "BLUE": "\033[94m",
        "MAGENTA": "\033[95m",
        "CYAN": "\033[96m",
        "WHITE": "\033[97m",
        "BOLD": "\033[1m",
        "DIM": "\033[2m",
        "UNDERLINE": "\033[4m",
    },
    "high-contrast": {
        "RESET": "\033[0m",
        "RED": "\033[1;97;41m",
        "GREEN": "\033[1;30;102m",
        "YELLOW": "\033[1;30;103m",
        "BLUE": "\033[1;97;44m",
        "MAGENTA": "\033[1;97;45m",
        "CYAN": "\033[1;30;106m",
        "WHITE": "\033[1;97m",
        "BOLD": "\033[1m",
        "DIM": "\033[2m",
        "UNDERLINE": "\033[4m",
    },
    "mono": {
        "RESET": "\033[0m",
        "RED": "",
        "GREEN": "",
        "YELLOW": "",
        "BLUE": "",
        "MAGENTA": "",
        "CYAN": "",
        "WHITE": "",
        "BOLD": "\033[1m",
        "DIM": "\033[2m",
        "UNDERLINE": "\033[4m",
    },
}


def apply_color_theme(theme_name):
    normalized = str(theme_name or "default").strip().lower()
    if normalized not in COLOR_THEME_MAP:
        return None
    for attr_name, color_code in COLOR_THEME_MAP[normalized].items():
        setattr(Colors, attr_name, color_code)
    return normalized


DEFAULT_COLOR_THEME = "default"
DEFAULT_VERBOSITY_LEVEL = "brief"
VERBOSITY_LEVELS = ("brief", "standard", "rich")

# Ensure theme attributes are consistently initialized through one code path.
apply_color_theme(DEFAULT_COLOR_THEME)

# --- Save Game File ---
SAVE_GAME_FILE = "savegame.json"

# --- Gameplay Constants ---
DREAM_CHANCE_NORMAL_STATE = 0.05  # Chance of dream on new day if normal state
DREAM_CHANCE_TROUBLED_STATE = (
    0.35  # Chance if feverish, agitated etc. on new day/long wait
)
RUMOR_CHANCE_PER_NPC_INTERACTION = 0.15  # Chance an NPC shares a rumor during dialogue
AMBIENT_RUMOR_CHANCE_PUBLIC_PLACE = 0.05  # Chance to overhear ambient rumor in public
NPC_SHARE_RUMOR_MIN_RELATIONSHIP = (
    -2
)  # NPC won't share rumors if relationship is too low
DEBUG_LOGS = False

# --- Phrases that might indicate a natural end to a conversation ---
CONCLUDING_PHRASES = [
    r"\b(goodbye|farewell|i must be going|i have to go|until next time|that is all|nothing more to say|very well then|i see)\b",
    r"^(enough|that will be all|we are done here|indeed)\.?$",
    r"\b(i'm done|nothing else|that's it|exit conversation|end dialogue|stop talking|no more questions)\b",  # Added more ways
]

# --- Simplified keywords for relationship adjustments ---
POSITIVE_KEYWORDS = [
    "friend",
    "help",
    "thank",
    "agree",
    "understand",
    "kind",
    "sorry",
    "apologize",
    "sympathize",
    "comfort",
    "give",
    "offer",
]
NEGATIVE_KEYWORDS = [
    "hate",
    "stupid",
    "fool",
    "annoy",
    "disagree",
    "refuse",
    "threaten",
    "never",
    "accuse",
    "doubt",
    "take",
    "demand",
]

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
    "Night": (181, 240),
}
MAX_TIME_UNITS_PER_DAY = 240


# --- Default Item Definitions ---
def load_default_items(data_path=None):
    if data_path is None:
        data_path = get_data_path("data/items.json")
    """Loads default item data from a JSON file."""
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: The items data file was not found at {data_path}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Error: The items data file at {data_path} is not a valid JSON.")
        return {}


DEFAULT_ITEMS = load_default_items()

# --- Input Parsing ---
COMMAND_SYNONYMS = {
    "look": ["examine", "l", "observe", "look around"],  # Added "look around"
    "talk to": ["speak to", "chat with", "ask", "question"],
    "move to": ["go to", "walk to", "travel to", "head to"],
    "objectives": ["goals", "tasks", "obj", "purpose"],
    "think": ["reflect", "ponder", "contemplate"],
    "wait": ["pass time"],
    "inventory": ["inv", "i", "possessions", "belongings"],
    "take": ["get", "pick up", "acquire"],
    "drop": ["leave", "discard"],
    "use": ["apply"],
    "give": ["offer"],
    "read": ["peruse"],
    "help": ["commands", "actions"],
    "save": ["save game"],
    "load": ["load game"],
    "quit": ["exit", "q"],
    "persuade": ["convince", "argue with"],  # New command
    "status": ["char", "character", "profile", "st"],
    "toggle_lowai": ["toggle lowai", "lowaimode"],
    "history": ["/history", "hist"],
    "theme": ["set theme", "color theme"],
    "verbosity": ["density", "text density"],
    "turnheaders": ["turn headers", "turn header"],
    "retry": [],
    "rephrase": [],
}

# --- Player States (for NPC reactions) ---
PLAYER_APPARENT_STATES = [
    "normal",
    "agitated",
    "feverish",
    "suspiciously calm",
    "despondent",
    "injured",
    "contemplative",
    "thoughtful",
    "burdened",
    "dangerously agitated",
    "less feverish",
    "slightly drunk",
    "remorseful",
    "resolved",
    "hopeful",
    "paranoid",
    "haunted by dreams",
    "intrigued by rumors",
    "intensely persuasive",
]

# --- UI Elements ---
PROMPT_ARROW = f"{Colors.GREEN}> {Colors.RESET}"
SEPARATOR_LINE = Colors.DIM + ("-" * 60) + Colors.RESET
SPINNER_FRAMES = ["|", "/", "-", "\\"]

# --- NPC Memory Configuration ---
HIGHLY_NOTABLE_ITEMS_FOR_MEMORY = [
    "raskolnikov's axe",
    "bloodied rag",
    "lizaveta's bundle",
    "sonya's cypress cross",
    "sonya's new testament",
    "mother's letter",
]

# --- Generic Scenery Keywords (for "look at scenery") ---
# These are nouns that might appear in location descriptions.
# If the player "looks at" one of these, and it's not a defined item,
# the AI can generate a description.
GENERIC_SCENERY_KEYWORDS = [
    "wallpaper",
    "window",
    "stain",
    "floor",
    "ceiling",
    "door",
    "street",
    "corner",
    "shadow",
    "light",
    "cobblestones",
    "wall",
    "furniture",
    "table",
    "chair",
    "bed",
    "painting",
    "mirror",
    "dust",
    "grime",
    "candle",
    "gaslight",
    "sky",
    "canal",
    "building",
    "crowd",
]

# --- Static Fallbacks for AI Generation (if API fails or is not configured) ---

STATIC_ATMOSPHERIC_DETAILS = [
    "The air is heavy and still.",
    "A distant sound briefly catches your attention, then fades.",
    "Shadows lengthen around you.",
    "The usual city noise drones on.",
    "A sense of unease hangs in the air.",
]

STATIC_NPC_NPC_INTERACTIONS = [
    "NPC1: The times are hard, wouldn't you agree?\nNPC2: Indeed. One must be careful.",
    "NPC1: Did you see the price of bread today?\nNPC2: Scandalous!",
    "You overhear two figures nearby discussing trivial matters.",
    "Two NPCs are talking nearby, but their words are indistinct.",
]

STATIC_DREAM_SEQUENCES = [
    "You had a restless night filled with strange, fleeting images.",
    "Vague, unsettling dreams disturbed your sleep.",
    "Fragments of a troubling dream cling to your mind, but the details are lost.",
]

STATIC_RUMORS = [
    "Someone mentions a recent string of petty thefts in the Haymarket.",
    "There's talk of a new decree from the governor.",
    "People are saying the summer will be unusually hot.",
]

STATIC_NEWSPAPER_SNIPPETS = [
    "The newspaper reports on minor bureaucratic changes.",
    "An article discusses crop yields in a distant province. It holds little interest.",
    "The pages are filled with dull advertisements and local notices.",
    "You scan the headlines, but nothing seems particularly noteworthy today.",
]


def generate_static_scenery_observation(scenery_noun_phrase):
    options = [
        f"You observe the {scenery_noun_phrase}. It is as it seems.",
        f"The {scenery_noun_phrase} is unremarkable.",
        f"You find nothing special about the {scenery_noun_phrase}.",
    ]
    return random.choice(options)


STATIC_STREET_LIFE_EVENTS = [
    "A carriage rattles noisily down the cobblestones.",
    "Two merchants haggle loudly over a price.",
    "A stray dog darts through the crowd.",
    "Children's laughter is heard from a nearby alley.",
]

STATIC_ENHANCED_OBSERVATIONS = [
    "You notice a few minor details, but nothing immediately actionable.",
    "Your keen senses pick up on the usual subtleties of the place.",
    "Despite your efforts, nothing further of note catches your eye.",
]

STATIC_PLAYER_REFLECTIONS = [
    "Your thoughts are a jumble.",
    "You ponder your situation.",
    "The weight of your circumstances presses upon you.",
    "A wave of weariness washes over you.",
]


def generate_static_item_interaction_description(item_name, action_type):
    options = [
        f"You {action_type} the {item_name} for a moment, but no special insight comes to mind.",
        f"You handle the {item_name}, but it seems ordinary under your {action_type}.",
    ]
    return random.choice(options)


STATIC_ANONYMOUS_NOTE_CONTENT = "They know. Watched at every turn. The old woman is not the only ghost that haunts these streets. Burn this."
