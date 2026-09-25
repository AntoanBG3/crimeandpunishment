"""Gameplay state separated from runtime services, with legacy Game attribute adapters."""

from dataclasses import dataclass, field
from typing import Any

from .game_config import DEFAULT_COLOR_THEME, DEFAULT_VERBOSITY_LEVEL


@dataclass
class GameState:
    """Mutable gameplay data; API clients, UI and services belong to Game instead."""

    player_character: Any = None
    all_character_objects: dict = field(default_factory=dict)
    current_location_name: str | None = None
    dynamic_location_items: dict = field(default_factory=dict)
    game_time: int = 0
    current_day: int = 1
    last_significant_event_summary: str | None = None
    current_location_description_shown_this_visit: bool = False
    visited_locations: set[str] = field(default_factory=set)
    player_notoriety_level: float = 0
    known_facts_about_crime: list[str] = field(default_factory=lambda: ["An old pawnbroker and her sister were murdered recently."])
    key_events_occurred: list[str] = field(default_factory=lambda: ["Game started."])
    low_ai_data_mode: bool = False
    player_action_count: int = 0
    tutorial_steps_done: set[str] = field(default_factory=set)
    command_history: list[str] = field(default_factory=list)
    turn_headers_enabled: bool = True
    turn_headers_explicit: bool = False
    clear_on_move: bool = False
    verbosity_level: str = DEFAULT_VERBOSITY_LEVEL
    color_theme: str = DEFAULT_COLOR_THEME


class StateAttribute:
    """Compatibility descriptor while handlers migrate from Game to explicit state."""

    def __init__(self):
        self.name = ""

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return getattr(instance.state, self.name)

    def __set__(self, instance, value):
        setattr(instance.state, self.name, value)
