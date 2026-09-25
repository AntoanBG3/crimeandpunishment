"""Validate and reconstruct save candidates before touching the live session."""

import copy
from dataclasses import dataclass
import math

from .character_module import Character
from .game_config import DEFAULT_COLOR_THEME, DEFAULT_VERBOSITY_LEVEL, VERBOSITY_LEVELS


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _strings(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _inventory(value):
    _require(isinstance(value, list), "Inventory must be a list.")
    for item in value:
        _require(isinstance(item, dict) and isinstance(item.get("name"), str),
                 "Inventory entries need an item name.")
        quantity = item.get("quantity", 1)
        _require(_number(quantity) and quantity > 0, "Item quantity must be positive.")
        for key in ("content", "generated_content"):
            _require(key not in item or isinstance(item[key], str), "Invalid readable item content.")


def _character(data, name, static, locations):
    _require(isinstance(data, dict) and data.get("name") == name, "Invalid character identity.")
    _inventory(data.get("inventory", []))
    for key in ("skills", "psychology", "npc_relationships"):
        values = data.get(key, {})
        _require(isinstance(values, dict) and all(_number(v) for v in values.values()),
                 f"Invalid character {key}.")
    _require(_number(data.get("relationship_with_player", 0)), "Invalid relationship score.")
    _require(isinstance(data.get("apparent_state", "normal"), str), "Invalid apparent state.")
    _require(_strings(data.get("journal_entries", [])), "Invalid journal.")
    memories = data.get("memory_about_player", [])
    _require(isinstance(memories, list) and all(isinstance(m, dict) for m in memories),
             "Invalid character memories.")
    for memory in memories:
        _require(_number(memory.get("turn", 0)) and _number(memory.get("sentiment_impact", 0)),
                 "Invalid memory time or sentiment.")
        _require(isinstance(memory.get("content", {}), dict), "Invalid memory content.")
    histories = data.get("conversation_histories", {})
    _require(isinstance(histories, dict) and all(_strings(h) for h in histories.values()),
             "Invalid conversation history.")
    objectives = data.get("objectives", [])
    _require(isinstance(objectives, list), "Invalid objective list.")
    for objective in objectives:
        _require(isinstance(objective, dict) and isinstance(objective.get("id"), str),
                 "Invalid objective identity.")
        for flag in ("active", "completed"):
            _require(isinstance(objective.get(flag, False), bool), "Invalid objective flag.")
        stages = objective.get("stages", [])
        _require(isinstance(stages, list) and all(isinstance(s, dict) for s in stages),
                 "Invalid objective stages.")
    character = Character.from_dict(copy.deepcopy(data), static)
    _require(character.current_location in locations, f"Unknown location for {name}.")
    return character


@dataclass
class RestoredState:
    """Fully prepared state plus runtime preferences applied only after validation."""

    attributes: dict
    triggered_events: set
    cooldown_reset_time: int
    narrative_pace: bool
    model_name: str | None
    skipped_characters: tuple

    def apply(self, game):
        for name, value in self.attributes.items():
            setattr(game, name, value)
        for character in game.all_character_objects.values():
            character.rng = game.rng
        game.event_manager.triggered_events = self.triggered_events
        game.event_manager._last_cooldown_reset_time = self.cooldown_reset_time
        game.numbered_actions_context = []
        game.current_conversation_log = []
        game.actions_since_last_autosave = 0
        game.time_since_last_npc_interaction = 0
        game.time_since_last_npc_schedule_update = 0
        game._full_desc_shown_at = {}
        game._atmospherics_shown_at = {}
        game.last_ai_generated_text = None
        game.last_ai_generation_source = None
        game._last_full_text = None


def prepare_restore(data, characters_data, locations_data, default_items):
    """Decode legacy save JSON without mutating the game, terminal, or source data."""
    _require(isinstance(data, dict), "Save must contain a JSON object.")
    attributes = {}
    for name, default in (("game_time", 0), ("current_day", 1), ("player_action_count", 0)):
        value = data.get(name, default)
        _require(isinstance(value, int) and not isinstance(value, bool) and value >= (1 if name == "current_day" else 0),
                 f"Invalid {name}.")
        attributes[name] = value
    notoriety = data.get("player_notoriety_level", 0)
    _require(_number(notoriety), "Invalid notoriety.")
    attributes["player_notoriety_level"] = notoriety
    for name, default in (
        ("known_facts_about_crime", ["An old pawnbroker and her sister were murdered recently."]),
        ("key_events_occurred", ["Game loaded."]), ("visited_locations", []),
        ("tutorial_steps_done", []), ("triggered_events", []),
    ):
        _require(_strings(data.get(name, default)), f"Invalid {name}.")
        attributes[name] = copy.deepcopy(data.get(name, default))
    events = set(attributes.pop("triggered_events"))
    attributes["visited_locations"] = set(attributes["visited_locations"])
    attributes["tutorial_steps_done"] = set(attributes["tutorial_steps_done"])
    for name, default in (
        ("current_location_description_shown_this_visit", False), ("low_ai_data_mode", False),
        ("turn_headers_enabled", True), ("turn_headers_explicit", False), ("clear_on_move", False),
    ):
        _require(isinstance(data.get(name, default), bool), f"Invalid {name}.")
        attributes[name] = data.get(name, default)
    summary = data.get("last_significant_event_summary")
    _require(summary is None or isinstance(summary, str), "Invalid event summary.")
    attributes["last_significant_event_summary"] = summary
    theme = data.get("color_theme", DEFAULT_COLOR_THEME)
    attributes["color_theme"] = theme if theme in ("default", "high-contrast", "mono") else DEFAULT_COLOR_THEME
    verbosity = data.get("verbosity_level", DEFAULT_VERBOSITY_LEVEL)
    attributes["verbosity_level"] = verbosity if verbosity in VERBOSITY_LEVELS else DEFAULT_VERBOSITY_LEVEL
    history = data.get("command_history", [])
    attributes["command_history"] = history[-25:] if _strings(history) else []
    saved_characters = data.get("all_character_objects_state")
    _require(isinstance(saved_characters, dict), "Save has no character state.")
    restored = {}
    skipped = []
    for name, character in saved_characters.items():
        if name not in characters_data:
            skipped.append(name)
            continue
        restored[name] = _character(character, name, characters_data[name], locations_data)
    player_name = data.get("player_character_name")
    _require(isinstance(player_name, str) and player_name in restored, "Saved player is missing.")
    player = restored[player_name]
    for character in restored.values():
        character.is_player = character is player
    location = data.get("current_location_name") or player.current_location
    _require(isinstance(location, str) and location in locations_data, "Unknown current location.")
    player.current_location = location
    attributes.update(player_character=player, all_character_objects=restored,
                      current_location_name=location,
                      npcs_in_current_location=[c for c in restored.values()
                                                if c is not player and c.current_location == location])
    items = copy.deepcopy(data.get("dynamic_location_items", {}))
    _require(isinstance(items, dict), "Invalid world inventory.")
    for name, inventory in items.items():
        _require(name in locations_data, f"Unknown inventory location: {name}.")
        _inventory(inventory)
    if not items:
        items = {name: copy.deepcopy(details.get("items_present", []))
                 for name, details in locations_data.items()}
        for name, props in default_items.items():
            inventory = items.get(props.get("hidden_in_location"))
            if inventory is not None and not any(item["name"] == name for item in inventory):
                inventory.append({"name": name, "quantity": props.get("quantity", 1)})
    attributes["dynamic_location_items"] = items
    cooldown = data.get("event_manager_cooldown_reset_time", attributes["game_time"])
    _require(_number(cooldown) and cooldown >= 0, "Invalid event cooldown.")
    pace = data.get("narrative_pace", False)
    _require(isinstance(pace, bool), "Invalid narrative pacing.")
    model = data.get("chosen_gemini_model")
    _require(model is None or isinstance(model, str), "Invalid model preference.")
    return RestoredState(attributes, events, cooldown, pace, model, tuple(skipped))
