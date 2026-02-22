# display_mixin.py
"""Display and UI output methods for the Game class."""

import re
import random

from .game_config import Colors, DEFAULT_ITEMS, STATIC_ATMOSPHERIC_DETAILS


class DisplayMixin:
    """Mixin providing all display, output, and UI-related methods."""

    def _print_color(self, text, color_code, end="\n"):
        print(f"{color_code}{text}{Colors.RESET}", end=end)

    def _input_color(self, prompt_text, color_code):
        return input(f"{color_code}{prompt_text}{Colors.RESET}")

    def _prompt_arrow(self):
        return f"{Colors.GREEN}> {Colors.RESET}"

    def _separator_line(self):
        return Colors.DIM + ("-" * 60) + Colors.RESET

    def _get_mode_label(self):
        if self.low_ai_data_mode or not self.gemini_api.model:
            return "LOW-AI"
        return "AI"

    def _apply_verbosity(self, text):
        if text is None:
            return None
        normalized = str(text).strip()
        if not normalized:
            return normalized
        if self.verbosity_level == "brief":
            sentence = re.split(r"(?<=[.!?])\s+", normalized, maxsplit=1)[0]
            if len(sentence) > 180:
                sentence = sentence[:177].rstrip() + "..."
            return sentence
        if self.verbosity_level == "standard" and len(normalized) > 550:
            return normalized[:547].rstrip() + "..."
        return normalized

    def _print_turn_header(self):
        if not self.turn_headers_enabled:
            return
        time_info = self._get_current_game_time_period_str()
        location = self.current_location_name or "Unknown"
        self._print_color(self._separator_line(), Colors.DIM)
        self._print_color(
            f"[{time_info} | {location} | {self.last_turn_result_icon} | Mode: {self._get_mode_label()}]",
            Colors.DIM,
        )

    def _describe_item_brief(self, item_name):
        item_defaults = DEFAULT_ITEMS.get(item_name, {})
        tags = []
        if item_defaults.get("readable"):
            tags.append("readable")
        if item_defaults.get("consumable"):
            tags.append("consumable")
        if item_defaults.get("value") is not None:
            tags.append(f"value {item_defaults['value']}")
        if item_defaults.get("is_notable"):
            tags.append("notable")
        return ", ".join(tags) if tags else "common item"

    def _describe_npc_brief(self, npc_name):
        npc = next(
            (n for n in self.npcs_in_current_location if n.name == npc_name), None
        )
        if npc is None:
            return "person here"
        return f"appears {npc.apparent_state}"

    def _display_item_properties(self, item_default):
        properties_to_display = []
        if item_default.get("readable", False):
            properties_to_display.append("Type: Readable")
        if item_default.get("consumable", False):
            properties_to_display.append("Type: Consumable")
        if item_default.get("value") is not None:
            properties_to_display.append(f"Value: {item_default['value']} kopeks")
        if item_default.get("is_notable", False):
            properties_to_display.append("Trait: Notable")
        if item_default.get("stackable", False):
            properties_to_display.append("Trait: Stackable")
        if item_default.get("owner"):
            properties_to_display.append(f"Belongs to: {item_default['owner']}")
        if item_default.get("use_effect_player"):
            properties_to_display.append("Action: Can be 'used'")
        if properties_to_display:
            self._print_color("--- Properties ---", Colors.BLUE + Colors.BOLD)
            for prop_str in properties_to_display:
                self._print_color(f"- {prop_str}", Colors.BLUE)
            self._print_color("", Colors.RESET)

    def _display_command_history(self):
        self._print_color("\n--- Recent Commands ---", Colors.CYAN + Colors.BOLD)
        if not self.command_history:
            self._print_color("No commands recorded yet.", Colors.DIM)
            return
        history_to_show = self.command_history[-10:]
        for idx, command_text in enumerate(history_to_show, start=1):
            self._print_color(f"{idx}. {command_text}", Colors.WHITE)

    def _display_tutorial_hint(self):
        if self.player_action_count >= self.tutorial_turn_limit:
            return
        step = self.player_action_count + 1
        if hasattr(self, "command_handler") and hasattr(
            self.command_handler, "_build_intent_context"
        ):
            context = self.command_handler._build_intent_context()
        else:
            context = "none"
        talk_target = context["npcs"][0] if context.get("npcs") else "someone nearby"
        move_target = (
            context["exits"][0]["name"] if context.get("exits") else "an available exit"
        )
        tutorial_lines = {
            1: "Tutorial 1/5: Start by using 'look' to survey this location.",
            2: f"Tutorial 2/5: Try 'talk to {talk_target}' to open a social path.",
            3: "Tutorial 3/5: Use 'objectives' to check your active direction.",
            4: f"Tutorial 4/5: Travel with 'move to {move_target}' when you're ready.",
            5: "Tutorial 5/5: Need focused help? Try 'help movement' or 'help social'.",
        }
        self._print_color(tutorial_lines.get(step, ""), Colors.DIM)

    def display_atmospheric_details(self):
        if self.player_character and self.current_location_name:
            details = None
            ai_generated = False
            if not self.low_ai_data_mode and self.gemini_api.model:
                recently_visited = (
                    getattr(self.world_manager, "last_visited_location", None)
                    == self.current_location_name
                )
                details = self.gemini_api.get_atmospheric_details(
                    self.player_character,
                    self.current_location_name,
                    self.world_manager.get_current_time_period(),
                    self.last_significant_event_summary,
                    self._get_objectives_summary(self.player_character),
                    recently_visited,
                )
                self.world_manager.last_visited_location = self.current_location_name

            if (
                details is None
                or (isinstance(details, str) and details.startswith("(OOC:"))
                or self.low_ai_data_mode
            ):
                if STATIC_ATMOSPHERIC_DETAILS:
                    details = random.choice(STATIC_ATMOSPHERIC_DETAILS)
                else:
                    details = "The atmosphere is thick with unspoken stories."  # Ultimate fallback
            else:
                ai_generated = True

            if details:  # Ensure details is not None if fallbacks were empty
                final_details = self._apply_verbosity(details)
                self._print_color(f"\n{final_details}", Colors.CYAN)
                if ai_generated:
                    self._remember_ai_output(final_details, "atmosphere")
            self.last_significant_event_summary = None

    def display_objectives(self):
        self._print_color("\n--- Your Objectives ---", Colors.CYAN + Colors.BOLD)
        if not self.player_character or not self.player_character.objectives:
            self._print_color(
                "You have no specific objectives at the moment.", Colors.DIM
            )
            return
        active_objectives = [
            obj
            for obj in self.player_character.objectives
            if obj.get("active", False) and not obj.get("completed", False)
        ]
        completed_objectives = [
            obj
            for obj in self.player_character.objectives
            if obj.get("completed", False)
        ]
        if not active_objectives and not completed_objectives:
            self._print_color(
                "You have no specific objectives at the moment.", Colors.DIM
            )
            return
        if active_objectives:
            self._print_color("\nOngoing:", Colors.YELLOW + Colors.BOLD)
            for obj in active_objectives:
                self._print_color(
                    f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE
                )
                current_stage = self.player_character.get_current_stage_for_objective(
                    obj.get("id")
                )
                if current_stage:
                    self._print_color(
                        f"  Current Stage: {current_stage.get('description', 'No stage description')}",
                        Colors.CYAN,
                    )
        else:
            self._print_color("\nNo active objectives right now.", Colors.DIM)
        if completed_objectives:
            self._print_color("\nCompleted:", Colors.GREEN + Colors.BOLD)
            for obj in completed_objectives:
                self._print_color(
                    f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE
                )

    def display_help(self, category=None):
        self._print_color("\n--- Available Actions ---", Colors.CYAN + Colors.BOLD)
        self._print_color("", Colors.RESET)
        self._print_color(
            f"Mode: {self._get_mode_label()} | Theme: {self.color_theme} | Verbosity: {self.verbosity_level}",
            Colors.DIM,
        )
        action_groups = {
            "movement": [
                (
                    "look / l / examine / observe / look around",
                    "Examine surroundings, see people, items, and exits.",
                ),
                (
                    "look at [thing/person/scenery]",
                    "Examine something specific more closely.",
                ),
                ("move to [exit desc / location name]", "Change locations."),
                ("wait", "Pass some time (may trigger dreams if troubled)."),
            ],
            "social": [
                ("talk to [name]", "Speak with someone here."),
                (
                    "persuade [name] that/to [argument]",
                    "Try to sway a character with a focused argument.",
                ),
                (
                    "give [item name] to [target name]",
                    "Offer an item to another character.",
                ),
                ("think / reflect", "Access your character's inner thoughts."),
            ],
            "items": [
                ("inventory / inv / i", "Check your possessions."),
                ("take [item name]", "Pick up an item from the location."),
                (
                    "drop [item name]",
                    "Leave an item from your inventory in the location.",
                ),
                (
                    "use [item name]",
                    "Attempt to use an item from your inventory (often on yourself).",
                ),
                (
                    "use [item name] on [target name/item]",
                    "Use an item on something or someone specifically.",
                ),
                (
                    "read [item name]",
                    "Read a readable item like a letter or newspaper.",
                ),
            ],
            "meta": [
                ("objectives / obj", "See your current goals."),
                (
                    "journal / notes",
                    "Review your journal entries (rumors, news, etc.).",
                ),
                (
                    "save [slot]",
                    "Save your current game progress (optional slot name).",
                ),
                ("load [slot]", "Load a previously saved game (optional slot name)."),
                ("help / commands", "Show this help message."),
                (
                    "status / char / profile / st",
                    "Display your character's current status.",
                ),
                ("toggle lowai / lowaimode", "Toggle low AI data usage mode."),
                ("history / /history", "Show recent commands."),
                ("!!", "Repeat your previous command."),
                (
                    "retry / rephrase",
                    "Generate an alternate wording of the last AI text.",
                ),
                ("theme [default|high-contrast|mono]", "Switch color profile."),
                ("verbosity [brief|standard|rich]", "Adjust narrative text density."),
                ("turnheaders [on|off]", "Toggle turn boundary headers."),
                ("quit / exit / q", "Exit the game."),
            ],
        }

        normalized_category = (
            category.strip().lower()
            if isinstance(category, str) and category.strip()
            else "all"
        )
        if normalized_category == "all":
            actions = [item for group in action_groups.values() for item in group]
        elif normalized_category in action_groups:
            self._print_color(f"Category: {normalized_category}", Colors.DIM)
            actions = action_groups[normalized_category]
        else:
            available = ", ".join(action_groups.keys())
            self._print_color(
                f"Unknown help category '{category}'. Available: {available}. Showing all commands.",
                Colors.YELLOW,
            )
            actions = [item for group in action_groups.values() for item in group]

        for cmd, desc in actions:
            self._print_color(
                f"{cmd:<65} {Colors.WHITE}- {desc}{Colors.RESET}", Colors.MAGENTA
            )
        self._print_color("", Colors.RESET)
        self._print_color(
            "Tip: use 'help movement', 'help social', 'help items', or 'help meta'.",
            Colors.DIM,
        )
        self._print_color("", Colors.RESET)

    def _display_load_recap(self):
        if not self.player_character:
            return

        self._print_color("\n--- Session Recap ---", Colors.CYAN + Colors.BOLD)
        self._print_color(f"Location: {self.current_location_name}", Colors.WHITE)
        self._print_color(
            f"Time: {self._get_current_game_time_period_str()}", Colors.WHITE
        )

        active_objective = None
        for objective in self.player_character.objectives:
            if objective.get("active") and not objective.get("completed"):
                active_objective = objective
                break
        if active_objective:
            stage = self.player_character.get_current_stage_for_objective(
                active_objective.get("id")
            )
            stage_text = stage.get("description") if stage else "unspecified stage"
            self._print_color(
                f"Objective: {active_objective.get('description', 'Unnamed objective')} ({stage_text})",
                Colors.WHITE,
            )
        else:
            self._print_color("Objective: No active objective.", Colors.WHITE)

        recent_events = (
            self.key_events_occurred[-3:] if self.key_events_occurred else []
        )
        if recent_events:
            self._print_color("Recent events:", Colors.WHITE)
            for event in recent_events:
                self._print_color(f"- {event}", Colors.DIM)

        relationship_entries = []
        for character_name, character_obj in self.all_character_objects.items():
            if character_obj.is_player:
                continue
            score = getattr(character_obj, "relationship_with_player", 0)
            if score != 0:
                relationship_entries.append(
                    (abs(score), character_name, self.get_relationship_text(score))
                )
        relationship_entries.sort(reverse=True)
        if relationship_entries:
            self._print_color("Relationship highlights:", Colors.WHITE)
            for _, character_name, relationship_text in relationship_entries[:3]:
                self._print_color(
                    f"- {character_name}: {relationship_text}", Colors.DIM
                )

    def _display_turn_feedback(self, show_atmospherics_this_turn, command):
        if show_atmospherics_this_turn:
            self.display_atmospheric_details()
        elif command == "load":
            self.last_significant_event_summary = None

    def _handle_status_command(self):
        if not self.player_character:
            self._print_color("No player character loaded.", Colors.RED)
            return
        self._print_color("\n--- Your Status ---", Colors.CYAN + Colors.BOLD)
        self._print_color(
            f"Name: {Colors.GREEN}{self.player_character.name}{Colors.RESET}",
            Colors.WHITE,
        )
        self._print_color(
            f"Apparent State: {Colors.YELLOW}{self.player_character.apparent_state}{Colors.RESET}",
            Colors.WHITE,
        )
        self._print_color(
            f"Current Location: {Colors.CYAN}{self.current_location_name}{Colors.RESET}",
            Colors.WHITE,
        )
        notoriety_desc = "Unknown"
        if self.player_notoriety_level == 0:
            notoriety_desc = "Unknown"
        elif self.player_notoriety_level < 0.5:
            notoriety_desc = "Barely Noticed"
        elif self.player_notoriety_level < 1.5:
            notoriety_desc = "Slightly Known"
        elif self.player_notoriety_level < 2.5:
            notoriety_desc = "Talked About"
        else:
            notoriety_desc = "Infamous"
        self._print_color(
            f"Notoriety: {Colors.MAGENTA}{notoriety_desc} (Level {self.player_notoriety_level:.1f}){Colors.RESET}",
            Colors.WHITE,
        )
        ai_mode = (
            "Low AI / Fallback Friendly" if self.low_ai_data_mode else "AI Dynamic"
        )
        self._print_color(
            f"Narrative Mode: {Colors.CYAN}{ai_mode}{Colors.RESET}", Colors.WHITE
        )
        self._print_color(f"Theme: {self.color_theme}", Colors.WHITE)
        self._print_color(f"Verbosity: {self.verbosity_level}", Colors.WHITE)
        self._print_color(
            f"Turn Headers: {'on' if self.turn_headers_enabled else 'off'}",
            Colors.WHITE,
        )
        if self.player_action_count < self.tutorial_turn_limit:
            self._print_color(
                f"Tutorial Progress: {self.player_action_count}/{self.tutorial_turn_limit} actions",
                Colors.DIM,
            )
        self._print_color("\n--- Skills ---", Colors.CYAN + Colors.BOLD)
        if self.player_character.skills:
            for skill_name, value in self.player_character.skills.items():
                self._print_color(f"- {skill_name.capitalize()}: {value}", Colors.WHITE)
        else:
            self._print_color("No specialized skills.", Colors.DIM)
        self._print_color("\n--- Active Objectives ---", Colors.CYAN + Colors.BOLD)
        active_objectives = [
            obj
            for obj in self.player_character.objectives
            if obj.get("active", False) and not obj.get("completed", False)
        ]
        if active_objectives:
            for obj in active_objectives:
                self._print_color(
                    f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE
                )
                current_stage = self.player_character.get_current_stage_for_objective(
                    obj.get("id")
                )
                if current_stage:
                    self._print_color(
                        f"  Current Stage: {current_stage.get('description', 'No stage description')}",
                        Colors.CYAN,
                    )
        else:
            self._print_color("No active objectives.", Colors.DIM)
        self._print_color("\n--- Inventory Highlights ---", Colors.CYAN + Colors.BOLD)
        if self.player_character.inventory:
            highlights = []
            for item_obj in self.player_character.inventory:
                item_name = item_obj["name"]
                item_qty = item_obj.get("quantity", 1)
                item_default_props = DEFAULT_ITEMS.get(item_name, {})
                if (
                    item_default_props.get("stackable")
                    or item_default_props.get("value") is not None
                ) and item_qty > 1:
                    highlights.append(f"{item_name} (x{item_qty})")
                else:
                    highlights.append(item_name)
            if highlights:
                self._print_color(", ".join(highlights), Colors.GREEN)
            else:
                self._print_color("Carrying some items.", Colors.DIM)
        else:
            self._print_color("Carrying nothing of note.", Colors.DIM)
        self._print_color("\n--- Relationships ---", Colors.CYAN + Colors.BOLD)
        meaningful_relationships = False
        for char_name, char_obj in self.all_character_objects.items():
            if char_obj.is_player:
                continue
            if (
                hasattr(char_obj, "relationship_with_player")
                and char_obj.relationship_with_player != 0
            ):
                relationship_text = self.get_relationship_text(
                    char_obj.relationship_with_player
                )
                self._print_color(f"- {char_name}: {relationship_text}", Colors.WHITE)
                meaningful_relationships = True
        if not meaningful_relationships:
            self._print_color(
                "No significant relationships established yet.", Colors.DIM
            )
        self._print_color("", Colors.RESET)

    def _handle_inventory_command(self):
        if self.player_character:
            self._print_color("\n--- Your Inventory ---", Colors.CYAN + Colors.BOLD)
            inv_desc = self.player_character.get_inventory_description()
            if inv_desc.startswith("You are carrying: "):
                items_str = inv_desc.replace("You are carrying: ", "", 1)
                if items_str.lower() == "nothing.":
                    self._print_color("- Nothing", Colors.DIM)
                else:
                    items_list = items_str.split(", ")
                    for item_with_details in items_list:
                        self._print_color(
                            f"- {item_with_details.rstrip('.')}", Colors.GREEN
                        )
                    if items_list:
                        self._print_color(
                            "(Hint: You can 'use [item]', 'read [item]', 'drop [item]', or 'give [item] to [person]'.)",
                            Colors.DIM,
                        )
            elif inv_desc.lower() == "you are carrying nothing.":
                self._print_color("- Nothing", Colors.DIM)
            else:
                print(inv_desc)
        else:
            self._print_color(
                "Cannot display inventory: Player character not available.", Colors.RED
            )
