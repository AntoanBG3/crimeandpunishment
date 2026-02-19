import random
import copy
import re
import os
from .game_config import (Colors, TIME_UNITS_PER_PLAYER_ACTION, MAX_TIME_UNITS_PER_DAY, TIME_PERIODS,
                         TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE, NPC_MOVE_CHANCE,
                         DEFAULT_ITEMS, AMBIENT_RUMOR_CHANCE_PUBLIC_PLACE,
                         STATIC_DREAM_SEQUENCES, STATIC_RUMORS,
                         DREAM_CHANCE_TROUBLED_STATE, DREAM_CHANCE_NORMAL_STATE,
                         NPC_INTERACTION_CHANCE, TIME_UNITS_FOR_NPC_INTERACTION_CHANCE,
                         HIGHLY_NOTABLE_ITEMS_FOR_MEMORY, SAVE_GAME_FILE, DEBUG_LOGS)
from .location_module import LOCATIONS_DATA
from .character_module import Character, CHARACTERS_DATA

class WorldManager:
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
                    self.player_character.add_player_memory(
                        memory_type="dream",
                        turn=self.game_time,
                        content={"summary": f"Had a disturbing dream: {(dream_text if dream_text else '')[:50]}..."},
                        sentiment_impact=-1
                    )
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

    def _check_game_ending_conditions(self):
        if self.player_character and self.player_character.name == "Rodion Raskolnikov":
            obj_grapple = self.player_character.get_objective_by_id("grapple_with_crime")
            if obj_grapple and obj_grapple.get("completed", False):
                current_stage = self.player_character.get_current_stage_for_objective("grapple_with_crime")
                if current_stage and current_stage.get("is_ending_stage"):
                    self._print_color(f"\n--- The story of {self.player_character.name} has reached a conclusion ({current_stage.get('description', 'an end')}) ---", Colors.CYAN + Colors.BOLD)
                    return True
        return False

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
