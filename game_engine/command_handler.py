# command_handler.py
"""
Mixin for handling player commands and input interpretation.
"""

import re
import difflib
from .game_config import (
    Colors,
    COMMAND_SYNONYMS,
    VERBOSITY_LEVELS,
    COLOR_THEME_MAP,
    TIME_UNITS_PER_PLAYER_ACTION,
    DEFAULT_ITEMS,
    apply_color_theme,
)
from .location_module import LOCATIONS_DATA


class CommandHandler:
    """Service for handling player commands and input interpretation."""

    def __init__(self, game_state):
        self.game_state = game_state

    def _canonical_command_text(self, command, argument):
        if command is None:
            return ""
        if argument is None:
            return str(command)
        if isinstance(argument, tuple):
            if command == "use" and len(argument) == 3:
                item_name, target_name, mode = argument
                if mode == "give" and target_name:
                    return f"give {item_name} to {target_name}"
                if mode == "read":
                    return f"read {item_name}"
                if mode == "use_on" and target_name:
                    return f"use {item_name} on {target_name}"
                return f"use {item_name}"
            if command == "persuade" and len(argument) == 2:
                return f"persuade {argument[0]} that {argument[1]}"
            return str(command)
        return f"{command} {argument}".strip()

    def _record_command_history(self, command, argument):
        if not command or command in ["history", "retry", "rephrase", "select_item"]:
            return
        command_text = self._canonical_command_text(command, argument)
        if not command_text:
            return
        self.game_state.command_history.append(command_text)
        if len(self.game_state.command_history) > self.game_state.max_command_history:
            self.game_state.command_history.pop(0)

    def _resolve_prefix_match(self, target, options, label, descriptor_lookup=None):
        target = target.lower()
        matches = [option for option in options if option.lower().startswith(target)]
        if not matches:
            return None, False
        if len(matches) > 1:
            entries = []
            for option in matches[:5]:
                descriptor = descriptor_lookup(option) if descriptor_lookup else ""
                if descriptor:
                    entries.append(f"{option} ({descriptor})")
                else:
                    entries.append(option)
            self.game_state._print_color(
                f"Which {label} did you mean? {'; '.join(entries)}", Colors.YELLOW
            )
            return None, True
        return matches[0], False

    def _get_matching_location_item(self, target):
        location_items = self.game_state.dynamic_location_items.get(
            self.game_state.current_location_name, []
        )
        options = [item_info["name"] for item_info in location_items]
        match, ambiguous = self._resolve_prefix_match(
            target,
            options,
            "item",
            descriptor_lookup=self.game_state._describe_item_brief,
        )
        if ambiguous or not match:
            return None, ambiguous
        return (
            next(
                (item_info for item_info in location_items if item_info["name"] == match),
                None,
            ),
            False,
        )

    def _get_matching_inventory_item(self, target):
        if not self.game_state.player_character:
            return None, False
        options = [item_info["name"] for item_info in self.game_state.player_character.inventory]
        match, ambiguous = self._resolve_prefix_match(
            target,
            options,
            "item",
            descriptor_lookup=self.game_state._describe_item_brief,
        )
        if ambiguous or not match:
            return None, ambiguous
        return (
            next(
                (
                    item_info
                    for item_info in self.game_state.player_character.inventory
                    if item_info["name"] == match
                ),
                None,
            ),
            False,
        )

    def _get_matching_npc(self, target):
        options = [npc.name for npc in self.game_state.npcs_in_current_location]
        match, ambiguous = self._resolve_prefix_match(
            target,
            options,
            "person",
            descriptor_lookup=self.game_state._describe_npc_brief,
        )
        if ambiguous or not match:
            return None, ambiguous
        return (
            next(
                (npc for npc in self.game_state.npcs_in_current_location if npc.name == match),
                None,
            ),
            False,
        )

    def _get_matching_exit(self, target_input, location_exits):
        matches = []
        for target_loc_key, desc_text in location_exits.items():
            if (
                target_loc_key.lower() == target_input
                or desc_text.lower().startswith(target_input)
                or target_input in desc_text.lower()
            ):
                matches.append(target_loc_key)
        if not matches:
            return None, False
        if len(matches) > 1:
            descriptions = []
            for match in matches[:5]:
                desc = location_exits.get(match, "")
                descriptions.append(f"{match} ({desc})" if desc else match)
            self.game_state._print_color(
                f"Which exit did you mean? {'; '.join(descriptions)}", Colors.YELLOW
            )
            return None, True
        return matches[0], False

    def _is_known_command(self, command):
        if not command:
            return False
        known_commands = set(COMMAND_SYNONYMS.keys())
        known_commands.update(["select_item"])
        return command in known_commands

    def _build_intent_context(self):
        current_location_data = LOCATIONS_DATA.get(self.game_state.current_location_name, {})
        exits = []
        for exit_target, exit_desc in current_location_data.get("exits", {}).items():
            exits.append({"name": exit_target, "description": exit_desc})
        items = [
            item_info["name"]
            for item_info in self.game_state.dynamic_location_items.get(
                self.game_state.current_location_name, []
            )
        ]
        npcs = [npc.name for npc in self.game_state.npcs_in_current_location]
        inventory = (
            [item_info["name"] for item_info in self.game_state.player_character.inventory]
            if self.game_state.player_character
            else []
        )
        return {"exits": exits, "items": items, "npcs": npcs, "inventory": inventory}

    def _handle_unknown_intent(self):
        self.game_state._print_color("Your mind is too clouded to focus on that.", Colors.YELLOW)
        context_examples = self._get_contextual_command_examples()
        if context_examples:
            self.game_state._print_color(f"Try: {', '.join(context_examples)}", Colors.DIM)

    def _get_contextual_command_examples(self):
        context = self._build_intent_context()
        examples = ["look", "help movement", "help social"]

        if context.get("npcs"):
            examples.append(f"talk to {context['npcs'][0]}")
        if context.get("items"):
            examples.append(f"take {context['items'][0]}")
        if context.get("exits"):
            first_exit = context["exits"][0].get("name")
            if first_exit:
                examples.append(f"move to {first_exit}")

        seen = set()
        unique_examples = []
        for example in examples:
            if example not in seen:
                unique_examples.append(example)
                seen.add(example)
            if len(unique_examples) >= 4:
                break
        return unique_examples

    def _interpret_with_nlp(self, raw_input):
        context = self._build_intent_context()
        intent_payload = self.game_state.nl_parser.parse_player_intent(raw_input, context)
        if intent_payload.get("intent") == "unknown" or intent_payload.get("confidence", 0.0) < 0.7:
            self._handle_unknown_intent()
            return None, None
        intent = intent_payload.get("intent")
        target = intent_payload.get("target")
        if intent == "move":
            return "move to", target
        if intent == "take":
            return "take", target
        if intent == "examine":
            return "look", target
        if intent == "talk":
            return "talk to", target
        self._handle_unknown_intent()
        return None, None

    def _get_command_suggestions(self, command_text, limit=3):
        candidates = []
        for base_cmd, synonyms in COMMAND_SYNONYMS.items():
            candidates.append(base_cmd)
            candidates.extend(synonyms)
        return difflib.get_close_matches(command_text, candidates, n=limit, cutoff=0.5)

    def parse_action(self, raw_input):
        action = raw_input.strip().lower()
        if not action:
            return None, None
        give_match = re.match(r"^(give|offer)\s+(.+?)\s+to\s+(.+)$", action)
        if give_match:
            return "use", (
                give_match.group(2).strip(),
                give_match.group(3).strip(),
                "give",
            )
        read_match = re.match(r"^(read|peruse)\s+(.+)$", action)
        if read_match:
            return "use", (read_match.group(2).strip(), None, "read")
        use_on_match = re.match(r"^(use|apply)\s+(.+?)\s+on\s+(.+)$", action)
        if use_on_match:
            return "use", (
                use_on_match.group(2).strip(),
                use_on_match.group(3).strip(),
                "use_on",
            )
        persuade_match = re.match(
            r"^(persuade|convince|argue with)\s+(.+?)\s+(?:that|to)\s+(.+)$", action
        )
        if persuade_match:
            return "persuade", (
                persuade_match.group(2).strip(),
                persuade_match.group(3).strip(),
            )

        matched_command = None
        best_match_length = 0
        parsed_arg = None
        for base_cmd, synonyms in COMMAND_SYNONYMS.items():
            for cmd_to_check in [base_cmd] + synonyms:
                if action == cmd_to_check:
                    if len(cmd_to_check) > best_match_length:
                        matched_command = base_cmd
                        best_match_length = len(cmd_to_check)
                        parsed_arg = None
                elif action.startswith(cmd_to_check + " "):
                    if len(cmd_to_check) > best_match_length:
                        matched_command = base_cmd
                        best_match_length = len(cmd_to_check)
                        parsed_arg = action[len(cmd_to_check) :].strip()
        if matched_command:
            return matched_command, parsed_arg
        parts = action.split(" ", 1)
        return parts[0], parts[1] if len(parts) > 1 else None

    def _get_player_input(self):
        player_state_info = (
            f"{self.game_state.player_character.apparent_state}"
            if self.game_state.player_character
            else "Unknown state"
        )
        prompt_hint_objects = []
        hint_types_added = set()
        if (
            hasattr(self.game_state, "numbered_actions_context")
            and self.game_state.numbered_actions_context
        ):
            if "talk" not in hint_types_added and len(prompt_hint_objects) < 2:
                for action_info in self.game_state.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2:
                        break
                    if action_info["type"] == "talk":
                        current_action_type = "talk"
                        current_target = action_info["target"]
                        display_string = f"Talk to {current_target}"
                        is_duplicate = any(
                            ex_h["action_type"] == current_action_type
                            and (
                                ex_h["target"].startswith(current_target)
                                or current_target.startswith(ex_h["target"])
                            )
                            for ex_h in prompt_hint_objects
                        )
                        if not is_duplicate:
                            prompt_hint_objects.append(
                                {
                                    "action_type": current_action_type,
                                    "target": current_target,
                                    "display_string": display_string,
                                }
                            )
                            hint_types_added.add("talk")
                            break
            if len(prompt_hint_objects) < 2 and "item_take" not in hint_types_added:
                for action_info in self.game_state.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2:
                        break
                    if action_info["type"] == "take" and DEFAULT_ITEMS.get(
                        action_info["target"], {}
                    ).get("is_notable", False):
                        current_action_type = "item_take"
                        current_target = action_info["target"]
                        display_string = f"Take {current_target}"
                        is_duplicate = any(
                            ex_h["action_type"] == current_action_type
                            and (
                                ex_h["target"].startswith(current_target)
                                or current_target.startswith(ex_h["target"])
                            )
                            for ex_h in prompt_hint_objects
                        )
                        if not is_duplicate:
                            prompt_hint_objects.append(
                                {
                                    "action_type": current_action_type,
                                    "target": current_target,
                                    "display_string": display_string,
                                }
                            )
                            hint_types_added.add("item_take")
                            break
            if len(prompt_hint_objects) < 2 and "item_examine" not in hint_types_added:
                for action_info in self.game_state.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2:
                        break
                    if action_info["type"] == "look_at_item" and DEFAULT_ITEMS.get(
                        action_info["target"], {}
                    ).get("is_notable", False):
                        current_action_type = "item_examine"
                        current_target = action_info["target"]
                        display_string = f"Examine {current_target}"
                        is_duplicate = any(
                            ex_h["action_type"] == current_action_type
                            and (
                                ex_h["target"].startswith(current_target)
                                or current_target.startswith(ex_h["target"])
                            )
                            for ex_h in prompt_hint_objects
                        )
                        if not is_duplicate:
                            prompt_hint_objects.append(
                                {
                                    "action_type": current_action_type,
                                    "target": current_target,
                                    "display_string": display_string,
                                }
                            )
                            hint_types_added.add("item_examine")
                            break
            if len(prompt_hint_objects) < 2 and "item_take" not in hint_types_added:
                for action_info in self.game_state.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2:
                        break
                    if action_info["type"] == "take":
                        current_action_type = "item_take"
                        current_target = action_info["target"]
                        display_string = f"Take {current_target}"
                        is_duplicate = any(
                            ex_h["action_type"] == current_action_type
                            and (
                                ex_h["target"].startswith(current_target)
                                or current_target.startswith(ex_h["target"])
                            )
                            for ex_h in prompt_hint_objects
                        )
                        if not is_duplicate:
                            prompt_hint_objects.append(
                                {
                                    "action_type": current_action_type,
                                    "target": current_target,
                                    "display_string": display_string,
                                }
                            )
                            hint_types_added.add("item_take")
                            break
            if len(prompt_hint_objects) < 2 and "item_examine" not in hint_types_added:
                for action_info in self.game_state.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2:
                        break
                    if action_info["type"] == "look_at_item":
                        current_action_type = "item_examine"
                        current_target = action_info["target"]
                        display_string = f"Examine {current_target}"
                        is_duplicate = any(
                            ex_h["action_type"] == current_action_type
                            and (
                                ex_h["target"].startswith(current_target)
                                or current_target.startswith(ex_h["target"])
                            )
                            for ex_h in prompt_hint_objects
                        )
                        if not is_duplicate:
                            prompt_hint_objects.append(
                                {
                                    "action_type": current_action_type,
                                    "target": current_target,
                                    "display_string": display_string,
                                }
                            )
                            hint_types_added.add("item_examine")
                            break
            if "move" not in hint_types_added and len(prompt_hint_objects) < 2:
                for action_info in self.game_state.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2:
                        break
                    if action_info["type"] == "move":
                        current_action_type = "move"
                        current_target = action_info["target"]
                        display_string = f"Go to {current_target}"
                        is_duplicate = any(
                            ex_h["action_type"] == current_action_type
                            and (
                                ex_h["target"].startswith(current_target)
                                or current_target.startswith(ex_h["target"])
                            )
                            for ex_h in prompt_hint_objects
                        )
                        if not is_duplicate:
                            prompt_hint_objects.append(
                                {
                                    "action_type": current_action_type,
                                    "target": current_target,
                                    "display_string": display_string,
                                }
                            )
                            hint_types_added.add("move")
                            break
        active_hint_display_strings = [h["display_string"] for h in prompt_hint_objects[:2]]
        hint_string = (
            f" (Hint: {Colors.DIM}{' | '.join(active_hint_display_strings)}{Colors.RESET})"
            if active_hint_display_strings
            else (
                f" (Hint: {Colors.DIM}type 'look' or 'help'{Colors.RESET})"
                if not (
                    hasattr(self.game_state, "numbered_actions_context")
                    and self.game_state.numbered_actions_context
                )
                else ""
            )
        )
        time_info = self.game_state._get_current_game_time_period_str()
        mode_label = self.game_state._get_mode_label()
        prompt_text = (
            f"\n[{Colors.DIM}{time_info}{Colors.RESET} | {Colors.CYAN}{self.game_state.current_location_name}{Colors.RESET} "
            f"| {mode_label} | {self.game_state.verbosity_level} | {player_state_info}]"
            f"{hint_string} What do you do? {self.game_state._prompt_arrow()}"
        )
        raw_action_input = self.game_state._input_color(prompt_text, Colors.WHITE)
        fast_input = raw_action_input.strip().lower()
        if fast_input == "!!":
            if not self.game_state.command_history:
                self.game_state._print_color("No previous command to repeat yet.", Colors.YELLOW)
                return None, None
            repeated_command = self.game_state.command_history[-1]
            self.game_state._print_color(f"Repeating: {repeated_command}", Colors.DIM)
            raw_action_input = repeated_command
            fast_input = raw_action_input.strip().lower()
        fast_map = {
            "n": ("move to", "north"),
            "s": ("move to", "south"),
            "e": ("move to", "east"),
            "w": ("move to", "west"),
            "look": ("look", None),
            "l": ("look", None),
            "inv": ("inventory", None),
            "i": ("inventory", None),
        }
        if fast_input in fast_map:
            return fast_map[fast_input]
        try:
            action_number = int(raw_action_input)
            if 1 <= action_number <= len(self.game_state.numbered_actions_context):
                action_info = self.game_state.numbered_actions_context[action_number - 1]
                action_type = action_info["type"]
                target = action_info["target"]
                if action_type == "move":
                    return "move to", target
                if action_type == "talk":
                    return "talk to", target
                if action_type == "take":
                    return "take", target
                if action_type == "look_at_item":
                    return "look", target
                if action_type == "look_at_npc":
                    return "look", target
                if action_info["type"] == "select_item":
                    return ("select_item", action_info["target"])
            else:
                parsed_command, parsed_argument = self.parse_action(raw_action_input)
                if self._is_known_command(parsed_command):
                    return parsed_command, parsed_argument
                if self.game_state.gemini_api.model:
                    return self._interpret_with_nlp(raw_action_input)
                self._handle_unknown_intent()
                return None, None
        except ValueError:
            parsed_command, parsed_argument = self.parse_action(raw_action_input)
            if self._is_known_command(parsed_command):
                return parsed_command, parsed_argument
            if self.game_state.gemini_api.model:
                return self._interpret_with_nlp(raw_action_input)
            self._handle_unknown_intent()
            return None, None
        return None, None

    def _handle_theme_command(self, argument):
        if not argument:
            available = ", ".join(COLOR_THEME_MAP.keys())
            self.game_state._print_color(
                f"Current theme: {self.game_state.color_theme}. Available: {available}.",
                Colors.CYAN,
            )
            return
        requested_theme = str(argument).strip().lower()
        applied_theme = apply_color_theme(requested_theme)
        if not applied_theme:
            self.game_state._print_color(
                f"Unknown theme '{requested_theme}'. Use: {', '.join(COLOR_THEME_MAP.keys())}.",
                Colors.YELLOW,
            )
            return
        self.game_state.color_theme = applied_theme
        self.game_state._print_color(f"Theme set to {self.game_state.color_theme}.", Colors.GREEN)

    def _handle_verbosity_command(self, argument):
        if not argument:
            self.game_state._print_color(
                f"Current verbosity: {self.game_state.verbosity_level}. Options: {', '.join(VERBOSITY_LEVELS)}.",
                Colors.CYAN,
            )
            return
        requested_level = str(argument).strip().lower()
        if requested_level not in VERBOSITY_LEVELS:
            self.game_state._print_color(
                f"Unknown verbosity '{requested_level}'. Use: {', '.join(VERBOSITY_LEVELS)}.",
                Colors.YELLOW,
            )
            return
        self.game_state.verbosity_level = requested_level
        self.game_state._print_color(
            f"Verbosity set to {self.game_state.verbosity_level}.", Colors.GREEN
        )

    def _handle_turnheaders_command(self, argument):
        if not argument:
            status_text = "on" if self.game_state.turn_headers_enabled else "off"
            self.game_state._print_color(
                f"Turn headers are currently {status_text}. Use 'turnheaders on' or 'turnheaders off'.",
                Colors.CYAN,
            )
            return
        normalized = str(argument).strip().lower()
        if normalized in ["on", "true", "yes", "1"]:
            self.game_state.turn_headers_enabled = True
            self.game_state._print_color("Turn headers enabled.", Colors.GREEN)
            return
        if normalized in ["off", "false", "no", "0"]:
            self.game_state.turn_headers_enabled = False
            self.game_state._print_color("Turn headers disabled.", Colors.GREEN)
            return
        self.game_state._print_color(
            "Invalid value. Use 'turnheaders on' or 'turnheaders off'.", Colors.YELLOW
        )

    def _handle_retry_or_rephrase(self, mode):
        if not self.game_state.last_ai_generated_text:
            self.game_state._print_color(
                "No recent AI text available to rework yet.", Colors.YELLOW
            )
            return False
        if not self.game_state.gemini_api.model or self.game_state.low_ai_data_mode:
            self.game_state._print_color("Retry/rephrase requires active AI mode.", Colors.YELLOW)
            return False

        if mode == "retry":
            prompt = (
                "Rewrite this game narration with a different angle and details while preserving meaning:\n"
                f"{self.game_state.last_ai_generated_text}"
            )
        else:
            prompt = (
                "Rephrase this game narration for clarity in 1-2 concise sentences, preserving meaning:\n"
                f"{self.game_state.last_ai_generated_text}"
            )

        regenerated_text = self.game_state.gemini_api._generate_content_with_fallback(
            prompt, f"{mode} last AI output"
        )
        if regenerated_text is None or (
            isinstance(regenerated_text, str) and regenerated_text.startswith("(OOC:")
        ):
            self.game_state._print_color(
                "Could not generate an alternate version right now.", Colors.YELLOW
            )
            return False

        final_text = self.game_state._apply_verbosity(regenerated_text)
        self.game_state._print_color(f'{mode.title()}: "{final_text}"', Colors.CYAN)
        self.game_state._remember_ai_output(final_text, f"{mode}_command")
        return True

    def _process_command(self, command, argument):
        show_full_look_details = False
        if command == "look" or command == "move to":
            show_full_look_details = True
        action_taken_this_turn = True
        time_to_advance = TIME_UNITS_PER_PLAYER_ACTION
        show_atmospherics_this_turn = True
        if command == "quit":
            self.game_state._print_color("Exiting game. Goodbye.", Colors.MAGENTA)
            return False, False, 0, True
        if command == "select_item":
            item_name_selected = argument
            secondary_action_input = (
                self.game_state._input_color(
                    f"What to do with {Colors.GREEN}{item_name_selected}{Colors.WHITE}? (e.g., look at, take, use, read, give to...) {self.game_state._prompt_arrow()}",
                    Colors.WHITE,
                )
                .strip()
                .lower()
            )

            if secondary_action_input == "look at":
                self.game_state._handle_look_command(
                    item_name_selected, show_full_look_details
                )  # _handle_look_command doesn't return action_taken flags
                return True, True, TIME_UNITS_PER_PLAYER_ACTION, False
            if secondary_action_input == "take":
                action_taken, show_atmospherics = self.game_state._handle_take_command(
                    item_name_selected
                )
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, show_atmospherics, time_units, False
            if secondary_action_input == "read":
                action_taken = self.game_state.handle_use_item(item_name_selected, None, "read")
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, False, time_units, False
            if secondary_action_input == "use":
                action_taken = self.game_state.handle_use_item(
                    item_name_selected, None, "use_self_implicit"
                )
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, False, time_units, False
            if secondary_action_input.startswith("give to "):
                target_npc_name = secondary_action_input.replace("give to ", "").strip()
                if not target_npc_name:
                    self.game_state._print_color("Who do you want to give it to?", Colors.RED)
                    return False, False, 0, False
                action_taken = self.game_state.handle_use_item(
                    item_name_selected, target_npc_name, "give"
                )
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, False, time_units, False
            if secondary_action_input.startswith("use on "):
                target_for_use = secondary_action_input.replace("use on ", "").strip()
                if not target_for_use:
                    self.game_state._print_color("What do you want to use it on?", Colors.RED)
                    return False, False, 0, False
                action_taken = self.game_state.handle_use_item(
                    item_name_selected, target_for_use, "use_on"
                )
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, False, time_units, False
            self.game_state._print_color(
                f"Invalid action '{secondary_action_input}' for {item_name_selected}.",
                Colors.RED,
            )
            return False, False, 0, False
        if command == "save":
            self.game_state.save_game(argument)
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "load":
            if self.game_state.load_game(argument):
                show_atmospherics_this_turn = True
            else:
                show_atmospherics_this_turn = False
            action_taken_this_turn = False
            return (
                action_taken_this_turn,
                show_atmospherics_this_turn,
                0,
                "load_triggered",
            )
        elif command == "help":
            self.game_state.display_help(argument)
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "journal":
            if self.game_state.player_character:
                self.game_state._print_color(
                    self.game_state.player_character.get_journal_summary(), Colors.CYAN
                )
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "look":
            self.game_state._handle_look_command(argument, show_full_look_details)
        elif command == "inventory":
            self.game_state._handle_inventory_command()
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "take":
            action_taken_this_turn, show_atmospherics_this_turn = (
                self.game_state._handle_take_command(argument)
            )
        elif command == "drop":
            action_taken_this_turn, show_atmospherics_this_turn = (
                self.game_state._handle_drop_command(argument)
            )
        elif command == "use":
            action_taken_this_turn = self.game_state._handle_use_command(argument)
            show_atmospherics_this_turn = False
        elif command == "objectives":
            self.game_state.display_objectives()
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "think":
            self.game_state._handle_think_command()
            show_atmospherics_this_turn = True
        elif command == "wait":
            time_to_advance = self.game_state._handle_wait_command()
            show_atmospherics_this_turn = True
        elif command == "talk to":
            action_taken_this_turn, show_atmospherics_this_turn = (
                self.game_state._handle_talk_to_command(argument)
            )
        elif command == "move to":
            action_taken_this_turn, show_atmospherics_this_turn = (
                self.game_state.world_manager._handle_move_to_command(argument)
            )
        elif command == "persuade":
            action_taken_this_turn, show_atmospherics_this_turn = (
                self.game_state._handle_persuade_command(argument)
            )
        elif command == "status":
            self.game_state._handle_status_command()
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "toggle_lowai":
            self.game_state.low_ai_data_mode = not self.game_state.low_ai_data_mode
            self.game_state._print_color(
                f"Low AI Data Mode is now {'ON' if self.game_state.low_ai_data_mode else 'OFF'}.",
                Colors.MAGENTA,
            )
            return False, False, 0, False  # No action, no time, no atmospherics
        elif command == "history":
            self.game_state._display_command_history()
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "theme":
            self._handle_theme_command(argument)
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "verbosity":
            self._handle_verbosity_command(argument)
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "turnheaders":
            self._handle_turnheaders_command(argument)
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "retry":
            self._handle_retry_or_rephrase("retry")
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "rephrase":
            self._handle_retry_or_rephrase("rephrase")
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        else:
            suggestions = self._get_command_suggestions(command)
            suggestion_text = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            self.game_state._print_color(
                f"Unknown command: '{command}'. Type 'help' for a list of actions.{suggestion_text}",
                Colors.RED,
            )
            self.game_state._print_color(
                f"Try: {', '.join(self._get_contextual_command_examples())}", Colors.DIM
            )
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        return (
            action_taken_this_turn,
            show_atmospherics_this_turn,
            time_to_advance,
            False,
        )
