# static_fallbacks.py
# Static fallback text used when the AI API is unavailable or in low-AI mode.
import random


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
