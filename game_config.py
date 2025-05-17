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
    DIM = '\033[2m' # For less prominent text like timestamps
    UNDERLINE = '\033[4m'

# --- API Key Configuration ---
API_CONFIG_FILE = "gemini_config.json"
GEMINI_API_KEY_ENV_VAR = "GEMINI_API_KEY"
GEMINI_MODEL_NAME = 'gemini-2.0-flash'

# --- Save Game File ---
SAVE_GAME_FILE = "savegame.json"

# --- Gameplay Constants ---
DREAM_CHANCE_NORMAL_STATE = 0.05 # Chance of dream on new day if normal state
DREAM_CHANCE_TROUBLED_STATE = 0.35 # Chance if feverish, agitated etc. on new day/long wait
RUMOR_CHANCE_PER_NPC_INTERACTION = 0.15 # Chance an NPC shares a rumor during dialogue
AMBIENT_RUMOR_CHANCE_PUBLIC_PLACE = 0.05 # Chance to overhear ambient rumor in public
NPC_SHARE_RUMOR_MIN_RELATIONSHIP = -2 # NPC won't share rumors if relationship is too low

# --- Phrases that might indicate a natural end to a conversation ---
CONCLUDING_PHRASES = [
    r"\b(goodbye|farewell|i must be going|i have to go|until next time|that is all|nothing more to say|very well then|i see)\b",
    r"^(enough|that will be all|we are done here|indeed)\.?$"
]

# --- Simplified keywords for relationship adjustments ---
POSITIVE_KEYWORDS = ["friend", "help", "thank", "agree", "understand", "kind", "sorry", "apologize", "sympathize", "comfort", "give", "offer"]
NEGATIVE_KEYWORDS = ["hate", "stupid", "fool", "annoy", "disagree", "refuse", "threaten", "never", "accuse", "doubt", "take", "demand"]

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
    "worn coin": {
        "description": "A grimy, well-worn kopek. It's seen better days, but still holds some small value. Could be offered as meagre charity or perhaps to buy a moment's peace or a cheap drink.",
        "takeable": True, "value": 1, "stackable": True,
        "notable_threshold": 20,
        "use_effect_player": "offer_charity_or_payment"
    },
    "tattered handkerchief": {
        "description": "A stained and frayed piece of cloth. A grim reminder of illness or poverty. Perhaps it could offer some small comfort if one is unwell.",
        "takeable": True,
        "use_effect_player": "comfort_self_if_ill"
    },
    "dusty bottle": {
        "description": "An empty bottle covered in a thick layer of dust. Perhaps it once held vodka. Now it's just a piece of refuse, or maybe a desperate, makeshift weapon if one were truly cornered.",
        "takeable": True,
        "use_effect_player": "examine_bottle_for_residue"
    },
    "old newspaper": { # This can be a generic one
        "description": "A yellowed page from a St. Petersburg newspaper, dated some weeks ago. The print is faded. Reading it might offer a glimpse into the city's recent events or spark a troubling thought.",
        "takeable": True, "readable": True, # Mark as readable
        "use_effect_player": "read_newspaper_for_news_or_thoughts"
    },
    "Fresh Newspaper": { # A new item for dynamic content
        "description": "A recently printed newspaper, still smelling faintly of ink. The headlines might offer insights into current events or the city's mood.",
        "takeable": True, "readable": True, "value": 2, # Could be bought
        "use_effect_player": "read_evolving_news_article"
    },
    "Anonymous Note": { # For AI-generated notes
        "description": "A hastily scribbled note, contents unknown until read. It feels ominous.",
        "takeable": True, "readable": True, "is_notable": True,
        "use_effect_player": "read_generated_document",
        "generated_content": "" # To store the AI-generated text for this specific instance of the note
    },
    "Raskolnikov's axe": {
        "description": "A heavy, sharp axe, the blade still bearing almost imperceptible dark stains. It feels cold and menacing to the touch, a weight not just in hand but on the soul. Holding it brings back vivid, horrifying memories and a surge of conflicting emotions.",
        "takeable": True,
        "hidden_in_location": "Raskolnikov's Garret",
        "is_notable": True,
        "use_effect_player": "grip_axe_and_reminisce_horror"
    },
    "Sonya's New Testament": {
        "description": "A small, well-thumbed copy of the New Testament. Its pages are marked and worn, a testament to Sonya's unwavering faith. Reading it might offer solace, or a stark confrontation with one's own sins.",
        "takeable": True, "readable": True,
        "owner": "Sonya Marmeladova",
        "is_notable": True,
        "use_effect_player": "read_testament_for_solace_or_guilt"
    },
    "Sonya's Cypress Cross": {
        "description": "A small, plain cypress wood cross, given by Sonya. It feels strangely warm to the touch, imbued with a sense of simple, profound faith and shared suffering. Holding it might bring a moment of clarity, remorse, or a fragile hope for redemption.",
        "takeable": True,
        "owner": "Sonya Marmeladova",
        "is_notable": True,
        "use_effect_player": "reflect_on_faith_and_redemption"
    },
    "bloodied rag": {
        "description": "A rag stained with dark, dried blood. A chilling piece of evidence that screams of violence. Examining it too closely might trigger intense paranoia or flashbacks.",
        "takeable": True,
        "is_notable": True,
        "use_effect_player": "examine_rag_and_spiral_into_paranoia"
    },
    "mother's letter": {
        "description": "A letter from Pulcheria Alexandrovna, filled with anxious love and troubling news of Dunya. Re-reading it might stir deep feelings of guilt, responsibility, or a desperate urge to protect one's family.",
        "takeable": True, "readable": True,
        "is_notable": True,
        "owner": "Rodion Raskolnikov",
        "use_effect_player": "reread_letter_and_feel_familial_pressure"
    },
    "cheap vodka": {
        "description": "A half-empty bottle of harsh, cheap vodka. It promises temporary oblivion from the crushing weight of thoughts and reality. Drinking it will likely lead to a muddled state.",
        "takeable": True, "consumable": True, "value": 5,
        "use_effect_player": "drink_vodka_for_oblivion"
    },
    "Lizaveta's bundle": {
        "description": "A small, poorly wrapped bundle tied with string, containing a few meager possessions. It was dropped by Lizaveta. Examining its contents – perhaps a worn shawl, a child's toy, a copper coin – serves as a brutal reminder of the innocent life taken, deepening the sense of guilt.",
        "takeable": True,
        "is_notable": True,
        "hidden_in_location": "Pawnbroker's Apartment",
        "use_effect_player": "examine_bundle_and_face_guilt_for_Lizaveta"
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
    "use": ["apply"],
    "give": ["offer"],
    "read": ["peruse"],
    "help": ["commands", "actions"],
    "save": ["save game"],
    "load": ["load game"],
    "quit": ["exit", "q"]
}

# --- Player States (for NPC reactions) ---
PLAYER_APPARENT_STATES = [
    "normal", "agitated", "feverish", "suspiciously calm", "despondent",
    "injured", "contemplative", "thoughtful", "burdened", "dangerously agitated",
    "less feverish", "slightly drunk", "remorseful", "resolved", "hopeful", "paranoid",
    "haunted by dreams", "intrigued by rumors" # New states
]

# --- UI Elements ---
PROMPT_ARROW = f"{Colors.GREEN}> {Colors.RESET}"
SEPARATOR_LINE = Colors.DIM + ("-" * 60) + Colors.RESET

# --- Generic Scenery Keywords (for "look at scenery") ---
# These are nouns that might appear in location descriptions.
# If the player "looks at" one of these, and it's not a defined item,
# the AI can generate a description.
GENERIC_SCENERY_KEYWORDS = [
    "wallpaper", "window", "stain", "floor", "ceiling", "door", "street",
    "corner", "shadow", "light", "cobblestones", "wall", "furniture",
    "table", "chair", "bed", "painting", "mirror", "dust", "grime",
    "candle", "gaslight", "sky", "canal", "building", "crowd"
]