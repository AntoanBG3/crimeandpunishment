# game_state.py
import json
import os
import re
import random
from typing import Set, Optional, List, Dict, Any, Tuple

from .game_config import (
    Colors,
    SAVE_GAME_FILE,  # API_CONFIG_FILE, GEMINI_MODEL_NAME removed
    TIME_UNITS_PER_PLAYER_ACTION,
    apply_color_theme,
    DEFAULT_COLOR_THEME,
    DEFAULT_VERBOSITY_LEVEL,
    VERBOSITY_LEVELS,
    STATIC_PLAYER_REFLECTIONS,
)  # Added
from .character_module import Character, CHARACTERS_DATA
from .location_module import LOCATIONS_DATA
from .gemini_interactions import GeminiAPI, NaturalLanguageParser
from .event_manager import EventManager
from .display_mixin import DisplayMixin
from .command_handler import CommandHandler
from .item_interaction_handler import ItemInteractionHandler
from .npc_interaction_handler import NPCInteractionHandler
from .world_manager import WorldManager

# Re-exported for test patching compatibility.
from .game_config import (
    STATIC_ATMOSPHERIC_DETAILS as STATIC_ATMOSPHERIC_DETAILS,
)  # noqa: F401
from .game_config import (
    STATIC_NEWSPAPER_SNIPPETS as STATIC_NEWSPAPER_SNIPPETS,
)  # noqa: F401


class Game(DisplayMixin, ItemInteractionHandler, NPCInteractionHandler, EventManager):
    def __init__(self) -> None:
        self.world_manager = WorldManager(self)
        self.command_handler = CommandHandler(self)
        self.player_character: Optional[Any] = None
        self.all_character_objects: Dict[str, Any] = {}
        self.npcs_in_current_location: List[Any] = []
        self.current_location_name = None
        self.dynamic_location_items: Dict[str, Any] = {}

        self.gemini_api = GeminiAPI()
        self.nl_parser = NaturalLanguageParser(self.gemini_api)
        self.event_manager = EventManager(self)
        # self.game_config = __import__('game_config') # Removed

        self.game_time = 0
        self.current_day = 1
        self.time_since_last_npc_interaction = 0
        self.time_since_last_npc_schedule_update = 0
        self.last_significant_event_summary = None

        self.current_location_description_shown_this_visit = False
        self.visited_locations: Set[str] = set()

        self.player_notoriety_level = 0
        self.known_facts_about_crime = [
            "An old pawnbroker and her sister were murdered recently."
        ]
        self.key_events_occurred = ["Game started."]
        self.numbered_actions_context: List[Any] = []
        self.current_conversation_log = []
        self.overheard_rumors: List[str] = []
        self.low_ai_data_mode = False
        self.autosave_interval_actions = 10
        self.actions_since_last_autosave = 0
        self.player_action_count = 0
        self.tutorial_turn_limit = 5
        self.command_history: List[Tuple[str, str]] = []
        self.max_command_history = 25
        self.turn_headers_enabled = True
        self.last_turn_result_icon = "..."
        self.verbosity_level = DEFAULT_VERBOSITY_LEVEL
        self.color_theme = DEFAULT_COLOR_THEME
        self.last_ai_generated_text: Optional[str] = None
        self.last_ai_generation_source: Optional[str] = None
        apply_color_theme(self.color_theme)

    def _get_current_game_time_period_str(self) -> str:
        return f"Day {self.current_day}, {self.world_manager.get_current_time_period()}"

    def _get_objectives_summary(self, character: Optional[Character]) -> str:
        if not character or not character.objectives:
            return "No particular objectives."

        active_objective_details = []
        for obj in character.objectives:
            if obj.get("active") and not obj.get("completed"):
                obj_desc = obj.get("description", "An unknown goal.")
                current_stage = character.get_current_stage_for_objective(obj.get("id"))
                if isinstance(current_stage, dict):
                    stage_desc = current_stage.get("description", "unspecified stage")
                    active_objective_details.append(
                        f"{obj_desc} (Currently: {stage_desc})"
                    )
                else:
                    active_objective_details.append(
                        f"{obj_desc} (Currently: unspecified stage)"
                    )

        if not active_objective_details:
            return "Currently pursuing no specific objectives."
        prefix = (
            "Your current objectives: "
            if character.is_player
            else f"{character.name}'s current objectives: "
        )
        return prefix + "; ".join(active_objective_details) + "."

    def _get_recent_events_summary(self, count: int = 3) -> str:
        if not self.key_events_occurred:
            return "Nothing much has happened yet."
        return "Key recent events: " + "; ".join(self.key_events_occurred[-count:])

    def _get_known_facts_summary(self) -> str:
        if not self.known_facts_about_crime:
            return "No specific details are widely known about the recent crime."
        return "Known facts about the crime: " + "; ".join(self.known_facts_about_crime)

    def _remember_ai_output(self, text: Optional[str], source_label: str) -> None:
        if not text or not isinstance(text, str):
            return
        if text.startswith("(OOC:"):
            return
        self.last_ai_generated_text = text.strip()
        self.last_ai_generation_source = source_label

    def get_relationship_text(self, score: int) -> str:
        if score > 5:
            return "very positive"
        if score > 2:
            return "positive"
        if score < -5:
            return "very negative"
        if score < -2:
            return "negative"
        return "neutral"

    def _get_save_file_path(self, slot_name: Optional[str] = None) -> Optional[str]:
        if not slot_name:
            return SAVE_GAME_FILE
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", str(slot_name).strip().lower())
        if not sanitized:
            return None
        return f"savegame_{sanitized}.json"

    def save_game(
        self, slot_name: Optional[str] = None, is_autosave: bool = False
    ) -> None:
        if not self.player_character:
            self._print_color("Cannot save: Game not fully initialized.", Colors.RED)
            return
        save_file = self._get_save_file_path(slot_name)
        if not save_file:
            self._print_color(
                "Invalid save slot name. Use letters, numbers, hyphens, or underscores.",
                Colors.RED,
            )
            return
        game_state_data = {
            "player_character_name": self.player_character.name,
            "current_location_name": self.current_location_name,
            "game_time": self.game_time,
            "current_day": self.current_day,
            "all_character_objects_state": {
                name: char.to_dict()
                for name, char in self.all_character_objects.items()
            },
            "dynamic_location_items": self.dynamic_location_items,
            "triggered_events": list(self.event_manager.triggered_events),
            "last_significant_event_summary": self.last_significant_event_summary,
            "player_notoriety_level": self.player_notoriety_level,
            "known_facts_about_crime": self.known_facts_about_crime,
            "key_events_occurred": self.key_events_occurred,
            "visited_locations": list(self.visited_locations),
            "current_location_description_shown_this_visit": self.current_location_description_shown_this_visit,
            "chosen_gemini_model": self.gemini_api.chosen_model_name,
            "low_ai_data_mode": self.low_ai_data_mode,
            "player_action_count": self.player_action_count,
            "color_theme": self.color_theme,
            "verbosity_level": self.verbosity_level,
            "turn_headers_enabled": self.turn_headers_enabled,
            "command_history": self.command_history[-self.max_command_history :],
        }
        try:
            with open(save_file, "w") as f:
                json.dump(game_state_data, f, indent=4)
            if is_autosave:
                self._print_color(f"Autosaved to {save_file}", Colors.DIM)
            else:
                self._print_color(f"Game saved to {save_file}", Colors.GREEN)
        except Exception as e:
            self._print_color(f"Error saving game: {e}", Colors.RED)

    def load_game(self, slot_name: Optional[str] = None) -> bool:
        save_file = self._get_save_file_path(slot_name)
        if not save_file:
            self._print_color(
                "Invalid save slot name. Use letters, numbers, hyphens, or underscores.",
                Colors.RED,
            )
            return False
        if not os.path.exists(save_file):
            self._print_color(f"No save file found at {save_file}.", Colors.YELLOW)
            return False
        try:
            with open(save_file, "r") as f:
                game_state_data = json.load(f)
            self.game_time = game_state_data.get("game_time", 0)
            self.current_day = game_state_data.get("current_day", 1)
            self.current_location_name = game_state_data.get("current_location_name")
            self.dynamic_location_items = game_state_data.get(
                "dynamic_location_items", {}
            )
            self.event_manager.triggered_events = set(
                game_state_data.get("triggered_events", [])
            )
            self.last_significant_event_summary = game_state_data.get(
                "last_significant_event_summary"
            )
            self.player_notoriety_level = game_state_data.get(
                "player_notoriety_level", 0
            )
            self.known_facts_about_crime = game_state_data.get(
                "known_facts_about_crime",
                ["An old pawnbroker and her sister were murdered recently."],
            )
            self.key_events_occurred = game_state_data.get(
                "key_events_occurred", ["Game loaded."]
            )
            self.visited_locations = set(game_state_data.get("visited_locations", []))
            self.current_location_description_shown_this_visit = game_state_data.get(
                "current_location_description_shown_this_visit", False
            )
            self.low_ai_data_mode = game_state_data.get("low_ai_data_mode", False)
            self.player_action_count = game_state_data.get("player_action_count", 0)
            loaded_theme = game_state_data.get("color_theme", DEFAULT_COLOR_THEME)
            applied_theme = apply_color_theme(loaded_theme)
            if not applied_theme:
                apply_color_theme(DEFAULT_COLOR_THEME)
                applied_theme = DEFAULT_COLOR_THEME
            self.color_theme = applied_theme
            self.verbosity_level = game_state_data.get(
                "verbosity_level", DEFAULT_VERBOSITY_LEVEL
            )
            if self.verbosity_level not in VERBOSITY_LEVELS:
                self.verbosity_level = DEFAULT_VERBOSITY_LEVEL
            self.turn_headers_enabled = game_state_data.get(
                "turn_headers_enabled", True
            )
            loaded_history = game_state_data.get("command_history", [])
            self.command_history = (
                loaded_history[-self.max_command_history :]
                if isinstance(loaded_history, list)
                else []
            )
            saved_model_name = game_state_data.get("chosen_gemini_model")
            if saved_model_name:
                self.gemini_api.chosen_model_name = saved_model_name
                self._print_color(
                    f"Loaded preferred Gemini model: {saved_model_name}", Colors.DIM
                )
            self.all_character_objects = {}
            saved_char_states = game_state_data.get("all_character_objects_state", {})
            for char_name, char_state_data in saved_char_states.items():
                static_data = CHARACTERS_DATA.get(char_name)
                if not static_data:
                    self._print_color(
                        f"Warning: Character '{char_name}' from save file not found in current CHARACTERS_DATA. Skipping.",
                        Colors.YELLOW,
                    )
                    continue
                self.all_character_objects[char_name] = Character.from_dict(
                    char_state_data, static_data
                )
            player_name = game_state_data.get("player_character_name")
            if player_name and player_name in self.all_character_objects:
                self.player_character = self.all_character_objects[player_name]
                if self.player_character:
                    self.player_character.is_player = True
            else:
                self._print_color(
                    f"Error: Saved player character '{player_name}' not found or invalid. Load failed.",
                    Colors.RED,
                )
                self.player_character = None
                return False
            if not self.current_location_name and self.player_character:
                self.current_location_name = self.player_character.current_location
            if not self.dynamic_location_items:
                self.world_manager.initialize_dynamic_location_items()
            self.world_manager.update_npcs_in_current_location()
            self._print_color("Game loaded successfully.", Colors.GREEN)
            self._display_load_recap()
            self.world_manager.update_current_location_details(
                from_explicit_look_cmd=False
            )
            return True
        except Exception as e:
            self._print_color(f"Error loading game: {e}", Colors.RED)
            self.player_character = None
            return False

    def _initialize_game(self) -> bool:
        # Call configure and get results
        config_results = self.gemini_api.configure(self._print_color, self._input_color)

        # The GeminiAPI.configure method already prints the Low AI Mode status upon selection.
        # No need for an additional print here unless desired for game-level confirmation.

        self._print_color(
            "\n--- Crime and Punishment: A Text Adventure ---",
            Colors.CYAN + Colors.BOLD,
        )
        self.world_manager._validate_item_data()

        game_loaded_successfully = False
        # Non-interactive mode: Automatically start a new game if GEMINI_API_KEY is set
        if os.getenv("GEMINI_API_KEY"):
            self._print_color("Starting a new game...", Colors.MAGENTA)
            self.low_ai_data_mode = config_results.get("low_ai_preference", False)
            self.world_manager.load_all_characters()
            if not self.world_manager.select_player_character(non_interactive=True):
                self._print_color(
                    "Critical Error: Could not initialize player character. Exiting.",
                    Colors.RED,
                )
                return False
        else:
            self._print_color(
                "Type 'load' to load a saved game, or press Enter to start a new game.",
                Colors.MAGENTA,
            )
            initial_action = (
                self._input_color(f"{self._prompt_arrow()}", Colors.WHITE)
                .strip()
                .lower()
            )
            if initial_action == "load":
                if self.load_game():
                    game_loaded_successfully = True
                else:
                    self._print_color(
                        "Failed to load game. Starting a new game instead.",
                        Colors.YELLOW,
                    )

            if not game_loaded_successfully:
                self.low_ai_data_mode = config_results.get("low_ai_preference", False)
                self.world_manager.load_all_characters()
                if not self.world_manager.select_player_character():
                    self._print_color(
                        "Critical Error: Could not initialize player character. Exiting.",
                        Colors.RED,
                    )
                    return False
        if not self.player_character or not self.current_location_name:
            self._print_color(
                "Game initialization failed critically. Exiting.", Colors.RED
            )
            return False
        if not game_loaded_successfully:
            self.world_manager.update_current_location_details(
                from_explicit_look_cmd=False
            )
            self.display_atmospheric_details()
        self._print_color("\n--- Game Start ---", Colors.CYAN + Colors.BOLD)
        if not game_loaded_successfully:
            self.display_help()
        return True

    def run(self) -> None:
        if not self._initialize_game():
            return
        while True:
            if not LOCATIONS_DATA.get(self.current_location_name):
                self._print_color(
                    f"Critical Error: Current location '{self.current_location_name}' data not found. Exiting.",
                    Colors.RED,
                )
                break
            self._print_turn_header()
            self._display_tutorial_hint()
            self.world_manager._handle_ambient_rumors()
            command, argument = self.command_handler._get_player_input()
            if command is None and argument is None:
                continue
            self.command_handler._record_command_history(command, argument)
            action_taken, show_atmospherics, time_units, special_flag = (
                self.command_handler._process_command(command, argument)
            )
            if special_flag == "load_triggered":
                self.last_turn_result_icon = "LOAD"
                continue
            if special_flag:
                self.last_turn_result_icon = "QUIT"
                break
            self.world_manager._update_world_state_after_action(
                command, action_taken, time_units
            )
            self._display_turn_feedback(show_atmospherics, command)
            if action_taken:
                self.last_turn_result_icon = "OK"
            elif command in [
                "help",
                "status",
                "history",
                "theme",
                "verbosity",
                "turnheaders",
                "retry",
                "rephrase",
                "save",
                "load",
                "toggle_lowai",
            ]:
                self.last_turn_result_icon = "INFO"
            else:
                self.last_turn_result_icon = "NOOP"
            if self.world_manager._check_game_ending_conditions():
                break

    def _handle_think_command(self) -> None:
        if not self.player_character:
            self._print_color(
                "Cannot think: Player character not available.", Colors.RED
            )
            return
        self._print_color("You pause to reflect...", Colors.MAGENTA)
        full_reflection_context = (
            self._get_objectives_summary(self.player_character)
            + f"\nInventory: {self.player_character.get_inventory_description()}"
            + f"\nYour current apparent state is '{self.player_character.apparent_state}'."
            + f"\nRecent notable events: {self._get_recent_events_summary()}"
        )
        if self.player_character.name == "Rodion Raskolnikov":
            theory_objective = self.player_character.get_objective_by_id(
                "understand_theory"
            )
            if theory_objective and theory_objective.get("active"):
                current_stage_obj = (
                    self.player_character.get_current_stage_for_objective(
                        "understand_theory"
                    )
                )
                current_stage_desc = (
                    current_stage_obj.get("description", "an unknown stage")
                    if current_stage_obj
                    else "an unknown stage"
                )
                full_reflection_context += f"\nHe is particularly wrestling with his 'extraordinary man' theory (currently at stage: '{current_stage_desc}'). How do his immediate surroundings, recent events, or current feelings intersect with or challenge this core belief?"

        reflection = None
        ai_generated = False
        if not self.low_ai_data_mode and self.gemini_api.model:
            reflection = self.gemini_api.get_player_reflection(
                self.player_character,
                self.current_location_name,
                self.world_manager.get_current_time_period(),
                full_reflection_context,
            )

        if (
            reflection is None
            or (isinstance(reflection, str) and reflection.startswith("(OOC:"))
            or self.low_ai_data_mode
        ):
            if STATIC_PLAYER_REFLECTIONS:
                reflection = random.choice(STATIC_PLAYER_REFLECTIONS)
            else:
                reflection = "Your mind is a whirl of thoughts."  # Ultimate fallback
        else:
            ai_generated = True

        final_reflection = self._apply_verbosity(reflection)
        self._print_color(
            f'Inner thought: "{final_reflection}"', Colors.GREEN
        )  # Print whatever reflection is chosen
        if ai_generated:
            self._remember_ai_output(final_reflection, "think")
        self.last_significant_event_summary = "was lost in thought."

    def _handle_wait_command(self) -> int:
        self._print_color("You wait for a while...", Colors.MAGENTA)
        self.last_significant_event_summary = "waited, letting time and thoughts drift."
        return TIME_UNITS_PER_PLAYER_ACTION * random.randint(3, 6)
