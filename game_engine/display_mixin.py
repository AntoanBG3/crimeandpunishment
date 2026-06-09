# display_mixin.py
"""Display and UI output methods for the Game class."""

import re
import random

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import terminal
from .game_config import Colors, DEFAULT_ITEMS
from .static_fallbacks import STATIC_ATMOSPHERIC_DETAILS
from .gemini_interactions import is_usable_ai_text


class DisplayMixin:
    """Mixin providing all display, output, and UI-related methods."""

    def _print_color(self, text, color_code, end="\n"):
        terminal.write_line(f"{color_code}{text}{Colors.RESET}", end=end)

    def _input_color(self, prompt_text, color_code, completion=True):
        return terminal.read_line(
            f"{color_code}{prompt_text}{Colors.RESET}", completion=completion
        )

    def _print_block(self, text, color_code):
        """Print text preceded by exactly one blank line."""
        terminal.ensure_blank_line()
        self._print_color(text, color_code)

    def _print_renderable(self, renderable):
        """Print a Rich renderable (Panel, Table, ...) through the funnel."""
        terminal.ensure_blank_line()
        terminal.write_renderable(renderable)

    def _print_narrative(self, text, color_code):
        """Print a narrative beat, paragraph-paced when the player enabled it."""
        terminal.ensure_blank_line()
        terminal.write_narrative(f"{color_code}{text}{Colors.RESET}")

    def _print_dialogue(self, speaker, quote):
        """Print a speaker-attributed line; wrapped lines hang under the name."""
        terminal.write_dialogue(
            f'{Colors.YELLOW}{speaker}:{Colors.RESET} {quote}', Colors.RESET
        )

    def _prompt_arrow(self):
        return f"{Colors.GREEN}> {Colors.RESET}"

    def _separator_line(self):
        return Colors.DIM + terminal.separator() + Colors.RESET

    def _get_mode_label(self):
        if self.low_ai_data_mode or not self.gemini_api.model:
            return "LOW-AI"
        return "AI"

    def _apply_verbosity(self, text):
        """Trim text to the chosen verbosity, always on sentence/paragraph boundaries.

        The untrimmed text is kept on self._last_full_text so the 'more'
        command can reveal the rest.
        """
        if text is None:
            return None
        normalized = str(text).strip()
        if not normalized:
            return normalized
        self._last_full_text = normalized
        if self.verbosity_level == "rich":
            return normalized
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", normalized) if p.strip()]
        first_paragraph = paragraphs[0]
        if self.verbosity_level == "brief":
            sentences = re.split(r"(?<=[.!?])\s+", first_paragraph)
            selected = " ".join(sentences[:2])
        else:  # standard
            selected = first_paragraph
        if selected != normalized:
            selected += " […more]"
        return selected

    def _handle_more_command(self):
        full_text = getattr(self, "_last_full_text", None)
        if not full_text:
            self._print_color("There is nothing more to reveal right now.", Colors.YELLOW)
            return
        self._print_block(full_text, Colors.CYAN)

    def _status_line_text(self):
        """Day/period, location, state (+LOW-AI); shared by header and toolbar."""
        time_info = self._get_current_game_time_period_str()
        location = self.current_location_name or "Unknown"
        parts = [time_info, location]
        if self.player_character and self.player_character.apparent_state:
            parts.append(self.player_character.apparent_state)
        if self._get_mode_label() == "LOW-AI":
            parts.append("LOW-AI")
        return "  ·  ".join(parts)

    def _print_turn_header(self):
        if not self.turn_headers_enabled:
            return
        self._print_block(self._status_line_text(), Colors.DIM)

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
        npc = next((n for n in self.npcs_in_current_location if n.name == npc_name), None)
        if npc is None:
            return "person here"
        return f"appears {npc.apparent_state}"

    def _display_item_properties(self, item_default):
        """One compact dim line, matching the scene listing's tag idiom."""
        tags = []
        if item_default.get("readable", False):
            tags.append("readable")
        if item_default.get("consumable", False):
            tags.append("consumable")
        if item_default.get("value") is not None:
            tags.append(f"worth {item_default['value']} kopeks")
        if item_default.get("is_notable", False):
            tags.append("notable")
        if item_default.get("owner"):
            tags.append(f"belongs to {item_default['owner']}")
        if item_default.get("use_effect_player"):
            tags.append("can be used")
        if tags:
            self._print_color(f"({' · '.join(tags)})", Colors.DIM)

    def _display_command_history(self):
        self._print_block("Recent Commands", Colors.CYAN + Colors.BOLD)
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
        # Don't repeat the same hint on consecutive non-action turns.
        if getattr(self, "_tutorial_hint_shown_for_step", 0) >= step:
            return
        if hasattr(self, "command_handler") and hasattr(
            self.command_handler, "_build_intent_context"
        ):
            context = self.command_handler._build_intent_context()
        else:
            context = {"npcs": [], "exits": []}
        talk_target = context["npcs"][0] if context.get("npcs") else None
        move_target = context["exits"][0]["name"] if context.get("exits") else "an available exit"
        examine_target = context["items"][0] if context.get("items") else None
        hint_1 = (
            f"Tutorial 1/5: Try 'look at {examine_target}' to examine something closely."
            if examine_target
            else "Tutorial 1/5: Use 'look' to survey your surroundings."
        )
        hint_2 = (
            f"Tutorial 2/5: Try 'talk to {talk_target}' to start a conversation."
            if talk_target
            else "Tutorial 2/5: Try 'look at [something]' to examine items, or 'think' to reflect."
        )
        tutorial_lines = {
            1: hint_1,
            2: hint_2,
            3: "Tutorial 3/5: Use 'objectives' to see your active goals.",
            4: f"Tutorial 4/5: Move with 'move to {move_target}'.",
            5: "Tutorial 5/5: Type 'help' for all commands, or 'help movement' / 'help social'.",
        }
        self._print_color(tutorial_lines.get(step, ""), Colors.YELLOW)
        self._tutorial_hint_shown_for_step = step

    def display_atmospheric_details(self):
        if self.player_character and self.current_location_name:
            from .game_config import ATMOSPHERIC_COOLDOWN_ACTIONS

            shown_at = getattr(self, "_atmospherics_shown_at", {})
            last_shown = shown_at.get(self.current_location_name)
            if (
                last_shown is not None
                and self.player_action_count - last_shown < ATMOSPHERIC_COOLDOWN_ACTIONS
            ):
                self.last_significant_event_summary = None
                return
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

            if not is_usable_ai_text(details) or self.low_ai_data_mode:
                if STATIC_ATMOSPHERIC_DETAILS:
                    details = random.choice(STATIC_ATMOSPHERIC_DETAILS)
                else:
                    details = "The atmosphere is thick with unspoken stories."  # Ultimate fallback
            else:
                ai_generated = True

            if details:  # Ensure details is not None if fallbacks were empty
                final_details = self._apply_verbosity(details)
                self._print_block(final_details, Colors.CYAN)
                shown_at[self.current_location_name] = self.player_action_count
                self._atmospherics_shown_at = shown_at
                if ai_generated:
                    self._remember_ai_output(final_details, "atmosphere")
            self.last_significant_event_summary = None

    def display_objectives(self):
        if not self.player_character or not self.player_character.objectives:
            self._print_block("You have no specific objectives at the moment.", Colors.DIM)
            return
        active_objectives = [
            obj
            for obj in self.player_character.objectives
            if obj.get("active", False) and not obj.get("completed", False)
        ]
        completed_objectives = [
            obj for obj in self.player_character.objectives if obj.get("completed", False)
        ]
        if not active_objectives and not completed_objectives:
            self._print_block("You have no specific objectives at the moment.", Colors.DIM)
            return
        sections = []
        if active_objectives:
            sections.append(Text("Ongoing", style="bold yellow"))
            for obj in active_objectives:
                sections.append(
                    Text(f"• {obj.get('description', 'Unnamed objective')}", style="white")
                )
                current_stage = self.player_character.get_current_stage_for_objective(obj.get("id"))
                if current_stage:
                    sections.append(
                        Text(
                            f"  Current Stage: {current_stage.get('description', 'No stage description')}",
                            style="cyan",
                        )
                    )
        else:
            sections.append(Text("No active objectives right now.", style="dim"))
        if completed_objectives:
            sections.append(Text("Completed", style="bold green"))
            for obj in completed_objectives:
                sections.append(
                    Text(f"• {obj.get('description', 'Unnamed objective')}", style="dim white")
                )
        self._print_renderable(
            Panel(Group(*sections), title="Your Objectives", border_style="cyan", expand=False)
        )

    def display_help(self, category=None):
        self._print_block(
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
                (
                    "confess",
                    "When the time and place are right, take your story's decisive turn.",
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
                ("more", "Show the rest of the last trimmed narrative text."),
                ("saves", "List existing save slots."),
                ("pace [on|off]", "Reveal dreams and major beats paragraph by paragraph."),
                ("theme [default|high-contrast|mono]", "Switch color profile."),
                ("verbosity [brief|standard|rich]", "Adjust narrative text density."),
                ("turnheaders [on|off]", "Toggle turn boundary headers."),
                ("quit / exit / q", "Exit the game."),
            ],
        }

        normalized_category = (
            category.strip().lower() if isinstance(category, str) and category.strip() else "all"
        )
        if normalized_category == "all":
            groups_to_show = action_groups
        elif normalized_category in action_groups:
            groups_to_show = {normalized_category: action_groups[normalized_category]}
        else:
            available = ", ".join(action_groups.keys())
            self._print_color(
                f"Unknown help category '{category}'. Available: {available}. Showing all commands.",
                Colors.YELLOW,
            )
            groups_to_show = action_groups

        sections = []
        for group_name, actions in groups_to_show.items():
            grid = Table.grid(padding=(0, 2))
            grid.add_column(style="magenta", no_wrap=False, max_width=40)
            grid.add_column(style="white")
            for cmd, desc in actions:
                # Wrap in Text so '[item name]' isn't parsed as Rich markup.
                grid.add_row(Text(cmd), Text(desc))
            sections.append(
                Panel(grid, title=group_name.capitalize(), border_style="cyan", expand=False)
            )
        self._print_renderable(Group(*sections))
        self._print_color(
            "Tip: use 'help movement', 'help social', 'help items', or 'help meta'.",
            Colors.DIM,
        )

    def _display_load_recap(self):
        if not self.player_character:
            return

        self._print_block("Session Recap", Colors.CYAN + Colors.BOLD)
        self._print_color(f"Location: {self.current_location_name}", Colors.WHITE)
        self._print_color(f"Time: {self._get_current_game_time_period_str()}", Colors.WHITE)

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

        recent_events = self.key_events_occurred[-3:] if self.key_events_occurred else []
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
                self._print_color(f"- {character_name}: {relationship_text}", Colors.DIM)

    def _display_turn_feedback(self, show_atmospherics_this_turn, command):
        if show_atmospherics_this_turn:
            self.display_atmospheric_details()
        elif command == "load":
            self.last_significant_event_summary = None

    def _handle_status_command(self):
        if not self.player_character:
            self._print_color("No player character loaded.", Colors.RED)
            return
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
        ai_mode = (
            "Low AI / Fallback Friendly" if self._get_mode_label() == "LOW-AI" else "AI Dynamic"
        )

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold cyan", justify="right")
        grid.add_column()
        grid.add_row("Name", Text(str(self.player_character.name), style="green"))
        grid.add_row(
            "Apparent State", Text(str(self.player_character.apparent_state), style="yellow")
        )
        grid.add_row("Location", Text(str(self.current_location_name), style="cyan"))
        grid.add_row(
            "Notoriety",
            Text(f"{notoriety_desc} (Level {self.player_notoriety_level:.1f})", style="magenta"),
        )
        grid.add_row("Narrative Mode", ai_mode)
        grid.add_row("Theme", str(self.color_theme))
        grid.add_row("Verbosity", str(self.verbosity_level))
        grid.add_row("Turn Headers", "on" if self.turn_headers_enabled else "off")
        if self.player_action_count < self.tutorial_turn_limit:
            grid.add_row(
                "Tutorial",
                Text(
                    f"{self.player_action_count}/{self.tutorial_turn_limit} actions",
                    style="dim",
                ),
            )
        sections = [grid]

        sections.append(Text("Skills", style="bold cyan"))
        if self.player_character.skills:
            for skill_name, value in self.player_character.skills.items():
                sections.append(Text(f"• {skill_name.capitalize()}: {value}", style="white"))
        else:
            sections.append(Text("No specialized skills.", style="dim"))

        sections.append(Text("Active Objectives", style="bold cyan"))
        active_objectives = [
            obj
            for obj in self.player_character.objectives
            if obj.get("active", False) and not obj.get("completed", False)
        ]
        if active_objectives:
            for obj in active_objectives:
                sections.append(
                    Text(f"• {obj.get('description', 'Unnamed objective')}", style="white")
                )
                current_stage = self.player_character.get_current_stage_for_objective(obj.get("id"))
                if current_stage:
                    sections.append(
                        Text(
                            f"  Current Stage: {current_stage.get('description', 'No stage description')}",
                            style="cyan",
                        )
                    )
        else:
            sections.append(Text("No active objectives.", style="dim"))

        sections.append(Text("Inventory Highlights", style="bold cyan"))
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
                sections.append(Text(", ".join(highlights), style="green"))
            else:
                sections.append(Text("Carrying some items.", style="dim"))
        else:
            sections.append(Text("Carrying nothing of note.", style="dim"))

        sections.append(Text("Relationships", style="bold cyan"))
        meaningful_relationships = False
        for char_name, char_obj in self.all_character_objects.items():
            if char_obj.is_player:
                continue
            if (
                hasattr(char_obj, "relationship_with_player")
                and char_obj.relationship_with_player != 0
            ):
                relationship_text = self.get_relationship_text(char_obj.relationship_with_player)
                sections.append(Text(f"• {char_name}: {relationship_text}", style="white"))
                meaningful_relationships = True
        if not meaningful_relationships:
            sections.append(Text("No significant relationships established yet.", style="dim"))

        self._print_renderable(
            Panel(Group(*sections), title="Your Status", border_style="cyan", expand=False)
        )

    def _handle_inventory_command(self):
        if self.player_character:
            inv_desc = self.player_character.get_inventory_description()
            if inv_desc.startswith("You are carrying: "):
                items_str = inv_desc.replace("You are carrying: ", "", 1)
                if items_str.lower() == "nothing.":
                    self._print_block("You are carrying nothing.", Colors.DIM)
                else:
                    table = Table(
                        title="Your Inventory",
                        border_style="cyan",
                        title_style="bold cyan",
                        show_header=False,
                        expand=False,
                        min_width=30,
                    )
                    table.add_column(style="green")
                    items_list = items_str.split(", ")
                    for item_with_details in items_list:
                        table.add_row(item_with_details.rstrip("."))
                    self._print_renderable(table)
                    if items_list:
                        self._print_color(
                            "(Hint: You can 'use [item]', 'read [item]', 'drop [item]', or 'give [item] to [person]'.)",
                            Colors.DIM,
                        )
            elif inv_desc.lower() == "you are carrying nothing.":
                self._print_block("You are carrying nothing.", Colors.DIM)
            else:
                self._print_color(inv_desc, Colors.RESET)
        else:
            self._print_color(
                "Cannot display inventory: Player character not available.", Colors.RED
            )
