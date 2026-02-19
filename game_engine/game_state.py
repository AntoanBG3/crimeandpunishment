# game_state.py
import json
import os
import re
import random
import copy
import difflib

from .game_config import (Colors, SAVE_GAME_FILE, # API_CONFIG_FILE, GEMINI_MODEL_NAME removed
                         CONCLUDING_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS,
                         TIME_UNITS_PER_PLAYER_ACTION, MAX_TIME_UNITS_PER_DAY, TIME_PERIODS,
                         TIME_UNITS_FOR_NPC_INTERACTION_CHANCE, NPC_INTERACTION_CHANCE,
                         TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE, NPC_MOVE_CHANCE,
                         DEFAULT_ITEMS, COMMAND_SYNONYMS, PLAYER_APPARENT_STATES,
                         DREAM_CHANCE_NORMAL_STATE, DREAM_CHANCE_TROUBLED_STATE,
                         RUMOR_CHANCE_PER_NPC_INTERACTION, AMBIENT_RUMOR_CHANCE_PUBLIC_PLACE,
                         NPC_SHARE_RUMOR_MIN_RELATIONSHIP, GENERIC_SCENERY_KEYWORDS,
                         HIGHLY_NOTABLE_ITEMS_FOR_MEMORY,
                         apply_color_theme, COLOR_THEME_MAP, DEFAULT_COLOR_THEME,
                         DEFAULT_VERBOSITY_LEVEL, VERBOSITY_LEVELS,
                         STATIC_ATMOSPHERIC_DETAILS, generate_static_scenery_observation, # Added
                         STATIC_PLAYER_REFLECTIONS, STATIC_ENHANCED_OBSERVATIONS,      # Added
                         STATIC_NEWSPAPER_SNIPPETS, STATIC_DREAM_SEQUENCES,            # Added
                         generate_static_item_interaction_description, STATIC_RUMORS)  # Added
from .game_config import DEBUG_LOGS
from .character_module import Character, CHARACTERS_DATA
from .location_module import LOCATIONS_DATA
from .gemini_interactions import GeminiAPI, NaturalLanguageParser
from .event_manager import EventManager


class Game:
    def __init__(self):
        self.player_character = None
        self.all_character_objects = {}
        self.npcs_in_current_location = []
        self.current_location_name = None
        self.dynamic_location_items = {}

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

        self.player_notoriety_level = 0
        self.known_facts_about_crime = ["An old pawnbroker and her sister were murdered recently."]
        self.key_events_occurred = ["Game started."]
        self.numbered_actions_context = []
        self.current_conversation_log = []
        self.overheard_rumors = []
        self.low_ai_data_mode = False
        self.autosave_interval_actions = 10
        self.actions_since_last_autosave = 0
        self.player_action_count = 0
        self.tutorial_turn_limit = 5
        self.command_history = []
        self.max_command_history = 25
        self.turn_headers_enabled = True
        self.last_turn_result_icon = "..."
        self.verbosity_level = DEFAULT_VERBOSITY_LEVEL
        self.color_theme = DEFAULT_COLOR_THEME
        self.last_ai_generated_text = None
        self.last_ai_generation_source = None
        apply_color_theme(self.color_theme)

    def _get_current_game_time_period_str(self):
        return f"Day {self.current_day}, {self.get_current_time_period()}"

    def _get_objectives_summary(self, character):
        if not character or not character.objectives:
            return "No particular objectives."

        active_objective_details = []
        for obj in character.objectives:
            if obj.get("active") and not obj.get("completed"):
                obj_desc = obj.get('description', 'An unknown goal.')
                current_stage = character.get_current_stage_for_objective(obj.get('id'))
                if isinstance(current_stage, dict):
                    stage_desc = current_stage.get('description', 'unspecified stage')
                    active_objective_details.append(f"{obj_desc} (Currently: {stage_desc})")
                else:
                    active_objective_details.append(f"{obj_desc} (Currently: unspecified stage)")

        if not active_objective_details:
            return "Currently pursuing no specific objectives."
        prefix = "Your current objectives: " if character.is_player else f"{character.name}'s current objectives: "
        return prefix + "; ".join(active_objective_details) + "."

    def _get_recent_events_summary(self, count=3):
        if not self.key_events_occurred:
            return "Nothing much has happened yet."
        return "Key recent events: " + "; ".join(self.key_events_occurred[-count:])

    def _get_known_facts_summary(self):
        if not self.known_facts_about_crime:
            return "No specific details are widely known about the recent crime."
        return "Known facts about the crime: " + "; ".join(self.known_facts_about_crime)

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
            sentence = re.split(r'(?<=[.!?])\s+', normalized, maxsplit=1)[0]
            if len(sentence) > 180:
                sentence = sentence[:177].rstrip() + "..."
            return sentence
        if self.verbosity_level == "standard" and len(normalized) > 550:
            return normalized[:547].rstrip() + "..."
        return normalized

    def _remember_ai_output(self, text, source_label):
        if not text or not isinstance(text, str):
            return
        if text.startswith("(OOC:"):
            return
        self.last_ai_generated_text = text.strip()
        self.last_ai_generation_source = source_label

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
        self.command_history.append(command_text)
        if len(self.command_history) > self.max_command_history:
            self.command_history.pop(0)

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
        context = self._build_intent_context()
        talk_target = context["npcs"][0] if context.get("npcs") else "someone nearby"
        move_target = context["exits"][0]["name"] if context.get("exits") else "an available exit"
        tutorial_lines = {
            1: "Tutorial 1/5: Start by using 'look' to survey this location.",
            2: f"Tutorial 2/5: Try 'talk to {talk_target}' to open a social path.",
            3: "Tutorial 3/5: Use 'objectives' to check your active direction.",
            4: f"Tutorial 4/5: Travel with 'move to {move_target}' when you're ready.",
            5: "Tutorial 5/5: Need focused help? Try 'help movement' or 'help social'."
        }
        self._print_color(tutorial_lines.get(step, ""), Colors.DIM)

    def _print_turn_header(self):
        if not self.turn_headers_enabled:
            return
        time_info = self._get_current_game_time_period_str()
        location = self.current_location_name or "Unknown"
        self._print_color(self._separator_line(), Colors.DIM)
        self._print_color(
            f"[{time_info} | {location} | {self.last_turn_result_icon} | Mode: {self._get_mode_label()}]",
            Colors.DIM
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
        npc = next((n for n in self.npcs_in_current_location if n.name == npc_name), None)
        if npc is None:
            return "person here"
        return f"appears {npc.apparent_state}"

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
            self._print_color(f"Which {label} did you mean? {'; '.join(entries)}", Colors.YELLOW)
            return None, True
        return matches[0], False

    def _get_matching_location_item(self, target):
        location_items = self.dynamic_location_items.get(self.current_location_name, [])
        options = [item_info["name"] for item_info in location_items]
        match, ambiguous = self._resolve_prefix_match(
            target,
            options,
            "item",
            descriptor_lookup=self._describe_item_brief
        )
        if ambiguous or not match:
            return None, ambiguous
        return next((item_info for item_info in location_items if item_info["name"] == match), None), False

    def _get_matching_inventory_item(self, target):
        if not self.player_character:
            return None, False
        options = [item_info["name"] for item_info in self.player_character.inventory]
        match, ambiguous = self._resolve_prefix_match(
            target,
            options,
            "item",
            descriptor_lookup=self._describe_item_brief
        )
        if ambiguous or not match:
            return None, ambiguous
        return next((item_info for item_info in self.player_character.inventory if item_info["name"] == match), None), False

    def _get_matching_npc(self, target):
        options = [npc.name for npc in self.npcs_in_current_location]
        match, ambiguous = self._resolve_prefix_match(
            target,
            options,
            "person",
            descriptor_lookup=self._describe_npc_brief
        )
        if ambiguous or not match:
            return None, ambiguous
        return next((npc for npc in self.npcs_in_current_location if npc.name == match), None), False

    def _get_matching_exit(self, target_input, location_exits):
        matches = []
        for target_loc_key, desc_text in location_exits.items():
            if target_loc_key.lower() == target_input or desc_text.lower().startswith(target_input) or target_input in desc_text.lower():
                matches.append(target_loc_key)
        if not matches:
            return None, False
        if len(matches) > 1:
            descriptions = []
            for match in matches[:5]:
                desc = location_exits.get(match, "")
                descriptions.append(f"{match} ({desc})" if desc else match)
            self._print_color(f"Which exit did you mean? {'; '.join(descriptions)}", Colors.YELLOW)
            return None, True
        return matches[0], False

    def _is_known_command(self, command):
        if not command:
            return False
        known_commands = set(COMMAND_SYNONYMS.keys())
        known_commands.update(["select_item"])
        return command in known_commands

    def _build_intent_context(self):
        current_location_data = LOCATIONS_DATA.get(self.current_location_name, {})
        exits = []
        for exit_target, exit_desc in current_location_data.get("exits", {}).items():
            exits.append({"name": exit_target, "description": exit_desc})
        items = [item_info["name"] for item_info in self.dynamic_location_items.get(self.current_location_name, [])]
        npcs = [npc.name for npc in self.npcs_in_current_location]
        inventory = [item_info["name"] for item_info in self.player_character.inventory] if self.player_character else []
        return {"exits": exits, "items": items, "npcs": npcs, "inventory": inventory}

    def _handle_unknown_intent(self):
        self._print_color("Your mind is too clouded to focus on that.", Colors.YELLOW)
        context_examples = self._get_contextual_command_examples()
        if context_examples:
            self._print_color(f"Try: {', '.join(context_examples)}", Colors.DIM)

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
        intent_payload = self.nl_parser.parse_player_intent(raw_input, context)
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

    def _display_item_properties(self, item_default):
        properties_to_display = []
        if item_default.get('readable', False): properties_to_display.append(f"Type: Readable")
        if item_default.get('consumable', False): properties_to_display.append(f"Type: Consumable")
        if item_default.get('value') is not None: properties_to_display.append(f"Value: {item_default['value']} kopeks")
        if item_default.get('is_notable', False): properties_to_display.append(f"Trait: Notable")
        if item_default.get('stackable', False): properties_to_display.append(f"Trait: Stackable")
        if item_default.get('owner'): properties_to_display.append(f"Belongs to: {item_default['owner']}")
        if item_default.get('use_effect_player'): properties_to_display.append(f"Action: Can be 'used'")
        if properties_to_display:
            self._print_color("--- Properties ---", Colors.BLUE + Colors.BOLD)
            for prop_str in properties_to_display: self._print_color(f"- {prop_str}", Colors.BLUE)
            self._print_color("", Colors.RESET)

    def _get_command_suggestions(self, command_text, limit=3):
        candidates = []
        for base_cmd, synonyms in COMMAND_SYNONYMS.items():
            candidates.append(base_cmd)
            candidates.extend(synonyms)
        return difflib.get_close_matches(command_text, candidates, n=limit, cutoff=0.5)

    def _inspect_item(self, item_name, item_default, action_context, observation_context, allow_npc_memory):
        if not self.player_character:
            self._print_color("Cannot inspect item: Player character not available.", Colors.RED)
            return
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        self._print_color(f"You examine the {item_name}:", Colors.GREEN)
        gen_desc = None
        base_desc_for_skill_check = item_default.get('description', "An ordinary item.")

        if not self.low_ai_data_mode and self.gemini_api.model:
            gen_desc = self.gemini_api.get_item_interaction_description(
                player_character, item_name, item_default, action_context,
                current_location_name, self.get_current_time_period()
            )

        if gen_desc is not None and not (isinstance(gen_desc, str) and gen_desc.startswith("(OOC:")) and not self.low_ai_data_mode:
            gen_desc = self._apply_verbosity(gen_desc)
            self._print_color(f"\"{gen_desc}\"", Colors.GREEN)
            base_desc_for_skill_check = gen_desc
            self._remember_ai_output(gen_desc, "item_inspection")
        else:
            if self.low_ai_data_mode or gen_desc is None or (isinstance(gen_desc, str) and gen_desc.startswith("(OOC:")):
                gen_desc = generate_static_item_interaction_description(item_name, "examine")
                self._print_color(f"\"{self._apply_verbosity(gen_desc)}\"", Colors.CYAN)
            else:
                self._print_color(f"({base_desc_for_skill_check})", Colors.DIM)

        self._display_item_properties(item_default)

        if player_character.check_skill("Observation", 1):
            self._print_color("(Your keen eye picks up on finer details...)", Colors.CYAN + Colors.DIM)
            detailed_observation = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                detailed_observation = self.gemini_api.get_enhanced_observation(
                    player_character,
                    target_name=item_name,
                    target_category="item",
                    base_description=base_desc_for_skill_check,
                    skill_check_context=observation_context
                )

            if detailed_observation is None or (isinstance(detailed_observation, str) and detailed_observation.startswith("(OOC:")) or self.low_ai_data_mode:
                if STATIC_ENHANCED_OBSERVATIONS:
                    detailed_observation = random.choice(STATIC_ENHANCED_OBSERVATIONS)
                else:
                    detailed_observation = "You notice a few more mundane details, but nothing striking."
                if detailed_observation:
                    self._print_color(f"Detail: \"{self._apply_verbosity(detailed_observation)}\"", Colors.CYAN)
            elif detailed_observation:
                final_detail = self._apply_verbosity(detailed_observation)
                self._print_color(f"Detail: \"{final_detail}\"", Colors.GREEN)
                self._remember_ai_output(final_detail, "item_detail")

        if allow_npc_memory and item_name in HIGHLY_NOTABLE_ITEMS_FOR_MEMORY:
            for npc_observer in self.npcs_in_current_location:
                if npc_observer.name != player_character.name:
                    sentiment_impact = -2 if item_name in ["raskolnikov's axe", "bloodied rag"] else -1
                    npc_observer.add_player_memory(
                        memory_type="player_action_observed",
                        turn=self.game_time,
                        content={"action": "examined_item", "item_name": item_name, "location": current_location_name},
                        sentiment_impact=sentiment_impact
                    )

    def _validate_item_data(self):
        missing_items = set()
        for location_name, location_data in LOCATIONS_DATA.items():
            for item_info in location_data.get("items_present", []):
                item_name = item_info.get("name")
                if item_name and item_name not in DEFAULT_ITEMS:
                    missing_items.add(f"Location '{location_name}' references unknown item '{item_name}'.")

        for character_name, character_data in CHARACTERS_DATA.items():
            for item_info in character_data.get("inventory_items", []):
                item_name = item_info.get("name")
                if item_name and item_name not in DEFAULT_ITEMS:
                    missing_items.add(f"Character '{character_name}' references unknown item '{item_name}'.")

        for item_name in HIGHLY_NOTABLE_ITEMS_FOR_MEMORY:
            if item_name not in DEFAULT_ITEMS:
                missing_items.add(f"Notable items list references unknown item '{item_name}'.")

        for item_name, item_data in DEFAULT_ITEMS.items():
            hidden_location = item_data.get("hidden_in_location")
            if hidden_location and hidden_location not in LOCATIONS_DATA:
                missing_items.add(f"Item '{item_name}' references unknown hidden location '{hidden_location}'.")

        if missing_items:
            self._print_color("Warning: Item data inconsistencies detected:", Colors.YELLOW)
            for message in sorted(missing_items):
                self._print_color(f"- {message}", Colors.YELLOW)
            self._print_color("", Colors.RESET)

    def get_current_time_period(self):
        time_in_day = self.game_time % MAX_TIME_UNITS_PER_DAY
        for period, (start, end) in TIME_PERIODS.items():
            if start <= time_in_day <= end:
                return period
        self._print_color(f"Warning: Could not determine time period for game_time {self.game_time % MAX_TIME_UNITS_PER_DAY}", Colors.RED)
        return "Unknown"

    def advance_time(self, units=TIME_UNITS_PER_PLAYER_ACTION):
        previous_day = self.current_day
        self.game_time += units
        new_day_begins = (self.game_time // MAX_TIME_UNITS_PER_DAY) + 1 > previous_day

        if new_day_begins:
            self.current_day = (self.game_time // MAX_TIME_UNITS_PER_DAY) + 1
            self._print_color(f"\n{Colors.DIM}--- A new day dawns. It is Day {self.current_day}. ---{Colors.RESET}", Colors.CYAN + Colors.BOLD)
            self.key_events_occurred.append(f"Day {self.current_day} began.")
            self.last_significant_event_summary = f"a new day (Day {self.current_day}) began."
            if self.player_character and self.player_character.name == "Rodion Raskolnikov":
                troubled_states = ["feverish", "dangerously agitated", "remorseful", "paranoid", "haunted by dreams", "agitated"]
                dream_chance = DREAM_CHANCE_TROUBLED_STATE if self.player_character.apparent_state in troubled_states else DREAM_CHANCE_NORMAL_STATE
                if random.random() < dream_chance:
                    self._print_color(f"\n{Colors.MAGENTA}As morning struggles to break, unsettling images from the night still cling to your mind...{Colors.RESET}", Colors.MAGENTA)
                    relationships_summary = "Relationships are complex."
                    if self.all_character_objects.get("Sonya Marmeladova"):
                        sonya_npc = self.all_character_objects["Sonya Marmeladova"]
                        relationships_summary = f"Sonya: {self.get_relationship_text(sonya_npc.relationship_with_player if hasattr(sonya_npc, 'relationship_with_player') else 0)}"

                    dream_text = None
                    if not self.low_ai_data_mode and self.gemini_api.model:
                        dream_text = self.gemini_api.get_dream_sequence(
                            self.player_character, self._get_recent_events_summary(),
                            self._get_objectives_summary(self.player_character), relationships_summary)

                    if dream_text is None or (isinstance(dream_text, str) and dream_text.startswith("(OOC:")) or self.low_ai_data_mode:
                        if STATIC_DREAM_SEQUENCES:
                            dream_text = random.choice(STATIC_DREAM_SEQUENCES)
                        else:
                            dream_text = "You had a restless night filled with strange, fleeting images." # Ultimate fallback

                    self._print_color(f"{Colors.CYAN}Dream: \"{dream_text}\"{Colors.RESET}", Colors.CYAN)
                    self.player_character.add_journal_entry("Dream", dream_text, self._get_current_game_time_period_str())
                    # Ensure add_player_memory gets a string, even if dream_text was None initially and STATIC_DREAM_SEQUENCES was empty.
                    self.player_character.add_player_memory(f"Had a disturbing dream: {(dream_text if dream_text else '')[:50]}...")
                    if "terror" in dream_text.lower() or "blood" in dream_text.lower() or "axe" in dream_text.lower():
                        self.player_character.apparent_state = random.choice(["paranoid", "agitated", "haunted by dreams"])
                    elif "sonya" in dream_text.lower() or "hope" in dream_text.lower() or "cross" in dream_text.lower():
                        self.player_character.apparent_state = random.choice(["thoughtful", "remorseful", "hopeful"])
                    else:
                        self.player_character.apparent_state = "haunted by dreams"
                    self._print_color(f"(The dream leaves you feeling {self.player_character.apparent_state}.)", Colors.YELLOW)
                    self.last_significant_event_summary = "awoke troubled by a vivid dream."
                    self._print_color("", Colors.RESET)

        self.time_since_last_npc_interaction += units
        self.time_since_last_npc_schedule_update += units
        if self.time_since_last_npc_schedule_update >= TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE:
            self.update_npc_locations_by_schedule()
            self.time_since_last_npc_schedule_update = 0

    def display_atmospheric_details(self):
        if self.player_character and self.current_location_name:
            details = None
            ai_generated = False
            if not self.low_ai_data_mode and self.gemini_api.model:
                details = self.gemini_api.get_atmospheric_details(
                    self.player_character, self.current_location_name, self.get_current_time_period(),
                    self.last_significant_event_summary, self._get_objectives_summary(self.player_character))

            if details is None or (isinstance(details, str) and details.startswith("(OOC:")) or self.low_ai_data_mode:
                if STATIC_ATMOSPHERIC_DETAILS:
                    details = random.choice(STATIC_ATMOSPHERIC_DETAILS)
                else:
                    details = "The atmosphere is thick with unspoken stories." # Ultimate fallback
            else:
                ai_generated = True

            if details: # Ensure details is not None if fallbacks were empty
                 final_details = self._apply_verbosity(details)
                 self._print_color(f"\n{final_details}", Colors.CYAN)
                 if ai_generated:
                     self._remember_ai_output(final_details, "atmosphere")
            self.last_significant_event_summary = None

    def initialize_dynamic_location_items(self):
        self.dynamic_location_items = {}
        for loc_name, loc_data in LOCATIONS_DATA.items():
            self.dynamic_location_items[loc_name] = copy.deepcopy(loc_data.get("items_present", []))
        for item_name, item_props in DEFAULT_ITEMS.items():
            if "hidden_in_location" in item_props:
                hidden_loc = item_props["hidden_in_location"]
                if hidden_loc in self.dynamic_location_items:
                    location_items = self.dynamic_location_items[hidden_loc]
                    if not any(loc_item["name"] == item_name for loc_item in location_items):
                        qty_to_add = item_props.get("quantity", 1) if item_props.get("stackable", False) or item_props.get("value") is not None else 1
                        location_items.append({"name": item_name, "quantity": qty_to_add})

    def load_all_characters(self, from_save=False):
        if from_save: return
        self.all_character_objects = {}
        for name, data in CHARACTERS_DATA.items():
            static_data_copy = copy.deepcopy(data)
            if "accessible_locations" not in static_data_copy:
                static_data_copy["accessible_locations"] = []
            if static_data_copy.get("default_location") not in static_data_copy["accessible_locations"]:
                static_data_copy["accessible_locations"].append(static_data_copy["default_location"])
            self.all_character_objects[name] = Character(
                name, static_data_copy.get("persona","A resident of St. Petersburg."),
                static_data_copy.get("greeting", "Yes?"),
                static_data_copy.get("default_location", "Haymarket Square"),
                static_data_copy.get("accessible_locations", ["Haymarket Square"]),
                static_data_copy.get("objectives", []),
                static_data_copy.get("inventory_items", []),
                static_data_copy.get("schedule", {}))
        self.initialize_dynamic_location_items()

    def select_player_character(self, non_interactive=False):
        self._print_color("\n--- Choose Your Character ---", Colors.CYAN + Colors.BOLD)
        playable_character_names = [name for name, data in CHARACTERS_DATA.items() if not data.get("non_playable", False)]
        if not playable_character_names:
            self._print_color("Error: No playable characters defined!", Colors.RED)
            return False

        if non_interactive:
            chosen_name = playable_character_names[0]
            self._print_color(f"Automatically selecting character: {chosen_name}", Colors.YELLOW)
        else:
            for i, name in enumerate(playable_character_names):
                print(f"{Colors.MAGENTA}{i + 1}. {Colors.WHITE}{name}{Colors.RESET}")
            while True:
                try:
                    choice_str = self._input_color("Enter the number of your choice: ", Colors.MAGENTA)
                    if not choice_str: continue
                    choice = int(choice_str) - 1
                    if 0 <= choice < len(playable_character_names):
                        chosen_name = playable_character_names[choice]
                        break
                    else:
                        self._print_color("Invalid choice. Please enter a number from the list.", Colors.RED)
                except ValueError:
                    self._print_color("Invalid input. Please enter a number.", Colors.RED)

        if chosen_name in self.all_character_objects:
            self.player_character = self.all_character_objects[chosen_name]
            self.player_character.is_player = True
            self.current_location_name = self.player_character.default_location
            self.player_character.current_location = self.current_location_name
            self.current_location_description_shown_this_visit = False
            self._print_color(f"\nYou are playing as {Colors.GREEN}{self.player_character.name}{Colors.RESET}.", Colors.WHITE)
            self._print_color(f"You start in: {Colors.CYAN}{self.current_location_name}{Colors.RESET}", Colors.WHITE)
            self._print_color(f"Your current state appears: {Colors.YELLOW}{self.player_character.apparent_state}{Colors.RESET}.", Colors.WHITE)
            return True
        else:
            self._print_color(f"Error: Character '{chosen_name}' not found in loaded objects.", Colors.RED)
            return False

    def update_npc_locations_by_schedule(self):
        current_time_period = self.get_current_time_period()
        if current_time_period == "Unknown": return
        moved_npcs_info = []
        for npc_name, npc_obj in self.all_character_objects.items():
            if npc_obj.is_player or not npc_obj.schedule: continue
            scheduled_location = npc_obj.schedule.get(current_time_period)
            if scheduled_location and scheduled_location != npc_obj.current_location:
                if scheduled_location in LOCATIONS_DATA and scheduled_location in npc_obj.accessible_locations:
                    if random.random() < NPC_MOVE_CHANCE:
                        old_location = npc_obj.current_location
                        npc_obj.current_location = scheduled_location
                        if old_location == self.current_location_name and scheduled_location != self.current_location_name:
                            moved_npcs_info.append(f"{npc_obj.name} has left.")
                        elif scheduled_location == self.current_location_name and old_location != self.current_location_name:
                             moved_npcs_info.append(f"{npc_obj.name} has arrived.")
        if moved_npcs_info:
            self._print_color("\n(As time passes...)", Colors.MAGENTA)
            for info in moved_npcs_info: self._print_color(info, Colors.MAGENTA)
            self._print_color("", Colors.RESET)
        self.update_npcs_in_current_location()

    def update_current_location_details(self, from_explicit_look_cmd=False):
        if not self.current_location_name:
            self._print_color("Error: Current location not set.", Colors.RED)
            if self.player_character and self.player_character.current_location: self.current_location_name = self.player_character.current_location
            else: self._print_color("Critical Error: Cannot determine current location.", Colors.RED); return
        location_data = LOCATIONS_DATA.get(self.current_location_name)
        if not location_data: self._print_color(f"Error: Unknown location: {self.current_location_name}. Data missing.", Colors.RED); return
        time_str = f"({self._get_current_game_time_period_str()})"
        self._print_color(f"\n--- {self.current_location_name} {time_str} ---", Colors.CYAN + Colors.BOLD)
        if from_explicit_look_cmd or not self.current_location_description_shown_this_visit:
            base_description = location_data.get("description", "A non-descript place.")
            time_effect_desc = location_data.get("time_effects", {}).get(self.get_current_time_period(), "")
            print(base_description + " " + time_effect_desc)
            self.current_location_description_shown_this_visit = True
        self.update_npcs_in_current_location()

    def update_npcs_in_current_location(self):
        self.npcs_in_current_location = []
        if not self.current_location_name: return
        for char_name, char_obj in self.all_character_objects.items():
            if not char_obj.is_player and char_obj.current_location == self.current_location_name:
                if char_obj not in self.npcs_in_current_location: self.npcs_in_current_location.append(char_obj)

    def get_relationship_text(self, score):
        if score > 5: return "very positive"
        if score > 2: return "positive"
        if score < -5: return "very negative"
        if score < -2: return "negative"
        return "neutral"

    def check_conversation_conclusion(self, text):
        for phrase_regex in CONCLUDING_PHRASES:
            if re.search(phrase_regex, text, re.IGNORECASE): return True
        return False

    def display_objectives(self):
        self._print_color("\n--- Your Objectives ---", Colors.CYAN + Colors.BOLD)
        if not self.player_character or not self.player_character.objectives:
            self._print_color("You have no specific objectives at the moment.", Colors.DIM); return
        active_objectives = [obj for obj in self.player_character.objectives if obj.get("active", False) and not obj.get("completed", False)]
        completed_objectives = [obj for obj in self.player_character.objectives if obj.get("completed", False)]
        if not active_objectives and not completed_objectives:
            self._print_color("You have no specific objectives at the moment.", Colors.DIM); return
        if active_objectives:
            self._print_color("\nOngoing:", Colors.YELLOW + Colors.BOLD)
            for obj in active_objectives:
                self._print_color(f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE)
                current_stage = self.player_character.get_current_stage_for_objective(obj.get('id'))
                if current_stage: self._print_color(f"  Current Stage: {current_stage.get('description', 'No stage description')}", Colors.CYAN)
        else: self._print_color("\nNo active objectives right now.", Colors.DIM)
        if completed_objectives:
            self._print_color("\nCompleted:", Colors.GREEN + Colors.BOLD)
            for obj in completed_objectives: self._print_color(f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE)

    def display_help(self, category=None):
        self._print_color("\n--- Available Actions ---", Colors.CYAN + Colors.BOLD); self._print_color("", Colors.RESET)
        self._print_color(
            f"Mode: {self._get_mode_label()} | Theme: {self.color_theme} | Verbosity: {self.verbosity_level}",
            Colors.DIM
        )
        action_groups = {
            "movement": [
                ("look / l / examine / observe / look around", "Examine surroundings, see people, items, and exits."),
                ("look at [thing/person/scenery]", "Examine something specific more closely."),
                ("move to [exit desc / location name]", "Change locations."),
                ("wait", "Pass some time (may trigger dreams if troubled).")
            ],
            "social": [
                ("talk to [name]", "Speak with someone here."),
                ("persuade [name] that/to [argument]", "Try to sway a character with a focused argument."),
                ("give [item name] to [target name]", "Offer an item to another character."),
                ("think / reflect", "Access your character's inner thoughts.")
            ],
            "items": [
                ("inventory / inv / i", "Check your possessions."),
                ("take [item name]", "Pick up an item from the location."),
                ("drop [item name]", "Leave an item from your inventory in the location."),
                ("use [item name]", "Attempt to use an item from your inventory (often on yourself)."),
                ("use [item name] on [target name/item]", "Use an item on something or someone specifically."),
                ("read [item name]", "Read a readable item like a letter or newspaper.")
            ],
            "meta": [
                ("objectives / obj", "See your current goals."),
                ("journal / notes", "Review your journal entries (rumors, news, etc.)."),
                ("save [slot]", "Save your current game progress (optional slot name)."),
                ("load [slot]", "Load a previously saved game (optional slot name)."),
                ("help / commands", "Show this help message."),
                ("status / char / profile / st", "Display your character's current status."),
                ("toggle lowai / lowaimode", "Toggle low AI data usage mode."),
                ("history / /history", "Show recent commands."),
                ("!!", "Repeat your previous command."),
                ("retry / rephrase", "Generate an alternate wording of the last AI text."),
                ("theme [default|high-contrast|mono]", "Switch color profile."),
                ("verbosity [brief|standard|rich]", "Adjust narrative text density."),
                ("turnheaders [on|off]", "Toggle turn boundary headers."),
                ("quit / exit / q", "Exit the game.")
            ]
        }

        normalized_category = category.strip().lower() if isinstance(category, str) and category.strip() else "all"
        if normalized_category == "all":
            actions = [item for group in action_groups.values() for item in group]
        elif normalized_category in action_groups:
            self._print_color(f"Category: {normalized_category}", Colors.DIM)
            actions = action_groups[normalized_category]
        else:
            available = ", ".join(action_groups.keys())
            self._print_color(
                f"Unknown help category '{category}'. Available: {available}. Showing all commands.",
                Colors.YELLOW
            )
            actions = [item for group in action_groups.values() for item in group]

        for cmd, desc in actions: self._print_color(f"{cmd:<65} {Colors.WHITE}- {desc}{Colors.RESET}", Colors.MAGENTA)
        self._print_color("", Colors.RESET)
        self._print_color("Tip: use 'help movement', 'help social', 'help items', or 'help meta'.", Colors.DIM)
        self._print_color("", Colors.RESET)

    def _display_load_recap(self):
        if not self.player_character:
            return

        self._print_color("\n--- Session Recap ---", Colors.CYAN + Colors.BOLD)
        self._print_color(f"Location: {self.current_location_name}", Colors.WHITE)
        self._print_color(f"Time: {self._get_current_game_time_period_str()}", Colors.WHITE)

        active_objective = None
        for objective in self.player_character.objectives:
            if objective.get("active") and not objective.get("completed"):
                active_objective = objective
                break
        if active_objective:
            stage = self.player_character.get_current_stage_for_objective(active_objective.get("id"))
            stage_text = stage.get("description") if stage else "unspecified stage"
            self._print_color(f"Objective: {active_objective.get('description', 'Unnamed objective')} ({stage_text})", Colors.WHITE)
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
                relationship_entries.append((abs(score), character_name, self.get_relationship_text(score)))
        relationship_entries.sort(reverse=True)
        if relationship_entries:
            self._print_color("Relationship highlights:", Colors.WHITE)
            for _, character_name, relationship_text in relationship_entries[:3]:
                self._print_color(f"- {character_name}: {relationship_text}", Colors.DIM)

    def parse_action(self, raw_input):
        action = raw_input.strip().lower();
        if not action: return None, None
        give_match = re.match(r"^(give|offer)\s+(.+?)\s+to\s+(.+)$", action)
        if give_match: return "use", (give_match.group(2).strip(), give_match.group(3).strip(), "give")
        read_match = re.match(r"^(read|peruse)\s+(.+)$", action)
        if read_match: return "use", (read_match.group(2).strip(), None, "read")
        use_on_match = re.match(r"^(use|apply)\s+(.+?)\s+on\s+(.+)$", action)
        if use_on_match: return "use", (use_on_match.group(2).strip(), use_on_match.group(3).strip(), "use_on")
        matched_command = None; best_match_length = 0; parsed_arg = None
        for base_cmd, synonyms in COMMAND_SYNONYMS.items():
            for cmd_to_check in [base_cmd] + synonyms:
                if action == cmd_to_check:
                    if len(cmd_to_check) > best_match_length: matched_command = base_cmd; best_match_length = len(cmd_to_check); parsed_arg = None
                elif action.startswith(cmd_to_check + " "):
                    if len(cmd_to_check) > best_match_length: matched_command = base_cmd; best_match_length = len(cmd_to_check); parsed_arg = action[len(cmd_to_check):].strip()
        if matched_command: return matched_command, parsed_arg
        parts = action.split(" ", 1)
        persuade_match = re.match(r"^(persuade|convince|argue with)\s+(.+?)\s+(?:that|to)\s+(.+)$", action)
        if persuade_match: return "persuade", (persuade_match.group(2).strip(), persuade_match.group(3).strip())
        return parts[0], parts[1] if len(parts) > 1 else None

    def _get_save_file_path(self, slot_name=None):
        if not slot_name:
            return SAVE_GAME_FILE
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", str(slot_name).strip().lower())
        if not sanitized:
            return None
        return f"savegame_{sanitized}.json"

    def save_game(self, slot_name=None, is_autosave=False):
        if not self.player_character: self._print_color("Cannot save: Game not fully initialized.", Colors.RED); return
        save_file = self._get_save_file_path(slot_name)
        if not save_file:
            self._print_color("Invalid save slot name. Use letters, numbers, hyphens, or underscores.", Colors.RED)
            return
        game_state_data = {
            "player_character_name": self.player_character.name, "current_location_name": self.current_location_name,
            "game_time": self.game_time, "current_day": self.current_day,
            "all_character_objects_state": {name: char.to_dict() for name, char in self.all_character_objects.items()},
            "dynamic_location_items": self.dynamic_location_items,
            "triggered_events": list(self.event_manager.triggered_events),
            "last_significant_event_summary": self.last_significant_event_summary,
            "player_notoriety_level": self.player_notoriety_level,
            "known_facts_about_crime": self.known_facts_about_crime,
            "key_events_occurred": self.key_events_occurred,
            "current_location_description_shown_this_visit": self.current_location_description_shown_this_visit,
            "chosen_gemini_model": self.gemini_api.chosen_model_name,
            "low_ai_data_mode": self.low_ai_data_mode,
            "player_action_count": self.player_action_count,
            "color_theme": self.color_theme,
            "verbosity_level": self.verbosity_level,
            "turn_headers_enabled": self.turn_headers_enabled,
            "command_history": self.command_history[-self.max_command_history:]
        }
        try:
            with open(save_file, 'w') as f: json.dump(game_state_data, f, indent=4)
            if is_autosave:
                self._print_color(f"Autosaved to {save_file}", Colors.DIM)
            else:
                self._print_color(f"Game saved to {save_file}", Colors.GREEN)
        except Exception as e: self._print_color(f"Error saving game: {e}", Colors.RED)

    def load_game(self, slot_name=None):
        save_file = self._get_save_file_path(slot_name)
        if not save_file:
            self._print_color("Invalid save slot name. Use letters, numbers, hyphens, or underscores.", Colors.RED)
            return False
        if not os.path.exists(save_file): self._print_color(f"No save file found at {save_file}.", Colors.YELLOW); return False
        try:
            with open(save_file, 'r') as f: game_state_data = json.load(f)
            self.game_time = game_state_data.get("game_time", 0); self.current_day = game_state_data.get("current_day", 1)
            self.current_location_name = game_state_data.get("current_location_name")
            self.dynamic_location_items = game_state_data.get("dynamic_location_items", {})
            self.event_manager.triggered_events = set(game_state_data.get("triggered_events", []))
            self.last_significant_event_summary = game_state_data.get("last_significant_event_summary")
            self.player_notoriety_level = game_state_data.get("player_notoriety_level", 0)
            self.known_facts_about_crime = game_state_data.get("known_facts_about_crime", ["An old pawnbroker and her sister were murdered recently."])
            self.key_events_occurred = game_state_data.get("key_events_occurred", ["Game loaded."])
            self.current_location_description_shown_this_visit = game_state_data.get("current_location_description_shown_this_visit", False)
            self.low_ai_data_mode = game_state_data.get("low_ai_data_mode", False)
            self.player_action_count = game_state_data.get("player_action_count", 0)
            loaded_theme = game_state_data.get("color_theme", DEFAULT_COLOR_THEME)
            applied_theme = apply_color_theme(loaded_theme)
            if not applied_theme:
                apply_color_theme(DEFAULT_COLOR_THEME)
                applied_theme = DEFAULT_COLOR_THEME
            self.color_theme = applied_theme
            self.verbosity_level = game_state_data.get("verbosity_level", DEFAULT_VERBOSITY_LEVEL)
            if self.verbosity_level not in VERBOSITY_LEVELS:
                self.verbosity_level = DEFAULT_VERBOSITY_LEVEL
            self.turn_headers_enabled = game_state_data.get("turn_headers_enabled", True)
            loaded_history = game_state_data.get("command_history", [])
            self.command_history = loaded_history[-self.max_command_history:] if isinstance(loaded_history, list) else []
            saved_model_name = game_state_data.get("chosen_gemini_model")
            if saved_model_name: self.gemini_api.chosen_model_name = saved_model_name; self._print_color(f"Loaded preferred Gemini model: {saved_model_name}", Colors.DIM)
            self.all_character_objects = {}
            saved_char_states = game_state_data.get("all_character_objects_state", {})
            for char_name, char_state_data in saved_char_states.items():
                static_data = CHARACTERS_DATA.get(char_name)
                if not static_data: self._print_color(f"Warning: Character '{char_name}' from save file not found in current CHARACTERS_DATA. Skipping.", Colors.YELLOW); continue
                self.all_character_objects[char_name] = Character.from_dict(char_state_data, static_data)
            player_name = game_state_data.get("player_character_name")
            if player_name and player_name in self.all_character_objects:
                self.player_character = self.all_character_objects[player_name]; self.player_character.is_player = True
            else: self._print_color(f"Error: Saved player character '{player_name}' not found or invalid. Load failed.", Colors.RED); self.player_character = None; return False
            if not self.current_location_name and self.player_character: self.current_location_name = self.player_character.current_location
            if not self.dynamic_location_items: self.initialize_dynamic_location_items()
            self.update_npcs_in_current_location(); self._print_color("Game loaded successfully.", Colors.GREEN)
            self._display_load_recap()
            self.update_current_location_details(from_explicit_look_cmd=False); return True
        except Exception as e: self._print_color(f"Error loading game: {e}", Colors.RED); self.player_character = None; return False

    def _initialize_game(self):
        # Call configure and get results
        config_results = self.gemini_api.configure(self._print_color, self._input_color)

        # The GeminiAPI.configure method already prints the Low AI Mode status upon selection.
        # No need for an additional print here unless desired for game-level confirmation.

        self._print_color("\n--- Crime and Punishment: A Text Adventure ---", Colors.CYAN + Colors.BOLD)
        self._validate_item_data()

        game_loaded_successfully = False
        # Non-interactive mode: Automatically start a new game if GEMINI_API_KEY is set
        if os.getenv("GEMINI_API_KEY"):
            self._print_color("Starting a new game...", Colors.MAGENTA)
            self.low_ai_data_mode = config_results.get("low_ai_preference", False)
            self.load_all_characters()
            if not self.select_player_character(non_interactive=True):
                self._print_color("Critical Error: Could not initialize player character. Exiting.", Colors.RED)
                return False
        else:
            self._print_color("Type 'load' to load a saved game, or press Enter to start a new game.", Colors.MAGENTA)
            initial_action = self._input_color(f"{self._prompt_arrow()}", Colors.WHITE).strip().lower()
            if initial_action == "load":
                if self.load_game():
                    game_loaded_successfully = True
                else:
                    self._print_color("Failed to load game. Starting a new game instead.", Colors.YELLOW)

            if not game_loaded_successfully:
                self.low_ai_data_mode = config_results.get("low_ai_preference", False)
                self.load_all_characters()
                if not self.select_player_character():
                    self._print_color("Critical Error: Could not initialize player character. Exiting.", Colors.RED)
                    return False
        if not self.player_character or not self.current_location_name: self._print_color("Game initialization failed critically. Exiting.", Colors.RED); return False
        if not game_loaded_successfully:
            self.update_current_location_details(from_explicit_look_cmd=False); self.display_atmospheric_details()
        self._print_color("\n--- Game Start ---", Colors.CYAN + Colors.BOLD)
        if not game_loaded_successfully: self.display_help()
        return True

    def _handle_ambient_rumors(self):
        if self.current_location_name in ["Haymarket Square", "Tavern", "Squalid St. Petersburg Street"] and \
           random.random() < AMBIENT_RUMOR_CHANCE_PUBLIC_PLACE:
            source_npc = random.choice(self.npcs_in_current_location) if self.npcs_in_current_location \
                         else Character("A Passerby", "A typical St. Petersburg citizen.", "", self.current_location_name, [])
            relationship_score_for_rumor = 0
            if source_npc.name != "A Passerby" and hasattr(source_npc, 'relationship_with_player'):
                relationship_score_for_rumor = source_npc.relationship_with_player

            rumor_text = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                rumor_text = self.gemini_api.get_rumor_or_gossip(
                    source_npc, self.current_location_name, self.get_current_time_period(),
                    self._get_known_facts_summary(), self.player_notoriety_level,
                    self.get_relationship_text(relationship_score_for_rumor), self._get_objectives_summary(source_npc))

            if rumor_text is None or (isinstance(rumor_text, str) and rumor_text.startswith("(OOC:")) or self.low_ai_data_mode:
                if STATIC_RUMORS:
                    rumor_text = random.choice(STATIC_RUMORS)
                else:
                    rumor_text = "The air buzzes with indistinct chatter." # Ultimate fallback
                rumor_text = self._apply_verbosity(rumor_text)
                # Print static rumor with a different color or note if desired
                self._print_color(f"\n{Colors.DIM}(You overhear some chatter nearby: \"{rumor_text}\"){Colors.RESET}", Colors.DIM); self._print_color("", Colors.RESET)
                if self.player_character and rumor_text: # Check rumor_text is not None
                     self.player_character.add_journal_entry("Overheard Rumor (Static)", rumor_text, self._get_current_game_time_period_str())
            elif rumor_text: # AI success and not OOC
                rumor_text = self._apply_verbosity(rumor_text)
                self._print_color(f"\n{Colors.DIM}(You overhear some chatter nearby: \"{rumor_text}\"){Colors.RESET}", Colors.DIM); self._print_color("", Colors.RESET)
                if self.player_character:
                     self.player_character.add_journal_entry("Overheard Rumor (AI)", rumor_text, self._get_current_game_time_period_str())
                self._remember_ai_output(rumor_text, "ambient_rumor")

            # Common logic for Raskolnikov if any rumor was processed (AI or static)
            if rumor_text and self.player_character and self.player_character.name == "Rodion Raskolnikov" and \
               any(kw in rumor_text.lower() for kw in ["student", "axe", "pawnbroker", "murder", "police"]):
                self.player_character.apparent_state = "paranoid"; self.player_notoriety_level = min(self.player_notoriety_level + 0.2, 3)

    def _get_player_input(self):
        player_state_info = f"{self.player_character.apparent_state}" if self.player_character else "Unknown state"
        prompt_hint_objects = []; hint_types_added = set()
        if hasattr(self, 'numbered_actions_context') and self.numbered_actions_context:
            if 'talk' not in hint_types_added and len(prompt_hint_objects) < 2:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'talk':
                        current_action_type = 'talk'; current_target = action_info['target']; display_string = f"Talk to {current_target}"
                        is_duplicate = any(ex_h['action_type'] == current_action_type and (ex_h['target'].startswith(current_target) or current_target.startswith(ex_h['target'])) for ex_h in prompt_hint_objects)
                        if not is_duplicate: prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string}); hint_types_added.add('talk'); break
            if len(prompt_hint_objects) < 2 and 'item_take' not in hint_types_added:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'take' and DEFAULT_ITEMS.get(action_info['target'], {}).get('is_notable', False):
                        current_action_type = 'item_take'; current_target = action_info['target']; display_string = f"Take {current_target}"
                        is_duplicate = any(ex_h['action_type'] == current_action_type and (ex_h['target'].startswith(current_target) or current_target.startswith(ex_h['target'])) for ex_h in prompt_hint_objects)
                        if not is_duplicate: prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string}); hint_types_added.add('item_take'); break
            if len(prompt_hint_objects) < 2 and 'item_examine' not in hint_types_added:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'look_at_item' and DEFAULT_ITEMS.get(action_info['target'], {}).get('is_notable', False):
                        current_action_type = 'item_examine'; current_target = action_info['target']; display_string = f"Examine {current_target}"
                        is_duplicate = any(ex_h['action_type'] == current_action_type and (ex_h['target'].startswith(current_target) or current_target.startswith(ex_h['target'])) for ex_h in prompt_hint_objects)
                        if not is_duplicate: prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string}); hint_types_added.add('item_examine'); break
            if len(prompt_hint_objects) < 2 and 'item_take' not in hint_types_added :
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'take':
                        current_action_type = 'item_take'; current_target = action_info['target']; display_string = f"Take {current_target}"
                        is_duplicate = any(ex_h['action_type'] == current_action_type and (ex_h['target'].startswith(current_target) or current_target.startswith(ex_h['target'])) for ex_h in prompt_hint_objects)
                        if not is_duplicate: prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string}); hint_types_added.add('item_take'); break
            if len(prompt_hint_objects) < 2 and 'item_examine' not in hint_types_added:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'look_at_item':
                        current_action_type = 'item_examine'; current_target = action_info['target']; display_string = f"Examine {current_target}"
                        is_duplicate = any(ex_h['action_type'] == current_action_type and (ex_h['target'].startswith(current_target) or current_target.startswith(ex_h['target'])) for ex_h in prompt_hint_objects)
                        if not is_duplicate: prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string}); hint_types_added.add('item_examine'); break
            if 'move' not in hint_types_added and len(prompt_hint_objects) < 2:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'move':
                        current_action_type = 'move'; current_target = action_info['target']; display_string = f"Go to {current_target}"
                        is_duplicate = any(ex_h['action_type'] == current_action_type and (ex_h['target'].startswith(current_target) or current_target.startswith(ex_h['target'])) for ex_h in prompt_hint_objects)
                        if not is_duplicate: prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string}); hint_types_added.add('move'); break
        active_hint_display_strings = [h['display_string'] for h in prompt_hint_objects[:2]]
        hint_string = f" (Hint: {Colors.DIM}{' | '.join(active_hint_display_strings)}{Colors.RESET})" if active_hint_display_strings else \
                      (f" (Hint: {Colors.DIM}type 'look' or 'help'{Colors.RESET})" if not (hasattr(self, 'numbered_actions_context') and self.numbered_actions_context) else "")
        time_info = self._get_current_game_time_period_str()
        mode_label = self._get_mode_label()
        prompt_text = (
            f"\n[{Colors.DIM}{time_info}{Colors.RESET} | {Colors.CYAN}{self.current_location_name}{Colors.RESET} "
            f"| {mode_label} | {self.verbosity_level} | {player_state_info}]"
            f"{hint_string} What do you do? {self._prompt_arrow()}"
        )
        raw_action_input = self._input_color(prompt_text, Colors.WHITE)
        fast_input = raw_action_input.strip().lower()
        if fast_input == "!!":
            if not self.command_history:
                self._print_color("No previous command to repeat yet.", Colors.YELLOW)
                return None, None
            repeated_command = self.command_history[-1]
            self._print_color(f"Repeating: {repeated_command}", Colors.DIM)
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
            if 1 <= action_number <= len(self.numbered_actions_context):
                action_info = self.numbered_actions_context[action_number - 1]
                action_type = action_info['type']; target = action_info['target']
                if action_type == 'move': return 'move to', target
                elif action_type == 'talk': return 'talk to', target
                elif action_type == 'take': return 'take', target
                elif action_type == 'look_at_item': return 'look', target
                elif action_type == 'look_at_npc': return 'look', target
                elif action_info['type'] == 'select_item': return ('select_item', action_info['target'])
            else:
                parsed_command, parsed_argument = self.parse_action(raw_action_input)
                if self._is_known_command(parsed_command):
                    return parsed_command, parsed_argument
                if self.gemini_api.model:
                    return self._interpret_with_nlp(raw_action_input)
                self._handle_unknown_intent()
                return None, None
        except ValueError:
            parsed_command, parsed_argument = self.parse_action(raw_action_input)
            if self._is_known_command(parsed_command):
                return parsed_command, parsed_argument
            if self.gemini_api.model:
                return self._interpret_with_nlp(raw_action_input)
            self._handle_unknown_intent()
            return None, None
        return None, None

    def _handle_theme_command(self, argument):
        if not argument:
            available = ", ".join(COLOR_THEME_MAP.keys())
            self._print_color(f"Current theme: {self.color_theme}. Available: {available}.", Colors.CYAN)
            return
        requested_theme = str(argument).strip().lower()
        applied_theme = apply_color_theme(requested_theme)
        if not applied_theme:
            self._print_color(
                f"Unknown theme '{requested_theme}'. Use: {', '.join(COLOR_THEME_MAP.keys())}.",
                Colors.YELLOW
            )
            return
        self.color_theme = applied_theme
        self._print_color(f"Theme set to {self.color_theme}.", Colors.GREEN)

    def _handle_verbosity_command(self, argument):
        if not argument:
            self._print_color(
                f"Current verbosity: {self.verbosity_level}. Options: {', '.join(VERBOSITY_LEVELS)}.",
                Colors.CYAN
            )
            return
        requested_level = str(argument).strip().lower()
        if requested_level not in VERBOSITY_LEVELS:
            self._print_color(
                f"Unknown verbosity '{requested_level}'. Use: {', '.join(VERBOSITY_LEVELS)}.",
                Colors.YELLOW
            )
            return
        self.verbosity_level = requested_level
        self._print_color(f"Verbosity set to {self.verbosity_level}.", Colors.GREEN)

    def _handle_turnheaders_command(self, argument):
        if not argument:
            status_text = "on" if self.turn_headers_enabled else "off"
            self._print_color(f"Turn headers are currently {status_text}. Use 'turnheaders on' or 'turnheaders off'.", Colors.CYAN)
            return
        normalized = str(argument).strip().lower()
        if normalized in ["on", "true", "yes", "1"]:
            self.turn_headers_enabled = True
            self._print_color("Turn headers enabled.", Colors.GREEN)
            return
        if normalized in ["off", "false", "no", "0"]:
            self.turn_headers_enabled = False
            self._print_color("Turn headers disabled.", Colors.GREEN)
            return
        self._print_color("Invalid value. Use 'turnheaders on' or 'turnheaders off'.", Colors.YELLOW)

    def _handle_retry_or_rephrase(self, mode):
        if not self.last_ai_generated_text:
            self._print_color("No recent AI text available to rework yet.", Colors.YELLOW)
            return False
        if not self.gemini_api.model or self.low_ai_data_mode:
            self._print_color("Retry/rephrase requires active AI mode.", Colors.YELLOW)
            return False

        if mode == "retry":
            prompt = (
                "Rewrite this game narration with a different angle and details while preserving meaning:\n"
                f"{self.last_ai_generated_text}"
            )
        else:
            prompt = (
                "Rephrase this game narration for clarity in 1-2 concise sentences, preserving meaning:\n"
                f"{self.last_ai_generated_text}"
            )

        regenerated_text = self.gemini_api._generate_content_with_fallback(prompt, f"{mode} last AI output")
        if regenerated_text is None or (isinstance(regenerated_text, str) and regenerated_text.startswith("(OOC:")):
            self._print_color("Could not generate an alternate version right now.", Colors.YELLOW)
            return False

        final_text = self._apply_verbosity(regenerated_text)
        self._print_color(f"{mode.title()}: \"{final_text}\"", Colors.CYAN)
        self._remember_ai_output(final_text, f"{mode}_command")
        return True

    def _process_command(self, command, argument):
        show_full_look_details = False
        if command == "look" or command == "move to":
            show_full_look_details = True
        action_taken_this_turn = True; time_to_advance = TIME_UNITS_PER_PLAYER_ACTION; show_atmospherics_this_turn = True
        if command == "quit": self._print_color("Exiting game. Goodbye.", Colors.MAGENTA); return False, False, 0, True
        elif command == "select_item":
            item_name_selected = argument
            secondary_action_input = self._input_color(f"What to do with {Colors.GREEN}{item_name_selected}{Colors.WHITE}? (e.g., look at, take, use, read, give to...) {self._prompt_arrow()}", Colors.WHITE).strip().lower()

            if secondary_action_input == "look at":
                self._handle_look_command(item_name_selected, show_full_look_details) # _handle_look_command doesn't return action_taken flags
                return True, True, TIME_UNITS_PER_PLAYER_ACTION, False
            elif secondary_action_input == "take":
                action_taken, show_atmospherics = self._handle_take_command(item_name_selected)
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, show_atmospherics, time_units, False
            elif secondary_action_input == "read":
                action_taken = self.handle_use_item(item_name_selected, None, "read")
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, True, time_units, False
            elif secondary_action_input == "use":
                action_taken = self.handle_use_item(item_name_selected, None, "use_self_implicit")
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, True, time_units, False
            elif secondary_action_input.startswith("give to "):
                target_npc_name = secondary_action_input.replace("give to ", "").strip()
                if not target_npc_name:
                    self._print_color("Who do you want to give it to?", Colors.RED)
                    return False, False, 0, False
                action_taken = self.handle_use_item(item_name_selected, target_npc_name, "give")
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, True, time_units, False
            elif secondary_action_input.startswith("use on "):
                target_for_use = secondary_action_input.replace("use on ", "").strip()
                if not target_for_use:
                    self._print_color("What do you want to use it on?", Colors.RED)
                    return False, False, 0, False
                action_taken = self.handle_use_item(item_name_selected, target_for_use, "use_on")
                time_units = TIME_UNITS_PER_PLAYER_ACTION if action_taken else 0
                return action_taken, True, time_units, False
            else:
                self._print_color(f"Invalid action '{secondary_action_input}' for {item_name_selected}.", Colors.RED)
                return False, False, 0, False
        elif command == "save": self.save_game(argument); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "load":
            if self.load_game(argument): show_atmospherics_this_turn = True
            else: show_atmospherics_this_turn = False
            action_taken_this_turn = False; return action_taken_this_turn, show_atmospherics_this_turn, 0, "load_triggered"
        elif command == "help": self.display_help(argument); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "journal":
            if self.player_character: self._print_color(self.player_character.get_journal_summary(), Colors.CYAN)
            action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "look": self._handle_look_command(argument, show_full_look_details)
        elif command == "inventory": self._handle_inventory_command(); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "take": action_taken_this_turn, show_atmospherics_this_turn = self._handle_take_command(argument)
        elif command == "drop": action_taken_this_turn, show_atmospherics_this_turn = self._handle_drop_command(argument)
        elif command == "use": action_taken_this_turn = self._handle_use_command(argument); show_atmospherics_this_turn = True
        elif command == "objectives": self.display_objectives(); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "think": self._handle_think_command(); show_atmospherics_this_turn = True
        elif command == "wait": time_to_advance = self._handle_wait_command(); show_atmospherics_this_turn = True
        elif command == "talk to": action_taken_this_turn, show_atmospherics_this_turn = self._handle_talk_to_command(argument)
        elif command == "move to": action_taken_this_turn, show_atmospherics_this_turn = self._handle_move_to_command(argument)
        elif command == "persuade": action_taken_this_turn, show_atmospherics_this_turn = self._handle_persuade_command(argument)
        elif command == "status": self._handle_status_command(); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "toggle_lowai":
            self.low_ai_data_mode = not self.low_ai_data_mode
            self._print_color(f"Low AI Data Mode is now {'ON' if self.low_ai_data_mode else 'OFF'}.", Colors.MAGENTA)
            return False, False, 0, False # No action, no time, no atmospherics
        elif command == "history":
            self._display_command_history(); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "theme":
            self._handle_theme_command(argument); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "verbosity":
            self._handle_verbosity_command(argument); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "turnheaders":
            self._handle_turnheaders_command(argument); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "retry":
            self._handle_retry_or_rephrase("retry"); action_taken_this_turn = False; show_atmospherics_this_turn = False
        elif command == "rephrase":
            self._handle_retry_or_rephrase("rephrase"); action_taken_this_turn = False; show_atmospherics_this_turn = False
        else:
            suggestions = self._get_command_suggestions(command)
            suggestion_text = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
            self._print_color(f"Unknown command: '{command}'. Type 'help' for a list of actions.{suggestion_text}", Colors.RED)
            self._print_color(f"Try: {', '.join(self._get_contextual_command_examples())}", Colors.DIM)
            action_taken_this_turn = False; show_atmospherics_this_turn = False
        return action_taken_this_turn, show_atmospherics_this_turn, time_to_advance, False

    def _update_world_state_after_action(self, command, action_taken_this_turn, time_to_advance):
        if action_taken_this_turn:
            self.player_action_count += 1
            if command != "talk to": self.advance_time(time_to_advance)
            self.actions_since_last_autosave += 1
            if self.actions_since_last_autosave >= self.autosave_interval_actions and command not in ["save", "load", "quit"]:
                self.save_game("autosave", is_autosave=True)
                self.actions_since_last_autosave = 0
            event_triggered = self.event_manager.check_and_trigger_events()
            if event_triggered and self.last_significant_event_summary and \
               self.last_significant_event_summary not in self.key_events_occurred[-3:]:
                self.key_events_occurred.append(self.last_significant_event_summary)
                if len(self.key_events_occurred) > 10: self.key_events_occurred.pop(0)
            if self.gemini_api.model and command != "talk to" and \
               self.time_since_last_npc_interaction >= TIME_UNITS_FOR_NPC_INTERACTION_CHANCE:
                if len(self.npcs_in_current_location) >= 2 and random.random() < NPC_INTERACTION_CHANCE:
                    if self.event_manager.attempt_npc_npc_interaction(): self.last_significant_event_summary = "overheard an exchange between NPCs."
                self.time_since_last_npc_interaction = 0

    def _display_turn_feedback(self, show_atmospherics_this_turn, command):
        if show_atmospherics_this_turn: self.display_atmospheric_details()
        elif command == "load": self.last_significant_event_summary = None

    def _check_game_ending_conditions(self):
        if self.player_character and self.player_character.name == "Rodion Raskolnikov":
            obj_grapple = self.player_character.get_objective_by_id("grapple_with_crime")
            if obj_grapple and obj_grapple.get("completed", False):
                current_stage = self.player_character.get_current_stage_for_objective("grapple_with_crime")
                if current_stage and current_stage.get("is_ending_stage"):
                    self._print_color(f"\n--- The story of {self.player_character.name} has reached a conclusion ({current_stage.get('description', 'an end')}) ---", Colors.CYAN + Colors.BOLD)
                    return True
        return False

    def run(self):
        if not self._initialize_game(): return
        while True:
            if not LOCATIONS_DATA.get(self.current_location_name):
                 self._print_color(f"Critical Error: Current location '{self.current_location_name}' data not found. Exiting.", Colors.RED); break
            self._print_turn_header()
            self._display_tutorial_hint()
            self._handle_ambient_rumors(); command, argument = self._get_player_input()
            if command is None and argument is None: continue
            self._record_command_history(command, argument)
            action_taken, show_atmospherics, time_units, special_flag = self._process_command(command, argument)
            if special_flag == "load_triggered":
                self.last_turn_result_icon = "LOAD"
                continue
            if special_flag:
                self.last_turn_result_icon = "QUIT"
                break
            self._update_world_state_after_action(command, action_taken, time_units)
            self._display_turn_feedback(show_atmospherics, command)
            if action_taken:
                self.last_turn_result_icon = "OK"
            elif command in ["help", "status", "history", "theme", "verbosity", "turnheaders", "retry", "rephrase", "save", "load", "toggle_lowai"]:
                self.last_turn_result_icon = "INFO"
            else:
                self.last_turn_result_icon = "NOOP"
            if self._check_game_ending_conditions(): break

    def _handle_look_at_location_item(self, target_to_look_at):
        if not self.player_character:
            self._print_color("Cannot inspect location items: Player character not available.", Colors.RED)
            return True
        player_character = self.player_character
        item_info, ambiguous = self._get_matching_location_item(target_to_look_at)
        if ambiguous:
            return True
        if item_info:
            item_default = DEFAULT_ITEMS.get(item_info["name"])
            if item_default:
                observation_context = (
                    f"Player ({player_character.name}) succeeded an Observation skill check examining the "
                    f"{item_info['name']} in {self.current_location_name}. What subtle detail, past use, hidden "
                    f"inscription, or unusual characteristic do they notice that isn't immediately obvious?"
                )
                self._inspect_item(
                    item_info["name"],
                    item_default,
                    "examine closely in environment",
                    observation_context,
                    allow_npc_memory=True
                )
                return True
        return False

    def _handle_look_at_inventory_item(self, target_to_look_at):
        if self.player_character:
            inv_item_info, ambiguous = self._get_matching_inventory_item(target_to_look_at)
            if ambiguous:
                return True
            if inv_item_info:
                item_default = DEFAULT_ITEMS.get(inv_item_info["name"])
                if item_default:
                    observation_context = (
                        f"Player ({self.player_character.name}) succeeded an Observation skill check examining their "
                        f"{inv_item_info['name']}. What subtle detail, past use, hidden inscription, or unusual "
                        f"characteristic do they notice that isn't immediately obvious?"
                    )
                    self._inspect_item(
                        inv_item_info["name"],
                        item_default,
                        "examine closely from inventory",
                        observation_context,
                        allow_npc_memory=True
                    )
                    return True
        return False

    def _handle_look_at_npc(self, target_to_look_at):
        if not self.player_character:
            self._print_color("Cannot inspect people: Player character not available.", Colors.RED)
            return True
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        npc, ambiguous = self._get_matching_npc(target_to_look_at)
        if ambiguous:
            return True
        if npc:
            self._print_color(f"You look closely at {Colors.YELLOW}{npc.name}{Colors.RESET} (appears {npc.apparent_state}):", Colors.WHITE)
            base_desc_for_skill_check = npc.persona[:100] if npc.persona else f"{npc.name} is present." # Initialize base_desc
            observation = None

            if not self.low_ai_data_mode and self.gemini_api.model:
                observation_prompt = f"observing {npc.name} in {current_location_name}. They appear to be '{npc.apparent_state}'. You recall: {npc.get_player_memory_summary(self.game_time)}"
                observation = self.gemini_api.get_player_reflection(player_character, current_location_name, self.get_current_time_period(), observation_prompt, player_character.get_inventory_description(), self._get_objectives_summary(player_character))

            if observation is not None and not (isinstance(observation, str) and observation.startswith("(OOC:")) and not self.low_ai_data_mode:
                final_observation = self._apply_verbosity(observation)
                self._print_color(f"\"{final_observation}\"", Colors.GREEN)
                base_desc_for_skill_check = final_observation
                self._remember_ai_output(final_observation, "look_npc")
            else:
                if self.low_ai_data_mode or observation is None or (isinstance(observation, str) and observation.startswith("(OOC:")) :
                    if STATIC_PLAYER_REFLECTIONS:
                        observation = f"{npc.name} is here. {random.choice(STATIC_PLAYER_REFLECTIONS)}"
                    else:
                        observation = f"You observe {npc.name}. They seem to be going about their business."
                    self._print_color(f"\"{self._apply_verbosity(observation)}\"", Colors.CYAN)
                else:
                    self._print_color(f"({base_desc_for_skill_check})", Colors.DIM)

            if player_character.check_skill("Observation", 1):
                self._print_color("(Your keen observation notices something more...)", Colors.CYAN + Colors.DIM)
                observation_context = (
                    f"Player ({player_character.name}) succeeded an Observation skill check while looking at "
                    f"{npc.name} (appears {npc.apparent_state}). What subtle, non-obvious detail does "
                    f"{player_character.name} notice about {npc.name}'s demeanor, clothing, a hidden object, "
                    f"or a subtle emotional cue? This should be something beyond the obvious, a deeper insight."
                )
                detailed_observation = None
                if not self.low_ai_data_mode and self.gemini_api.model:
                    detailed_observation = self.gemini_api.get_enhanced_observation(
                        player_character, target_name=npc.name, target_category="person",
                        base_description=base_desc_for_skill_check, skill_check_context=observation_context
                    )

                if detailed_observation is None or (isinstance(detailed_observation, str) and detailed_observation.startswith("(OOC:")) or self.low_ai_data_mode:
                    if STATIC_ENHANCED_OBSERVATIONS:
                        detailed_observation = random.choice(STATIC_ENHANCED_OBSERVATIONS)
                    else:
                        detailed_observation = "You notice some subtle cues, but their full meaning eludes you."
                    if detailed_observation:
                        self._print_color(f"Insight: \"{self._apply_verbosity(detailed_observation)}\"", Colors.CYAN)
                elif detailed_observation:
                    final_detail = self._apply_verbosity(detailed_observation)
                    self._print_color(f"Insight: \"{final_detail}\"", Colors.GREEN)
                    self._remember_ai_output(final_detail, "look_npc_detail")
            return True
        return False

    def _handle_look_at_scenery(self, target_to_look_at):
        if not self.player_character:
            self._print_color("Cannot inspect scenery: Player character not available.", Colors.RED)
            return True
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        loc_data = LOCATIONS_DATA.get(self.current_location_name, {}); loc_desc_lower = loc_data.get("description", "").lower()
        is_scenery = any(keyword in target_to_look_at for keyword in GENERIC_SCENERY_KEYWORDS) or target_to_look_at in loc_desc_lower
        if is_scenery:
            self._print_color(f"You focus on the {target_to_look_at}...", Colors.WHITE)
            base_desc_for_skill_check = f"The general scenery of {current_location_name}, focusing on {target_to_look_at}." # Initial base
            observation = None

            if not self.low_ai_data_mode and self.gemini_api.model:
                observation = self.gemini_api.get_scenery_observation(player_character, target_to_look_at, current_location_name, self.get_current_time_period(), self._get_objectives_summary(player_character))

            if observation is not None and not (isinstance(observation, str) and observation.startswith("(OOC:")) and not self.low_ai_data_mode:
                # AI success
                final_observation = self._apply_verbosity(observation)
                self._print_color(f"\"{final_observation}\"", Colors.CYAN)
                base_desc_for_skill_check = final_observation # Update for skill check
                self._remember_ai_output(final_observation, "look_scenery")
            else:
                # Fallback or AI failed/OOC or low_ai_mode
                if self.low_ai_data_mode or observation is None or (isinstance(observation, str) and observation.startswith("(OOC:")) :
                    observation = generate_static_scenery_observation(target_to_look_at)
                    # base_desc_for_skill_check remains the initial general one
                    self._print_color(f"\"{self._apply_verbosity(observation)}\"", Colors.DIM) # Static in DIM
                else: # Should not be reached
                     self._print_color(f"The {target_to_look_at} is just as it seems.", Colors.DIM)

            if player_character.check_skill("Observation", 0):
                self._print_color("(You scan the area more intently...)", Colors.CYAN + Colors.DIM)
                observation_context = f"Player ({player_character.name}) passed an Observation check while looking at '{target_to_look_at}' in {current_location_name}. What specific, easily missed detail about '{target_to_look_at}' or its immediate surroundings catches their eye, perhaps hinting at a past event, a hidden element, or the general atmosphere in a more profound way?"
                detailed_observation = None
                if not self.low_ai_data_mode and self.gemini_api.model:
                    detailed_observation = self.gemini_api.get_enhanced_observation(player_character, target_name=target_to_look_at, target_category="scenery", base_description=base_desc_for_skill_check, skill_check_context=observation_context)

                if detailed_observation is None or (isinstance(detailed_observation, str) and detailed_observation.startswith("(OOC:")) or self.low_ai_data_mode:
                    if STATIC_ENHANCED_OBSERVATIONS:
                        detailed_observation = random.choice(STATIC_ENHANCED_OBSERVATIONS)
                    else:
                        detailed_observation = "The scene offers no further secrets to your gaze." # Ultimate fallback
                    if detailed_observation: # Check if not None
                        self._print_color(f"You also notice: \"{self._apply_verbosity(detailed_observation)}\"", Colors.CYAN) # Static in Cyan
                elif detailed_observation: # AI success
                    final_detail = self._apply_verbosity(detailed_observation)
                    self._print_color(f"You also notice: \"{final_detail}\"", Colors.GREEN)
                    self._remember_ai_output(final_detail, "look_scenery_detail")
                # If still None, nothing printed.
            return True
        return False

    def _handle_look_command(self, argument, show_full_look_details=False):
        self.numbered_actions_context.clear(); action_number = 1
        current_location_data = LOCATIONS_DATA.get(self.current_location_name)
        is_general_look = (argument is None or argument.lower() in ["around", ""])
        self.update_current_location_details(from_explicit_look_cmd=is_general_look)

        if argument and not is_general_look:
            target_to_look_at = argument.lower()
            if self._handle_look_at_location_item(target_to_look_at):
                self._print_color(self._separator_line(), Colors.DIM)
            elif self._handle_look_at_inventory_item(target_to_look_at):
                self._print_color(self._separator_line(), Colors.DIM)
            elif self._handle_look_at_npc(target_to_look_at):
                self._print_color(self._separator_line(), Colors.DIM)
            elif self._handle_look_at_scenery(target_to_look_at):
                self._print_color(self._separator_line(), Colors.DIM)
            else:
                self._print_color(f"You don't see '{argument}' here to look at specifically.", Colors.RED)
                self._print_color(self._separator_line(), Colors.DIM)

        if show_full_look_details:
            self._print_color("", Colors.RESET)
            self._print_color("--- People Here ---", Colors.YELLOW + Colors.BOLD); npcs_present_for_hint = False
            if self.npcs_in_current_location:
                for npc in self.npcs_in_current_location:
                    look_at_npc_display = f"Look at {npc.name}"; self.numbered_actions_context.append({'type': 'look_at_npc', 'target': npc.name, 'display': look_at_npc_display})
                    self._print_color(f"{action_number}. {look_at_npc_display}", Colors.YELLOW, end=""); print(f" (Appears: {npc.apparent_state}, Relationship: {self.get_relationship_text(npc.relationship_with_player)})"); action_number += 1; npcs_present_for_hint = True
                    talk_to_npc_display = f"Talk to {npc.name}"; self.numbered_actions_context.append({'type': 'talk', 'target': npc.name, 'display': talk_to_npc_display})
                    self._print_color(f"{action_number}. {talk_to_npc_display}", Colors.YELLOW); action_number += 1
            else: self._print_color("You see no one else of note here.", Colors.DIM)
            self._print_color("", Colors.RESET); self._print_color("--- Items Here ---", Colors.YELLOW + Colors.BOLD)
            current_loc_items = self.dynamic_location_items.get(self.current_location_name, []); items_present_for_hint = False
            if current_loc_items:
                for item_info in current_loc_items:
                    item_name = item_info["name"]; item_qty = item_info.get("quantity", 1)
                    item_default_info = DEFAULT_ITEMS.get(item_name, {})

                    full_description = item_default_info.get('description', 'An undescribed item.')

                    qty_str = ""
                    if (item_default_info.get("stackable") or item_default_info.get("value") is not None) and item_qty > 1:
                        qty_str = f" (x{item_qty})"

                    item_display_line = f"{item_name}{qty_str} - {full_description}"
                    self._print_color(f"{action_number}. {item_display_line}", Colors.GREEN)

                    self.numbered_actions_context.append({
                        'type': 'select_item', # Changed from 'item_reference'
                        'target': item_name,
                        'display': item_name
                    })
                    action_number += 1
                    items_present_for_hint = True
            else:
                self._print_color("No loose items of interest here.", Colors.DIM)
            self._print_color("", Colors.RESET); self._print_color("--- Exits ---", Colors.BLUE + Colors.BOLD); has_accessible_exits = False
            if current_location_data and current_location_data.get("exits"):
                for exit_target_loc, exit_desc in current_location_data["exits"].items():
                    display_text = f"{exit_desc} (to {exit_target_loc})"; self.numbered_actions_context.append({'type': 'move', 'target': exit_target_loc, 'description': exit_desc, 'display': display_text})
                    self._print_color(f"{action_number}. {display_text}", Colors.BLUE); action_number += 1; has_accessible_exits = True
            if not has_accessible_exits: self._print_color("There are no obvious exits from here.", Colors.DIM)
            self._print_color("", Colors.RESET)
            if items_present_for_hint: self._print_color("(Hint: You can 'take [item name]', 'look at [item name]', or use a number to interact with items.)", Colors.DIM)
            if npcs_present_for_hint: self._print_color("(Hint: You can 'talk to [npc name]', 'look at [npc name]', or use a number to interact with people.)", Colors.DIM)

    def _handle_status_command(self):
        if not self.player_character: self._print_color("No player character loaded.", Colors.RED); return
        self._print_color("\n--- Your Status ---", Colors.CYAN + Colors.BOLD)
        self._print_color(f"Name: {Colors.GREEN}{self.player_character.name}{Colors.RESET}", Colors.WHITE)
        self._print_color(f"Apparent State: {Colors.YELLOW}{self.player_character.apparent_state}{Colors.RESET}", Colors.WHITE)
        self._print_color(f"Current Location: {Colors.CYAN}{self.current_location_name}{Colors.RESET}", Colors.WHITE)
        notoriety_desc = "Unknown"
        if self.player_notoriety_level == 0: notoriety_desc = "Unknown"
        elif self.player_notoriety_level < 0.5: notoriety_desc = "Barely Noticed"
        elif self.player_notoriety_level < 1.5: notoriety_desc = "Slightly Known"
        elif self.player_notoriety_level < 2.5: notoriety_desc = "Talked About"
        else: notoriety_desc = "Infamous"
        self._print_color(f"Notoriety: {Colors.MAGENTA}{notoriety_desc} (Level {self.player_notoriety_level:.1f}){Colors.RESET}", Colors.WHITE)
        ai_mode = "Low AI / Fallback Friendly" if self.low_ai_data_mode else "AI Dynamic"
        self._print_color(f"Narrative Mode: {Colors.CYAN}{ai_mode}{Colors.RESET}", Colors.WHITE)
        self._print_color(f"Theme: {self.color_theme}", Colors.WHITE)
        self._print_color(f"Verbosity: {self.verbosity_level}", Colors.WHITE)
        self._print_color(f"Turn Headers: {'on' if self.turn_headers_enabled else 'off'}", Colors.WHITE)
        if self.player_action_count < self.tutorial_turn_limit:
            self._print_color(f"Tutorial Progress: {self.player_action_count}/{self.tutorial_turn_limit} actions", Colors.DIM)
        self._print_color("\n--- Skills ---", Colors.CYAN + Colors.BOLD)
        if self.player_character.skills:
            for skill_name, value in self.player_character.skills.items(): self._print_color(f"- {skill_name.capitalize()}: {value}", Colors.WHITE)
        else: self._print_color("No specialized skills.", Colors.DIM)
        self._print_color("\n--- Active Objectives ---", Colors.CYAN + Colors.BOLD)
        active_objectives = [obj for obj in self.player_character.objectives if obj.get("active", False) and not obj.get("completed", False)]
        if active_objectives:
            for obj in active_objectives:
                self._print_color(f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE)
                current_stage = self.player_character.get_current_stage_for_objective(obj.get('id'))
                if current_stage: self._print_color(f"  Current Stage: {current_stage.get('description', 'No stage description')}", Colors.CYAN)
        else: self._print_color("No active objectives.", Colors.DIM)
        self._print_color("\n--- Inventory Highlights ---", Colors.CYAN + Colors.BOLD)
        if self.player_character.inventory:
            highlights = []
            for item_obj in self.player_character.inventory:
                item_name = item_obj["name"]; item_qty = item_obj.get("quantity", 1)
                item_default_props = DEFAULT_ITEMS.get(item_name, {})
                if (item_default_props.get("stackable") or item_default_props.get("value") is not None) and item_qty > 1: highlights.append(f"{item_name} (x{item_qty})")
                else: highlights.append(item_name)
            if highlights: self._print_color(", ".join(highlights), Colors.GREEN)
            else: self._print_color("Carrying some items.", Colors.DIM)
        else: self._print_color("Carrying nothing of note.", Colors.DIM)
        self._print_color("\n--- Relationships ---", Colors.CYAN + Colors.BOLD); meaningful_relationships = False
        for char_name, char_obj in self.all_character_objects.items():
            if char_obj.is_player: continue
            if hasattr(char_obj, 'relationship_with_player') and char_obj.relationship_with_player != 0:
                relationship_text = self.get_relationship_text(char_obj.relationship_with_player)
                self._print_color(f"- {char_name}: {relationship_text}", Colors.WHITE); meaningful_relationships = True
        if not meaningful_relationships: self._print_color("No significant relationships established yet.", Colors.DIM)
        self._print_color("", Colors.RESET)

    def _handle_inventory_command(self):
        if self.player_character:
            self._print_color("\n--- Your Inventory ---", Colors.CYAN + Colors.BOLD)
            inv_desc = self.player_character.get_inventory_description()
            if inv_desc.startswith("You are carrying: "):
                items_str = inv_desc.replace("You are carrying: ", "", 1)
                if items_str.lower() == "nothing.": self._print_color("- Nothing", Colors.DIM)
                else:
                    items_list = items_str.split(", ")
                    for item_with_details in items_list: self._print_color(f"- {item_with_details.rstrip('.')}", Colors.GREEN)
                    if items_list: self._print_color("(Hint: You can 'use [item]', 'read [item]', 'drop [item]', or 'give [item] to [person]'.)", Colors.DIM)
            elif inv_desc.lower() == "you are carrying nothing.": self._print_color("- Nothing", Colors.DIM)
            else: print(inv_desc)
        else: self._print_color("Cannot display inventory: Player character not available.", Colors.RED)

    def _handle_take_command(self, argument):
        if not argument: self._print_color("What do you want to take?", Colors.RED); return False, False
        if not self.player_character: self._print_color("Cannot take items: Player character not available.", Colors.RED); return False, False
        item_to_take_name = argument.lower()
        location_items = self.dynamic_location_items.get(self.current_location_name, [])
        item_found_in_loc, ambiguous = self._get_matching_location_item(item_to_take_name)
        item_idx_in_loc = -1
        if item_found_in_loc:
            item_idx_in_loc = location_items.index(item_found_in_loc)
        elif ambiguous:
            return False, False
        if item_found_in_loc:
            item_default_props = DEFAULT_ITEMS.get(item_found_in_loc["name"], {})
            if item_default_props.get("takeable", False):
                take_quantity = 1; actual_taken_qty = 0
                if item_default_props.get("stackable") or item_default_props.get("value") is not None:
                    current_qty_in_loc = item_found_in_loc.get("quantity", 1); actual_taken_qty = min(take_quantity, current_qty_in_loc)
                    item_found_in_loc["quantity"] -= actual_taken_qty
                    if item_found_in_loc["quantity"] <= 0: location_items.pop(item_idx_in_loc)
                else: actual_taken_qty = 1; location_items.pop(item_idx_in_loc)
                if self.player_character.add_to_inventory(item_found_in_loc["name"], actual_taken_qty):
                    self._print_color(f"You take the {item_found_in_loc['name']}" + (f" (x{actual_taken_qty})" if actual_taken_qty > 1 and (item_default_props.get("stackable") or item_default_props.get("value") is not None) else "") + ".", Colors.GREEN)
                    self.last_significant_event_summary = f"took the {item_found_in_loc['name']}."
                    if item_default_props.get("is_notable"): self.player_character.apparent_state = random.choice(["thoughtful", "burdened"])
                    if self.player_character.name == "Rodion Raskolnikov" and item_found_in_loc["name"] == "raskolnikov's axe":
                        self.player_notoriety_level = min(3, max(0, self.player_notoriety_level + 0.5)); self._print_color("(Reclaiming the axe sends a shiver down your spine, a feeling of being marked.)", Colors.RED + Colors.DIM)
                    for npc in self.npcs_in_current_location:
                        if npc.name != self.player_character.name:
                            npc.add_player_memory(memory_type="player_action_observed", turn=self.game_time, content={"action": "took_item", "item_name": item_found_in_loc["name"], "quantity": actual_taken_qty, "location": self.current_location_name}, sentiment_impact= -1 if item_default_props.get("is_notable") else 0)
                    taken_item_name = item_found_in_loc["name"]; taken_item_props = DEFAULT_ITEMS.get(taken_item_name, {}) # Changed: self.game_config
                    if taken_item_props.get("readable"): self._print_color(f"(Hint: You can now 'read {taken_item_name}'.)", Colors.DIM)
                    elif taken_item_props.get("use_effect_player") and taken_item_name != "worn coin": self._print_color(f"(Hint: You can try to 'use {taken_item_name}'.)", Colors.DIM)
                    return True, True
                else:
                    # Check if the failure was due to trying to take a non-stackable item already possessed
                    item_name_failed_to_add = item_found_in_loc["name"]
                    item_props_failed = DEFAULT_ITEMS.get(item_name_failed_to_add, {})
                    is_non_stackable_unique = not item_props_failed.get("stackable", False) and item_props_failed.get("value") is None

                    if is_non_stackable_unique and self.player_character.has_item(item_name_failed_to_add):
                        self._print_color(f"You cannot carry another '{item_name_failed_to_add}'.", Colors.YELLOW)
                    else:
                        # Generic failure message if not the specific non-stackable case
                        self._print_color(f"Failed to add {item_name_failed_to_add} to inventory.", Colors.RED)
                    return False, True # Action was attempted (hence True for show_atmospherics) but failed
            else: self._print_color(f"You can't take the {item_found_in_loc['name']}.", Colors.YELLOW); return False, True
        else: self._print_color(f"You don't see any '{item_to_take_name}' here to take.", Colors.RED); return False, False

    def _handle_drop_command(self, argument):
        if not argument: self._print_color("What do you want to drop?", Colors.RED); return False, False
        if not self.player_character: self._print_color("Cannot drop items: Player character not available.", Colors.RED); return False, False
        item_to_drop_name_input = argument.lower()
        item_in_inventory_obj, ambiguous = self._get_matching_inventory_item(item_to_drop_name_input)
        if ambiguous:
            return False, False
        if item_in_inventory_obj:
            item_name_to_drop = item_in_inventory_obj["name"]; item_default_props = DEFAULT_ITEMS.get(item_name_to_drop, {}); drop_quantity = 1
            if self.player_character.remove_from_inventory(item_name_to_drop, drop_quantity):
                location_items = self.dynamic_location_items.setdefault(self.current_location_name, []); existing_loc_item = None
                for loc_item in location_items:
                    if loc_item["name"] == item_name_to_drop: existing_loc_item = loc_item; break
                if existing_loc_item and (item_default_props.get("stackable") or item_default_props.get("value") is not None): existing_loc_item["quantity"] = existing_loc_item.get("quantity", 0) + drop_quantity
                else: location_items.append({"name": item_name_to_drop, "quantity": drop_quantity})
                self._print_color(f"You drop the {item_name_to_drop}.", Colors.GREEN); self.last_significant_event_summary = f"dropped the {item_name_to_drop}."
                for npc in self.npcs_in_current_location:
                    if npc.name != self.player_character.name:
                        npc.add_player_memory(memory_type="player_action_observed", turn=self.game_time, content={"action": "dropped_item", "item_name": item_name_to_drop, "quantity": drop_quantity, "location": self.current_location_name}, sentiment_impact=0)
                return True, True
            else: self._print_color(f"You try to drop {item_name_to_drop}, but something is wrong.", Colors.RED); return False, True
        else: self._print_color(f"You don't have '{item_to_drop_name_input}' to drop.", Colors.RED); return False, False

    def _handle_use_command(self, argument):
        if not self.player_character: self._print_color("Cannot use items: Player character not available.", Colors.RED); return False
        if isinstance(argument, tuple): item_name_input, target_name_input, interaction_mode = argument; return self.handle_use_item(item_name_input, target_name_input, interaction_mode)
        elif argument: return self.handle_use_item(argument, None, "use_self_implicit")
        else: self._print_color("What do you want to use or read?", Colors.RED); return False

    def _handle_think_command(self):
        if not self.player_character: self._print_color("Cannot think: Player character not available.", Colors.RED); return
        self._print_color("You pause to reflect...", Colors.MAGENTA)
        full_reflection_context = self._get_objectives_summary(self.player_character) + \
                                f"\nInventory: {self.player_character.get_inventory_description()}" + \
                                f"\nYour current apparent state is '{self.player_character.apparent_state}'." + \
                                f"\nRecent notable events: {self._get_recent_events_summary()}"
        if self.player_character.name == "Rodion Raskolnikov":
            theory_objective = self.player_character.get_objective_by_id("understand_theory")
            if theory_objective and theory_objective.get("active"):
                current_stage_obj = self.player_character.get_current_stage_for_objective("understand_theory")
                current_stage_desc = current_stage_obj.get("description", "an unknown stage") if current_stage_obj else "an unknown stage"
                full_reflection_context += (f"\nHe is particularly wrestling with his 'extraordinary man' theory (currently at stage: '{current_stage_desc}'). How do his immediate surroundings, recent events, or current feelings intersect with or challenge this core belief?")

        reflection = None
        ai_generated = False
        if not self.low_ai_data_mode and self.gemini_api.model:
            reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, self.get_current_time_period(), full_reflection_context)

        if reflection is None or (isinstance(reflection, str) and reflection.startswith("(OOC:")) or self.low_ai_data_mode:
            if STATIC_PLAYER_REFLECTIONS:
                reflection = random.choice(STATIC_PLAYER_REFLECTIONS)
            else:
                reflection = "Your mind is a whirl of thoughts." # Ultimate fallback
        else:
            ai_generated = True

        final_reflection = self._apply_verbosity(reflection)
        self._print_color(f"Inner thought: \"{final_reflection}\"", Colors.GREEN) # Print whatever reflection is chosen
        if ai_generated:
            self._remember_ai_output(final_reflection, "think")
        self.last_significant_event_summary = "was lost in thought."

    def _handle_wait_command(self):
        self._print_color("You wait for a while...", Colors.MAGENTA); self.last_significant_event_summary = "waited, letting time and thoughts drift."
        return TIME_UNITS_PER_PLAYER_ACTION * random.randint(3, 6)

    def _handle_talk_to_command(self, argument):
        """Handles the 'talk to [npc]' command."""
        if not argument: self._print_color("Who do you want to talk to?", Colors.RED); return False, False
        if not self.npcs_in_current_location: self._print_color("There's no one here to talk to.", Colors.DIM); return False, False
        if not self.player_character: self._print_color("Cannot talk: Player character not available.", Colors.RED); return False, False
        target_name_input = argument.lower()
        target_npc, ambiguous = self._get_matching_npc(target_name_input)
        if ambiguous:
            return False, False
        if target_npc:
            if target_npc.name == "Porfiry Petrovich":
                solve_murders_obj = target_npc.get_objective_by_id("solve_murders")
                if solve_murders_obj and solve_murders_obj.get("active"):
                    current_stage_obj = target_npc.get_current_stage_for_objective("solve_murders")
                    if current_stage_obj and current_stage_obj.get("stage_id") == "encourage_confession":
                        new_state = "intensely persuasive"
                        if target_npc.apparent_state != new_state: target_npc.apparent_state = new_state; self._print_color(f"({target_npc.name} seems to adopt a new demeanor, his gaze sharpening. He now appears {target_npc.apparent_state}.)", Colors.MAGENTA + Colors.DIM)
            self.current_conversation_log = []; MAX_CONVERSATION_LOG_LINES = 20
            self._print_color(f"\nYou approach {Colors.YELLOW}{target_npc.name}{Colors.RESET} (appears {target_npc.apparent_state}).", Colors.WHITE)
            should_print_static_greeting = True
            # Removed specific condition for Raskolnikov and Razumikhin
            if should_print_static_greeting and hasattr(target_npc, 'greeting') and target_npc.greeting:
                 initial_greeting_text = f"{target_npc.name}: \"{target_npc.greeting}\""; self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end=""); print(f"\"{target_npc.greeting}\"")
                 self.current_conversation_log.append(initial_greeting_text)
                 if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES: self.current_conversation_log.pop(0)
            conversation_active = True
            while conversation_active:
                player_dialogue = self._input_color(f"You ({Colors.GREEN}{self.player_character.name}{Colors.RESET}): {self._prompt_arrow()}", Colors.GREEN).strip()
                if player_dialogue.lower() in ['history', 'review', 'log']:
                    self._print_color("\n--- Recent Conversation History ---", Colors.CYAN + Colors.BOLD)
                    if not self.current_conversation_log: self._print_color("No history recorded yet for this conversation.", Colors.DIM)
                    else:
                        history_to_show = self.current_conversation_log[-10:]
                        for line in history_to_show:
                            if line.startswith("You:"): self._print_color(line, Colors.GREEN)
                            elif ":" in line: speaker, rest_of_line = line.split(":", 1); self._print_color(f"{speaker}:", Colors.YELLOW, end=""); print(rest_of_line)
                            else: self._print_color(line, Colors.DIM)
                    self._print_color("--- End of History ---", Colors.CYAN + Colors.BOLD); continue
                logged_player_dialogue = f"You: {player_dialogue}"; self.current_conversation_log.append(logged_player_dialogue)
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES: self.current_conversation_log.pop(0)
                if self.check_conversation_conclusion(player_dialogue): self._print_color(f"You end the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.", Colors.WHITE); conversation_active = False; break
                if not player_dialogue: self._print_color("You remain silent for a moment.", Colors.DIM); pass
                used_ai_dialogue = False
                if self.gemini_api.model:
                    ai_response = self.gemini_api.get_npc_dialogue(target_npc, self.player_character, player_dialogue, self.current_location_name, self.get_current_time_period(), self.get_relationship_text(target_npc.relationship_with_player), target_npc.get_player_memory_summary(self.game_time), self.player_character.apparent_state, self.player_character.get_notable_carried_items_summary(), self._get_recent_events_summary(), self._get_objectives_summary(target_npc), self._get_objectives_summary(self.player_character))
                    used_ai_dialogue = True
                else: ai_response = random.choice(["Yes?", "Hmm.", "What is it?", "I am busy.", f"{target_npc.greeting if hasattr(target_npc, 'greeting') else '...'}"]); self._print_color(f"{Colors.DIM}(Using placeholder dialogue){Colors.RESET}", Colors.DIM)
                ai_response = self._apply_verbosity(ai_response)
                target_npc.update_relationship(player_dialogue, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS, self.game_time); self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end=""); print(f"\"{ai_response}\"")
                logged_ai_response = f"{target_npc.name}: \"{ai_response}\""; self.current_conversation_log.append(logged_ai_response)
                if used_ai_dialogue and not (isinstance(ai_response, str) and ai_response.startswith("(OOC:")):
                    self._remember_ai_output(ai_response, "npc_dialogue")
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES: self.current_conversation_log.pop(0)
                self.last_significant_event_summary = f"spoke with {target_npc.name} who said: \"{ai_response[:50]}...\""
                if self.check_conversation_conclusion(ai_response): self._print_color(f"\nThe conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET} seems to have concluded.", Colors.MAGENTA); conversation_active = False
                self.advance_time(TIME_UNITS_PER_PLAYER_ACTION)
                if self.event_manager.check_and_trigger_events(): self.last_significant_event_summary = "an event occurred during conversation."
            unusual_states = ["feverish", "slightly drunk", "paranoid", "agitated", "dangerously agitated", "remorseful", "haunted by dreams", "injured"]
            current_player_state = self.player_character.apparent_state
            if current_player_state in unusual_states:
                sentiment = -1 if current_player_state in ["dangerously agitated", "paranoid"] else 0
                target_npc.add_player_memory(memory_type="observed_player_state", turn=self.game_time, content={"state": current_player_state, "context": "during conversation"}, sentiment_impact=sentiment)
            for item_in_inventory in self.player_character.inventory:
                item_name = item_in_inventory.get("name")
                if item_name in HIGHLY_NOTABLE_ITEMS_FOR_MEMORY: # Changed
                    sentiment = 0
                    if item_name in ["raskolnikov's axe", "bloodied rag"]: sentiment = -1
                    elif item_name == "sonya's cypress cross" and target_npc.name != "Sonya Marmeladova":
                        if target_npc.name == "Porfiry Petrovich" and self.player_character.name == "Rodion Raskolnikov": sentiment = -1
                    target_npc.add_player_memory(memory_type="observed_player_inventory", turn=self.game_time, content={"item_name": item_name, "context": "player was carrying during conversation"}, sentiment_impact=sentiment)
            if self.player_character.name == "Rodion Raskolnikov" and target_npc and target_npc.name == "Porfiry Petrovich":
                self.player_notoriety_level = min(3, max(0, self.player_notoriety_level + 0.15)); self._print_color("(Your conversation with Porfiry seems to have drawn some attention...)", Colors.YELLOW + Colors.DIM)
            return True, True
        else: self._print_color(f"You don't see anyone named '{target_name_input}' here.", Colors.RED); return False, False

    def _handle_move_to_command(self, argument):
        if not argument: self._print_color("Where do you want to move to?", Colors.RED); return False, False
        if not self.player_character: self._print_color("Cannot move: Player character not available.", Colors.RED); return False, False
        target_exit_input = argument.lower(); moved = False; potential_target_loc_name = None
        current_location_data = LOCATIONS_DATA.get(self.current_location_name)
        if not current_location_data: self._print_color(f"Error: Data for current location '{self.current_location_name}' is missing.", Colors.RED); return False, False
        location_exits = current_location_data.get("exits", {})
        potential_target_loc_name, ambiguous = self._get_matching_exit(target_exit_input, location_exits)
        if ambiguous:
            return False, False
        if potential_target_loc_name:
            old_location = self.current_location_name; self.current_location_name = potential_target_loc_name
            self.player_character.current_location = potential_target_loc_name; self.current_location_description_shown_this_visit = False
            self.last_significant_event_summary = f"moved from {old_location} to {self.current_location_name}."
            if self.player_character.name == "Rodion Raskolnikov" and potential_target_loc_name in ["Pawnbroker's Apartment", "Pawnbroker's Apartment Building"]:
                self.player_notoriety_level = min(3, max(0, self.player_notoriety_level + 0.25)); self._print_color("(Your presence in this place feels heavy with unseen eyes...)", Colors.YELLOW + Colors.DIM)
                if DEBUG_LOGS:
                    print(f"[DEBUG] Notoriety changed to: {self.player_notoriety_level}")
            self.update_current_location_details(from_explicit_look_cmd=False); moved = True
            return True, True
        else: self._print_color(f"You can't find a way to '{target_exit_input}' from here.", Colors.RED); return False, False

    def _handle_read_item(self, item_to_use_name, item_props, item_obj_in_inventory):
        if not self.player_character:
            self._print_color("Cannot read items: Player character not available.", Colors.RED)
            return False
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        if not item_props.get("readable"): self._print_color(f"You can't read the {item_to_use_name}.", Colors.YELLOW); return False
        effect_key = item_props.get("use_effect_player")
        if item_to_use_name == "old newspaper" or item_to_use_name == "fresh newspaper":
            self._print_color(f"You smooth out the creases of the {item_to_use_name} and scan the faded print.", Colors.WHITE)
            article_snippet = None
            ai_generated = False
            if not self.low_ai_data_mode and self.gemini_api.model:
                article_snippet = self.gemini_api.get_newspaper_article_snippet(self.current_day, self._get_recent_events_summary(), self._get_objectives_summary(player_character), player_character.apparent_state)

            if article_snippet is None or (isinstance(article_snippet, str) and article_snippet.startswith("(OOC:")) or self.low_ai_data_mode:
                if STATIC_NEWSPAPER_SNIPPETS:
                    article_snippet = random.choice(STATIC_NEWSPAPER_SNIPPETS)
                else:
                    article_snippet = "The newsprint is smudged and uninteresting." # Ultimate fallback

                if article_snippet : # Make sure we have something to print/log
                    article_snippet = self._apply_verbosity(article_snippet)
                    self._print_color(f"An article catches your eye: \"{article_snippet}\"", Colors.CYAN) # Static in Cyan
                    player_character.add_journal_entry("News (Static)", article_snippet, self._get_current_game_time_period_str()) # Optionally log differently
            elif article_snippet: # AI success and not OOC
                article_snippet = self._apply_verbosity(article_snippet)
                self._print_color(f"An article catches your eye: \"{article_snippet}\"", Colors.YELLOW)
                player_character.add_journal_entry("News (AI)", article_snippet, self._get_current_game_time_period_str()) # Optionally log differently
                ai_generated = True

            if not article_snippet: # Final fallback if all else fails
                 self._print_color("The print is too faded or the news too mundane to hold your interest.", Colors.DIM)

            # Common logic for both AI and static snippets if they are valid
            if article_snippet:
                if "crime" in article_snippet.lower() or "investigation" in article_snippet.lower() or "murder" in article_snippet.lower():
                    player_character.apparent_state = "thoughtful"
                    if player_character.name == "Rodion Raskolnikov":
                        player_character.add_player_memory(memory_type="read_news_crime", turn=self.game_time, content={"summary": "Read unsettling news about the recent crime."}, sentiment_impact=0)
                        self.player_notoriety_level = min(self.player_notoriety_level + 0.1, 3)
                self.last_significant_event_summary = f"read an {item_to_use_name}."
                if ai_generated:
                    self._remember_ai_output(article_snippet, "news_article")
            return True
        elif item_to_use_name == "mother's letter":
            self._print_color(f"You re-read your mother's letter. Her words of love and anxiety, Dunya's predicament... it all weighs heavily on you.", Colors.YELLOW)
            reflection = None
            prompt_context = "re-reading mother's letter about Dunya and Luzhin, feeling guilt and responsibility"
            if not self.low_ai_data_mode and self.gemini_api.model:
                reflection = self.gemini_api.get_player_reflection(player_character, current_location_name, self.get_current_time_period(), prompt_context)

            if reflection is None or (isinstance(reflection, str) and reflection.startswith("(OOC:")) or self.low_ai_data_mode:
                if STATIC_PLAYER_REFLECTIONS:
                    reflection = random.choice(STATIC_PLAYER_REFLECTIONS)
                else:
                    reflection = "The letter stirs a whirlwind of emotions and responsibilities." # Ultimate fallback
                self._print_color(f"\"{self._apply_verbosity(reflection)}\"", Colors.DIM) # Static reflection in DIM
            else: # AI success
                reflection = self._apply_verbosity(reflection)
                self._print_color(f"\"{reflection}\"", Colors.CYAN)
                self._remember_ai_output(reflection, "read_letter")

            player_character.apparent_state = random.choice(["burdened", "agitated", "resolved"])
            if player_character.name == "Rodion Raskolnikov": player_character.add_player_memory(memory_type="reread_mother_letter", turn=self.game_time, content={"summary": "Re-reading mother's letter intensified feelings of duty and distress."}, sentiment_impact=-1)
            self.last_significant_event_summary = f"re-read the {item_to_use_name}."; return True
        elif item_to_use_name == "sonya's new testament":
            self._print_color(f"You open {item_to_use_name}. The familiar words of the Gospels seem to both accuse and offer a sliver of hope.", Colors.GREEN)
            reflection = None
            prompt_context = f"reading from {item_to_use_name}, pondering Lazarus, guilt, and salvation"
            if not self.low_ai_data_mode and self.gemini_api.model:
                reflection = self.gemini_api.get_player_reflection(player_character, current_location_name, self.get_current_time_period(), prompt_context)

            if reflection is None or (isinstance(reflection, str) and reflection.startswith("(OOC:")) or self.low_ai_data_mode:
                if STATIC_PLAYER_REFLECTIONS:
                    reflection = random.choice(STATIC_PLAYER_REFLECTIONS)
                else:
                    reflection = "The words offer a strange mix of judgment and hope." # Ultimate fallback
                self._print_color(f"\"{self._apply_verbosity(reflection)}\"", Colors.DIM) # Static reflection in DIM
            else: # AI success
                reflection = self._apply_verbosity(reflection)
                self._print_color(f"\"{reflection}\"", Colors.CYAN)
                self._remember_ai_output(reflection, "read_testament")

            if player_character.name == "Rodion Raskolnikov":
                player_character.apparent_state = random.choice(["contemplative", "remorseful", "thoughtful", "hopeful"])
                player_character.add_player_memory(memory_type="read_testament_sonya", turn=self.game_time, content={"summary": "Read from the New Testament, stirring deep thoughts of salvation and suffering."}, sentiment_impact=0)
            self.last_significant_event_summary = f"read from {item_to_use_name}."; return True
        elif item_to_use_name == "anonymous note":
            if item_obj_in_inventory and "generated_content" in item_obj_in_inventory:
                self._print_color(f"You read the {item_to_use_name}:", Colors.WHITE); self._print_color(f"\"{item_obj_in_inventory['generated_content']}\"", Colors.CYAN)
                player_character.add_journal_entry("Note", item_obj_in_inventory['generated_content'], self._get_current_game_time_period_str()); self.last_significant_event_summary = f"read an {item_to_use_name}."
                if "watch" in item_obj_in_inventory['generated_content'].lower() or "know" in item_obj_in_inventory['generated_content'].lower(): player_character.apparent_state = "paranoid"
                return True
            else: self._print_color(f"The {item_to_use_name} seems to be blank or unreadable.", Colors.RED); return False
        elif item_to_use_name == "IOU Slip":
            if item_obj_in_inventory and item_obj_in_inventory.get("content"): self._print_color(f"You examine the {item_to_use_name}: \"{item_obj_in_inventory['content']}\"", Colors.YELLOW)
            else: self._print_color(f"You look at the {item_to_use_name}. It's a formal-looking slip of paper.", Colors.YELLOW)
            self.last_significant_event_summary = f"read an {item_to_use_name}."; return True
        elif item_to_use_name == "Student's Dog-eared Book":
            book_reflection = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                book_reflection = self.gemini_api.get_item_interaction_description(player_character, item_to_use_name, item_props, "read", current_location_name, self.get_current_time_period())

            if book_reflection is None or (isinstance(book_reflection, str) and book_reflection.startswith("(OOC:")) or self.low_ai_data_mode:
                book_reflection = generate_static_item_interaction_description(item_to_use_name, "read")
                self._print_color(f"You open the {item_to_use_name}. {book_reflection}", Colors.CYAN) # Static in Cyan
            else: # AI success
                self._print_color(f"You open the {item_to_use_name}. {book_reflection}", Colors.YELLOW)

            self.last_significant_event_summary = f"read from a {item_to_use_name}."; used_successfully = True; return True # Keep used_successfully variable, though it's always true here

        read_reflection = None
        if not self.low_ai_data_mode and self.gemini_api.model:
            read_reflection = self.gemini_api.get_item_interaction_description(player_character, item_to_use_name, item_props, "read", current_location_name, self.get_current_time_period())

        if read_reflection is None or (isinstance(read_reflection, str) and read_reflection.startswith("(OOC:")) or self.low_ai_data_mode:
            read_reflection = generate_static_item_interaction_description(item_to_use_name, "read")
            self._print_color(f"You read the {item_to_use_name}. {read_reflection}", Colors.CYAN) # Static in Cyan
        else: # AI success
            self._print_color(f"You read the {item_to_use_name}. {read_reflection}", Colors.YELLOW)

        self.last_significant_event_summary = f"read the {item_to_use_name}."; return True

    def _handle_self_use_item(self, item_to_use_name, item_props, effect_key):
        if not self.player_character:
            self._print_color("Cannot use items: Player character not available.", Colors.RED)
            return False
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        used_successfully = False
        if effect_key == "comfort_self_if_ill" and item_to_use_name == "tattered handkerchief":
            if player_character.apparent_state in ["feverish", "coughing", "ill", "haunted by dreams"]:
                self._print_color(f"You press the {item_to_use_name} to your brow. It offers little physical comfort, but it's something to cling to.", Colors.YELLOW)
                if player_character.apparent_state == "feverish" and random.random() < 0.2: player_character.apparent_state = "less feverish"; self._print_color("The coolness, imagined or real, seems to lessen the fever's grip for a moment.", Colors.CYAN)
                self.last_significant_event_summary = f"used a {item_to_use_name} while feeling unwell."; used_successfully = True
            else: self._print_color(f"You look at the {item_to_use_name}. It seems rather pointless to use it now.", Colors.YELLOW)
        elif effect_key == "examine_bottle_for_residue" and item_to_use_name == "dusty bottle":
            self._print_color(f"You peer into the {item_to_use_name}. A faint, stale smell of cheap spirits lingers. It's long empty.", Colors.YELLOW)
            self.last_significant_event_summary = f"examined a {item_to_use_name}."; used_successfully = True
        elif effect_key == "grip_axe_and_reminisce_horror" and item_to_use_name == "raskolnikov's axe":
            if player_character.name == "Rodion Raskolnikov":
                self._print_color(f"You grip the {item_to_use_name}. Its cold weight is a familiar dread. The memories, sharp and bloody, flood your mind. You feel a wave of nausea, then a chilling resolve, then utter despair.", Colors.RED + Colors.BOLD)
                player_character.apparent_state = random.choice(["dangerously agitated", "remorseful", "paranoid"]); self.last_significant_event_summary = f"held the axe, tormented by memories."; used_successfully = True
            else: self._print_color(f"You look at the {item_to_use_name}. It's a grim object, heavy and unsettling. Best left alone.", Colors.YELLOW); used_successfully = True
        elif effect_key == "reflect_on_faith_and_redemption" and item_to_use_name == "sonya's cypress cross":
            if player_character.name == "Rodion Raskolnikov":
                self._print_color("You clutch the small cypress cross. It feels strangely significant in your hand, a stark contrast to the turmoil within you.", Colors.GREEN)
                player_character.apparent_state = random.choice(["remorseful", "contemplative", "hopeful"]); self.last_significant_event_summary = f"held Sonya's cross, feeling its weight and Sonya's sacrifice."
                reflection = self.gemini_api.get_player_reflection(player_character, current_location_name, self.get_current_time_period(), "Holding Sonya's cross, new thoughts about suffering and sacrifice surface.")
                self._print_color(f"\"{reflection}\"", Colors.CYAN); used_successfully = True
            else: self._print_color(f"You examine {item_to_use_name}. It seems to be a simple wooden cross, yet it emanates a certain potent feeling.", Colors.YELLOW); used_successfully = True
        elif effect_key == "examine_rag_and_spiral_into_paranoia" and item_to_use_name == "bloodied rag":
            self._print_color(f"You stare at the {item_to_use_name}. The dark stains seem to shift and spread before your eyes. Every sound, every shadow, feels like an accusation.", Colors.RED)
            player_character.apparent_state = "paranoid"
            if player_character.name == "Rodion Raskolnikov": player_character.add_player_memory(memory_type="observed_bloodied_rag", turn=self.game_time, content={"summary": "The sight of the bloodied rag brought a fresh wave of paranoia."}, sentiment_impact=-1); self.player_notoriety_level = min(self.player_notoriety_level + 0.5, 3)
            self.last_significant_event_summary = f"was deeply disturbed by a {item_to_use_name}."; used_successfully = True
        elif effect_key == "drink_vodka_for_oblivion" and item_to_use_name == "cheap vodka":
            original_state_feverish = (player_character.apparent_state == "feverish")
            self._print_color(f"You take a long swig of the harsh vodka. It burns on the way down, offering a brief, false warmth and a dulling of the senses.", Colors.MAGENTA)

            # Default effect of vodka
            player_character.apparent_state = "slightly drunk"

            if player_character.has_item("cheap vodka"): player_character.remove_from_inventory("cheap vodka", 1)
            else: self._print_color("Odd, the bottle seems to have vanished before you could drink it all.", Colors.DIM)
            self.last_significant_event_summary = "drank some cheap vodka to numb the thoughts."

            # Override if originally feverish
            if original_state_feverish:
                player_character.apparent_state = "agitated"
                self._print_color("The vodka clashes terribly with your fever, making you feel worse.", Colors.RED)
            used_successfully = True; return True
        elif effect_key == "examine_bundle_and_face_guilt_for_Lizaveta" and item_to_use_name == "lizaveta's bundle":
            self._print_color(f"You hesitantly open {item_to_use_name}. Inside are a few pitiful belongings: a worn shawl, a child's small wooden toy, a copper coin... The sight is a fresh stab of guilt for the gentle Lizaveta.", Colors.YELLOW)
            if player_character.name == "Rodion Raskolnikov": player_character.apparent_state = "remorseful"; player_character.add_player_memory(memory_type="examined_lizavetas_bundle", turn=self.game_time, content={"summary": "Examined lizaveta's bundle; the innocence of the items was a heavy burden."}, sentiment_impact=-1)
            self.last_significant_event_summary = f"examined lizaveta's bundle, increasing the weight of guilt."; used_successfully = True
        elif effect_key == "eat_bread_for_sustenance" and item_to_use_name == "Loaf of Black Bread":
            self._print_color(f"You tear off a piece of the dense {item_to_use_name}. It's coarse, but fills your stomach somewhat.", Colors.YELLOW)
            if player_character.apparent_state in ["burdened", "feverish", "despondent"]: player_character.apparent_state = "normal"; self._print_color("The bread provides a moment of simple relief.", Colors.CYAN)
            self.last_significant_event_summary = f"ate some {item_to_use_name}."; used_successfully = True
        elif effect_key == "contemplate_icon" and item_to_use_name == "Small, Tarnished Icon":
            icon_reflection = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                icon_reflection = self.gemini_api.get_item_interaction_description(player_character, item_to_use_name, item_props, "contemplate", current_location_name, self.get_current_time_period())

            if icon_reflection is None or (isinstance(icon_reflection, str) and icon_reflection.startswith("(OOC:")) or self.low_ai_data_mode:
                icon_reflection = generate_static_item_interaction_description(item_to_use_name, "contemplate")
                self._print_color(f"You gaze at the {item_to_use_name}. {icon_reflection}", Colors.CYAN) # Static in Cyan
            else: # AI success
                self._print_color(f"You gaze at the {item_to_use_name}. {icon_reflection}", Colors.YELLOW)
            self.last_significant_event_summary = f"contemplated a {item_to_use_name}."; used_successfully = True
        if not used_successfully: self._print_color(f"You contemplate the {item_to_use_name}, but don't find a specific use for it right now.", Colors.YELLOW); return False
        return used_successfully

    def _handle_persuade_command(self, argument):
        if not argument or not isinstance(argument, tuple) or len(argument) != 2: self._print_color("How do you want to persuade them? Use: persuade [person] that/to [your argument]", Colors.RED); return False, False
        target_npc_name, statement_text = argument
        if not self.player_character: self._print_color("Cannot persuade: Player character not available.", Colors.RED); return False, False
        target_npc = next((npc for npc in self.npcs_in_current_location if npc.name.lower().startswith(target_npc_name.lower())), None)
        if not target_npc: self._print_color(f"You don't see anyone named '{target_npc_name}' here to persuade.", Colors.RED); return False, False
        self._print_color(f"\nYou attempt to persuade {Colors.YELLOW}{target_npc.name}{Colors.RESET} that \"{statement_text}\"...", Colors.WHITE)
        difficulty = 2; success = self.player_character.check_skill("Persuasion", difficulty)
        persuasion_skill_check_result_text = "SUCCESS due to their skillful argument" if success else "FAILURE despite their efforts"
        used_ai_dialogue = False
        if self.gemini_api.model:
            ai_response = self.gemini_api.get_npc_dialogue_persuasion_attempt(target_npc, self.player_character, player_persuasive_statement=statement_text, current_location_name=self.current_location_name, current_time_period=self.get_current_time_period(), relationship_status_text=self.get_relationship_text(target_npc.relationship_with_player), npc_memory_summary=target_npc.get_player_memory_summary(self.game_time), player_apparent_state=self.player_character.apparent_state, player_notable_items_summary=self.player_character.get_notable_carried_items_summary(), recent_game_events_summary=self._get_recent_events_summary(), npc_objectives_summary=self._get_objectives_summary(target_npc), player_objectives_summary=self._get_objectives_summary(self.player_character), persuasion_skill_check_result_text=persuasion_skill_check_result_text)
            used_ai_dialogue = True
        else: ai_response = f"Hmm, '{statement_text}', you say? That's... something to consider. (Skill: {persuasion_skill_check_result_text})"; self._print_color(f"{Colors.DIM}(Using placeholder dialogue for persuasion){Colors.RESET}", Colors.DIM)
        ai_response = self._apply_verbosity(ai_response)
        self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end=""); print(f"\"{ai_response}\"")
        if used_ai_dialogue and not (isinstance(ai_response, str) and ai_response.startswith("(OOC:")):
            self._remember_ai_output(ai_response, "persuasion_dialogue")
        sentiment_impact_base = 0
        if success: self._print_color(f"Your argument seems to have had an effect!", Colors.GREEN); sentiment_impact_base = 1; target_npc.relationship_with_player += 1
        else: self._print_color(f"Your words don't seem to convince {target_npc.name}.", Colors.RED); sentiment_impact_base = -1; target_npc.relationship_with_player -= 1
        target_npc.add_player_memory(memory_type="persuasion_attempt", turn=self.game_time, content={"statement": statement_text[:100], "outcome": "success" if success else "failure", "npc_response_snippet": ai_response[:70]}, sentiment_impact=sentiment_impact_base)
        self.last_significant_event_summary = f"attempted to persuade {target_npc.name} regarding '{statement_text[:30]}...'."
        unusual_states = ["feverish", "slightly drunk", "paranoid", "agitated", "dangerously agitated", "remorseful", "haunted by dreams", "injured"]
        current_player_state = self.player_character.apparent_state
        if current_player_state in unusual_states:
            sentiment = -1 if current_player_state in ["dangerously agitated", "paranoid"] else 0
            target_npc.add_player_memory(memory_type="observed_player_state", turn=self.game_time, content={"state": current_player_state, "context": "during persuasion attempt"}, sentiment_impact=sentiment)
        for item_in_inventory in self.player_character.inventory:
            item_name = item_in_inventory.get("name")
            if item_name in HIGHLY_NOTABLE_ITEMS_FOR_MEMORY: # Changed
                sentiment = 0
                if item_name in ["raskolnikov's axe", "bloodied rag"]: sentiment = -1
                elif item_name == "sonya's cypress cross" and target_npc.name != "Sonya Marmeladova":
                    if target_npc.name == "Porfiry Petrovich" and self.player_character.name == "Rodion Raskolnikov": sentiment = -1
                target_npc.add_player_memory(memory_type="observed_player_inventory", turn=self.game_time, content={"item_name": item_name, "context": "player was carrying during persuasion attempt"}, sentiment_impact=sentiment)
        self.advance_time(TIME_UNITS_PER_PLAYER_ACTION); return True, True

    def _handle_give_item(self, item_to_use_name, item_props, target_name_input):
        if not self.player_character:
            self._print_color("Cannot give items: Player character not available.", Colors.RED)
            return False
        player_character = self.player_character
        current_location_name = self.current_location_name or "Unknown Location"
        target_npc = next((npc for npc in self.npcs_in_current_location if npc.name.lower().startswith(target_name_input.lower())), None)

        if not target_npc:
            self._print_color(f"You don't see '{target_name_input}' here to give anything to.", Colors.RED)
            return False

        # Check if player has the item (using a generic quantity of 1 for now)
        # More sophisticated quantity handling could be added if items become stackable in a way that 'give' needs to respect.
        if not player_character.has_item(item_to_use_name, quantity=1):
            self._print_color(f"You don't have {item_to_use_name} to give.", Colors.RED)
            return False

        # Attempt to remove the item from player's inventory
        if player_character.remove_from_inventory(item_to_use_name, 1):
            # Add item to NPC's inventory
            target_npc.add_to_inventory(item_to_use_name, 1) # Assuming quantity 1 for now

            self._print_color(f"You give the {item_to_use_name} to {target_npc.name}.", Colors.WHITE)

            # Generate NPC reaction using Gemini API
            relationship_text = self.get_relationship_text(target_npc.relationship_with_player)
            dialogue_prompt = f"(Player gives {item_to_use_name} to NPC. Player expects a reaction.)"

            reaction = None
            if not self.low_ai_data_mode and self.gemini_api.model:
                reaction = self.gemini_api.get_npc_dialogue(
                    target_npc, player_character, dialogue_prompt,
                    current_location_name, self.get_current_time_period(), relationship_text,
                    target_npc.get_player_memory_summary(self.game_time), player_character.apparent_state,
                    player_character.get_notable_carried_items_summary(), self._get_recent_events_summary(),
                    self._get_objectives_summary(target_npc), self._get_objectives_summary(player_character)
                )

            if reaction is None or (isinstance(reaction, str) and reaction.startswith("(OOC:")) or self.low_ai_data_mode :
                # Fallback static reaction if AI fails or low_ai_mode
                static_reactions = [
                    f"Oh, for me? Thank you for the {item_to_use_name}.",
                    f"A {item_to_use_name}? How thoughtful of you.",
                    f"I appreciate you giving me this {item_to_use_name}.",
                    f"Thank you, this {item_to_use_name} is noted."
                ]
                reaction = random.choice(static_reactions)
                self._print_color(f"{target_npc.name}: \"{reaction}\" {Colors.DIM}(Static reaction){Colors.RESET}", Colors.YELLOW)
            else: # AI Success
                 self._print_color(f"{target_npc.name}: \"{reaction}\"", Colors.YELLOW)


            # Update NPC's relationship with the player (e.g., a slight increase)
            target_npc.relationship_with_player += 1 # Simple increment, can be more nuanced

            # Add a memory to the NPC about receiving the item
            target_npc.add_player_memory(
                memory_type="received_item",
                turn=self.game_time,
                content={"item_name": item_to_use_name, "quantity": 1, "from_player": True, "context": "player_gave_item"},
                sentiment_impact=1 # Generally positive for receiving an item
            )

            self.last_significant_event_summary = f"gave {item_to_use_name} to {target_npc.name}."
            return True
        else:
            # This case should ideally be caught by has_item, but as a fallback
            self._print_color(f"You find you don't actually have {item_to_use_name} to give after all.", Colors.RED)
            return False

        # Fallback for any other unhandled case (though the logic above should cover most)
        self._print_color(f"You can't give the {item_to_use_name} in this way.", Colors.YELLOW)
        return False

    def handle_use_item(self, item_name_input, target_name_input=None, interaction_type="use_self_implicit"):
        if not self.player_character: self._print_color("Cannot use items: Player character not set.", Colors.RED); return False
        item_to_use_name = None; item_obj_in_inventory = None
        if item_name_input:
            for inv_item_obj_loop in self.player_character.inventory:
                if inv_item_obj_loop["name"].lower().startswith(item_name_input.lower()): item_to_use_name = inv_item_obj_loop["name"]; item_obj_in_inventory = inv_item_obj_loop; break
            if not item_to_use_name:
                if self.player_character.has_item(item_name_input): item_to_use_name = item_name_input; item_obj_in_inventory = next((item for item in self.player_character.inventory if item["name"] == item_to_use_name), None)
                else: self._print_color(f"You don't have '{item_name_input}' to {interaction_type.replace('_', ' ')}.", Colors.RED); return False
        elif interaction_type != "use_self_implicit": self._print_color(f"What do you want to {interaction_type.replace('_', ' ')}{(' on ' + target_name_input) if target_name_input else ''}?", Colors.RED); return False
        if not item_to_use_name : self._print_color("You need to specify an item to use or read.", Colors.RED); return False
        item_props = DEFAULT_ITEMS.get(item_to_use_name, {}); used_successfully = False
        if interaction_type == "read": used_successfully = self._handle_read_item(item_to_use_name, item_props, item_obj_in_inventory)
        elif interaction_type == "give" and target_name_input: used_successfully = self._handle_give_item(item_to_use_name, item_props, target_name_input)
        elif interaction_type == "use_on" and target_name_input: self._print_color(f"You try to use the {item_to_use_name} on {target_name_input}, but nothing specific happens.", Colors.YELLOW); used_successfully = False
        else:
            effect_key = item_props.get("use_effect_player")
            if effect_key: used_successfully = self._handle_self_use_item(item_to_use_name, item_props, effect_key)
            else: self._print_color(f"You contemplate the {item_to_use_name}, but don't find a specific use for it right now.", Colors.YELLOW); used_successfully = False
        if used_successfully and item_props.get("consumable", False) and item_to_use_name != "cheap vodka":
            if self.player_character.remove_from_inventory(item_to_use_name, 1): self._print_color(f"The {item_to_use_name} is used up.", Colors.MAGENTA)
        return used_successfully
