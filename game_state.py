# game_state.py
import json
import os
import re
import random
import copy

from game_config import (Colors, API_CONFIG_FILE, GEMINI_MODEL_NAME, SAVE_GAME_FILE,
                         CONCLUDING_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS,
                         TIME_UNITS_PER_PLAYER_ACTION, MAX_TIME_UNITS_PER_DAY, TIME_PERIODS,
                         TIME_UNITS_FOR_NPC_INTERACTION_CHANCE, NPC_INTERACTION_CHANCE,
                         TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE, NPC_MOVE_CHANCE,
                         DEFAULT_ITEMS, COMMAND_SYNONYMS, PLAYER_APPARENT_STATES,
                         DREAM_CHANCE_NORMAL_STATE, DREAM_CHANCE_TROUBLED_STATE,
                         RUMOR_CHANCE_PER_NPC_INTERACTION, AMBIENT_RUMOR_CHANCE_PUBLIC_PLACE,
                         NPC_SHARE_RUMOR_MIN_RELATIONSHIP, GENERIC_SCENERY_KEYWORDS)
from character_module import Character, CHARACTERS_DATA
from location_module import LOCATIONS_DATA
from gemini_interactions import GeminiAPI
from event_manager import EventManager


class Game:
    def __init__(self):
        self.player_character = None
        self.all_character_objects = {}
        self.npcs_in_current_location = []
        self.current_location_name = None
        self.dynamic_location_items = {}

        self.gemini_api = GeminiAPI() 
        self.event_manager = EventManager(self)
        self.game_config = __import__('game_config') 

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
        self.overheard_rumors = [] # This line is already present from the previous successful edit.

    def _get_current_game_time_period_str(self):
        return f"Day {self.current_day}, {self.get_current_time_period()}"

    def _get_objectives_summary(self, character):
        if not character or not hasattr(character, 'objectives') or not character.objectives:
            return "No particular objectives."

        active_objective_details = []
        for obj in character.objectives:
            if obj.get("active") and not obj.get("completed"):
                obj_desc = obj.get('description', 'An unknown goal.')
                current_stage = None
                # Ensure get_current_stage_for_objective is callable on the character object
                if hasattr(character, 'get_current_stage_for_objective') and callable(character.get_current_stage_for_objective):
                    current_stage = character.get_current_stage_for_objective(obj.get('id'))

                if current_stage:
                    stage_desc = current_stage.get('description', 'unspecified stage')
                    active_objective_details.append(f"{obj_desc} (Currently: {stage_desc})")
                else:
                    active_objective_details.append(f"{obj_desc} (Currently: unspecified stage)")

        if not active_objective_details:
            return "Currently pursuing no specific objectives."

        # For player, use "Your current objectives:", for NPCs, use "Their current objectives:" or similar
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
                    
                    dream_text = self.gemini_api.get_dream_sequence(
                        self.player_character,
                        self._get_recent_events_summary(),
                        self._get_objectives_summary(self.player_character),
                        relationships_summary 
                    )
                    self._print_color(f"{Colors.CYAN}Dream: \"{dream_text}\"{Colors.RESET}", Colors.CYAN)
                    self.player_character.add_journal_entry("Dream", dream_text, self._get_current_game_time_period_str())
                    self.player_character.add_player_memory(f"Had a disturbing dream: {dream_text[:50]}...")
                    if "terror" in dream_text.lower() or "blood" in dream_text.lower() or "axe" in dream_text.lower():
                        self.player_character.apparent_state = random.choice(["paranoid", "agitated", "haunted by dreams"])
                    elif "sonya" in dream_text.lower() or "hope" in dream_text.lower() or "cross" in dream_text.lower():
                        self.player_character.apparent_state = random.choice(["thoughtful", "remorseful", "hopeful"])
                    else:
                        self.player_character.apparent_state = "haunted by dreams"
                    self._print_color(f"(The dream leaves you feeling {self.player_character.apparent_state}.)", Colors.YELLOW)
                    self.last_significant_event_summary = "awoke troubled by a vivid dream."
                    self._print_color("", Colors.RESET) # Extra spacing

        self.time_since_last_npc_interaction += units
        self.time_since_last_npc_schedule_update += units

        if self.time_since_last_npc_schedule_update >= TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE:
            self.update_npc_locations_by_schedule()
            self.time_since_last_npc_schedule_update = 0
            
    def display_atmospheric_details(self):
        if self.player_character and self.current_location_name and self.gemini_api.model: # Check if model is configured
            details = self.gemini_api.get_atmospheric_details(
                self.player_character,
                self.current_location_name,
                self.get_current_time_period(),
                self.last_significant_event_summary,
                self._get_objectives_summary(self.player_character) 
            )
            if details and not details.startswith("(OOC:"):
                self._print_color(f"\n{details}", Colors.CYAN)
            self.last_significant_event_summary = None # Clear after showing


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
                # else:
                #     self._print_color(f"Warning: Location '{hidden_loc}' for hidden item '{item_name}' not found in LOCATIONS_DATA.", Colors.YELLOW)


    def load_all_characters(self, from_save=False):
        if from_save: return 

        self.all_character_objects = {}
        for name, data in CHARACTERS_DATA.items():
            static_data_copy = copy.deepcopy(data) 
            # Ensure default_location is in accessible_locations
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
                static_data_copy.get("schedule", {})
            )
        self.initialize_dynamic_location_items() 


    def select_player_character(self):
        self._print_color("\n--- Choose Your Character ---", Colors.CYAN + Colors.BOLD)
        playable_character_names = [name for name, data in CHARACTERS_DATA.items() if not data.get("non_playable", False)]
        if not playable_character_names:
            self._print_color("Error: No playable characters defined!", Colors.RED)
            return False

        for i, name in enumerate(playable_character_names):
            print(f"{Colors.MAGENTA}{i + 1}. {Colors.WHITE}{name}{Colors.RESET}")

        while True:
            try:
                choice_str = self._input_color("Enter the number of your choice: ", Colors.MAGENTA)
                if not choice_str: continue
                choice = int(choice_str) - 1
                if 0 <= choice < len(playable_character_names):
                    chosen_name = playable_character_names[choice]
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
                else:
                    self._print_color("Invalid choice. Please enter a number from the list.", Colors.RED)
            except ValueError:
                self._print_color("Invalid input. Please enter a number.", Colors.RED)

    def update_npc_locations_by_schedule(self):
        current_time_period = self.get_current_time_period()
        if current_time_period == "Unknown": return

        moved_npcs_info = []
        for npc_name, npc_obj in self.all_character_objects.items():
            if npc_obj.is_player or not npc_obj.schedule: continue
            
            scheduled_location = npc_obj.schedule.get(current_time_period)
            if scheduled_location and scheduled_location != npc_obj.current_location:
                if scheduled_location in LOCATIONS_DATA: # Check if the scheduled location actually exists
                    if scheduled_location in npc_obj.accessible_locations: # And if NPC can access it
                        if random.random() < NPC_MOVE_CHANCE:
                            old_location = npc_obj.current_location
                            npc_obj.current_location = scheduled_location
                            if old_location == self.current_location_name and scheduled_location != self.current_location_name:
                                moved_npcs_info.append(f"{npc_obj.name} has left.")
                            elif scheduled_location == self.current_location_name and old_location != self.current_location_name:
                                 moved_npcs_info.append(f"{npc_obj.name} has arrived.")
                    # else:
                        # self._print_color(f"Debug: {npc_name} cannot access scheduled location {scheduled_location}", Colors.DIM)
                # else:
                    # self._print_color(f"Debug: Scheduled location {scheduled_location} for {npc_name} does not exist.", Colors.DIM)

        if moved_npcs_info:
            self._print_color("\n(As time passes...)", Colors.MAGENTA)
            for info in moved_npcs_info:
                self._print_color(info, Colors.MAGENTA)
            self._print_color("", Colors.RESET) # Extra spacing
        self.update_npcs_in_current_location() 


    def update_current_location_details(self, from_explicit_look_cmd=False):
        if not self.current_location_name:
            self._print_color("Error: Current location not set.", Colors.RED)
            if self.player_character and self.player_character.current_location: self.current_location_name = self.player_character.current_location
            else: self._print_color("Critical Error: Cannot determine current location.", Colors.RED); return

        location_data = LOCATIONS_DATA.get(self.current_location_name)
        if not location_data:
            self._print_color(f"Error: Unknown location: {self.current_location_name}. Data missing.", Colors.RED); return

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
                if char_obj not in self.npcs_in_current_location:
                    self.npcs_in_current_location.append(char_obj)


    def get_relationship_text(self, score): 
        if score > 5: return "very positive"
        if score > 2: return "positive"
        if score < -5: return "very negative"
        if score < -2: return "negative"
        return "neutral"

    def check_conversation_conclusion(self, text):
        for phrase_regex in self.game_config.CONCLUDING_PHRASES: 
            if re.search(phrase_regex, text, re.IGNORECASE):
                return True
        return False

    def display_objectives(self):
        self._print_color("\n--- Your Objectives ---", Colors.CYAN + Colors.BOLD)
        if not self.player_character or not self.player_character.objectives:
            self._print_color("You have no specific objectives at the moment.", Colors.DIM)
            return

        active_objectives = [obj for obj in self.player_character.objectives if obj.get("active", False) and not obj.get("completed", False)]
        completed_objectives = [obj for obj in self.player_character.objectives if obj.get("completed", False)]

        if not active_objectives and not completed_objectives:
            self._print_color("You have no specific objectives at the moment.", Colors.DIM)
            return

        if active_objectives:
            self._print_color("\nOngoing:", Colors.YELLOW + Colors.BOLD)
            for obj in active_objectives:
                self._print_color(f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE)
                current_stage = self.player_character.get_current_stage_for_objective(obj.get('id'))
                if current_stage:
                    self._print_color(f"  Current Stage: {current_stage.get('description', 'No stage description')}", Colors.CYAN)
        else:
            self._print_color("\nNo active objectives right now.", Colors.DIM)

        if completed_objectives:
            self._print_color("\nCompleted:", Colors.GREEN + Colors.BOLD)
            for obj in completed_objectives:
                self._print_color(f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE)


    def display_help(self):
        self._print_color("\n--- Available Actions ---", Colors.CYAN + Colors.BOLD)
        self._print_color("", Colors.RESET) # Extra spacing before list
        actions = [
            ("look / l / examine / observe / look around", "Examine surroundings, see people, items, and exits."),
            ("look at [thing/person/scenery]", "Examine something specific more closely."),
            ("talk to [name]", "Speak with someone here."),
            ("move to [exit desc / location name]", "Change locations."),
            ("inventory / inv / i", "Check your possessions."),
            ("take [item name]", "Pick up an item from the location."),
            ("drop [item name]", "Leave an item from your inventory in the location."),
            ("use [item name]", "Attempt to use an item from your inventory (often on yourself)."),
            ("use [item name] on [target name/item]", "Use an item on something or someone specifically."),
            ("give [item name] to [target name]", "Offer an item to another character."),
            ("read [item name]", "Read a readable item like a letter or newspaper."),
            ("objectives / obj", "See your current goals."),
            ("think / reflect", "Access your character's inner thoughts."),
            ("wait", "Pass some time (may trigger dreams if troubled)."),
            ("journal / notes", "Review your journal entries (rumors, news, etc.)."),
            ("save", "Save your current game progress."),
            ("load", "Load a previously saved game."),
            ("help / commands", "Show this help message."),
            ("status / char / profile / st", "Display your character's current status."),
            ("quit / exit / q", "Exit the game.")
        ]
        for cmd, desc in actions:
            self._print_color(f"{cmd:<65} {Colors.WHITE}- {desc}{Colors.RESET}", Colors.MAGENTA)
        self._print_color("", Colors.RESET) # Extra spacing after list


    def parse_action(self, raw_input):
        action = raw_input.strip().lower()
        if not action: return None, None

        give_match = re.match(r"^(give|offer)\s+(.+?)\s+to\s+(.+)$", action)
        if give_match:
            item_name = give_match.group(2).strip()
            target_name = give_match.group(3).strip()
            return "use", (item_name, target_name, "give") 

        read_match = re.match(r"^(read|peruse)\s+(.+)$", action)
        if read_match:
            item_name = read_match.group(2).strip()
            return "use", (item_name, None, "read") 

        use_on_match = re.match(r"^(use|apply)\s+(.+?)\s+on\s+(.+)$", action)
        if use_on_match:
            item_name = use_on_match.group(2).strip()
            target_name = use_on_match.group(3).strip()
            return "use", (item_name, target_name, "use_on") 
            
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
                        parsed_arg = action[len(cmd_to_check):].strip()
        
        if matched_command:
            return matched_command, parsed_arg

        parts = action.split(" ", 1)
        
        # Persuade command: "persuade [target_npc_name] that/to [statement_text]"
        # Example: persuade Razumikhin that I need his help
        # Example: persuade Sonya to give me her cross
        persuade_match = re.match(r"^(persuade|convince|argue with)\s+(.+?)\s+(?:that|to)\s+(.+)$", action)
        if persuade_match:
            command = "persuade" # Normalize command
            target_npc_name = persuade_match.group(2).strip()
            statement_text = persuade_match.group(3).strip()
            return command, (target_npc_name, statement_text)

        return parts[0], parts[1] if len(parts) > 1 else None


    def save_game(self):
        if not self.player_character:
            self._print_color("Cannot save: Game not fully initialized.", Colors.RED)
            return
        game_state_data = {
            "player_character_name": self.player_character.name,
            "current_location_name": self.current_location_name,
            "game_time": self.game_time,
            "current_day": self.current_day,
            "all_character_objects_state": {name: char.to_dict() for name, char in self.all_character_objects.items()},
            "dynamic_location_items": self.dynamic_location_items,
            "triggered_events": list(self.event_manager.triggered_events),
            "last_significant_event_summary": self.last_significant_event_summary,
            "player_notoriety_level": self.player_notoriety_level,
            "known_facts_about_crime": self.known_facts_about_crime,
            "key_events_occurred": self.key_events_occurred,
            "current_location_description_shown_this_visit": self.current_location_description_shown_this_visit,
            "chosen_gemini_model": self.gemini_api.chosen_model_name 
        }
        try:
            with open(SAVE_GAME_FILE, 'w') as f:
                json.dump(game_state_data, f, indent=4)
            self._print_color(f"Game saved to {SAVE_GAME_FILE}", Colors.GREEN)
        except Exception as e:
            self._print_color(f"Error saving game: {e}", Colors.RED)

    def load_game(self):
        if not os.path.exists(SAVE_GAME_FILE):
            self._print_color("No save file found.", Colors.YELLOW)
            return False
        try:
            with open(SAVE_GAME_FILE, 'r') as f:
                game_state_data = json.load(f)

            self.game_time = game_state_data.get("game_time", 0)
            self.current_day = game_state_data.get("current_day", 1)
            self.current_location_name = game_state_data.get("current_location_name")
            self.dynamic_location_items = game_state_data.get("dynamic_location_items", {})
            self.event_manager.triggered_events = set(game_state_data.get("triggered_events", []))
            self.last_significant_event_summary = game_state_data.get("last_significant_event_summary")
            self.player_notoriety_level = game_state_data.get("player_notoriety_level", 0)
            self.known_facts_about_crime = game_state_data.get("known_facts_about_crime", ["An old pawnbroker and her sister were murdered recently."])
            self.key_events_occurred = game_state_data.get("key_events_occurred", ["Game loaded."])
            self.current_location_description_shown_this_visit = game_state_data.get("current_location_description_shown_this_visit", False)
            
            saved_model_name = game_state_data.get("chosen_gemini_model")
            if saved_model_name:
                self.gemini_api.chosen_model_name = saved_model_name
                self._print_color(f"Loaded preferred Gemini model: {saved_model_name}", Colors.DIM)

            self.all_character_objects = {} 
            saved_char_states = game_state_data.get("all_character_objects_state", {})
            for char_name, char_state_data in saved_char_states.items():
                static_data = CHARACTERS_DATA.get(char_name) 
                if not static_data:
                    self._print_color(f"Warning: Character '{char_name}' from save file not found in current CHARACTERS_DATA. Skipping.", Colors.YELLOW)
                    continue
                self.all_character_objects[char_name] = Character.from_dict(char_state_data, static_data)

            player_name = game_state_data.get("player_character_name")
            if player_name and player_name in self.all_character_objects:
                self.player_character = self.all_character_objects[player_name]
                self.player_character.is_player = True 
            else:
                self._print_color(f"Error: Saved player character '{player_name}' not found or invalid. Load failed.", Colors.RED)
                self.player_character = None; return False 

            if not self.current_location_name and self.player_character: self.current_location_name = self.player_character.current_location
            if not self.dynamic_location_items: self.initialize_dynamic_location_items() 
            
            self.update_npcs_in_current_location() 
            self._print_color("Game loaded successfully.", Colors.GREEN)
            self.update_current_location_details(from_explicit_look_cmd=False) 
            return True
        except Exception as e:
            self._print_color(f"Error loading game: {e}", Colors.RED)
            self.player_character = None; return False

    def handle_use_item(self, item_name_input, target_name_input=None, interaction_type="use_self_implicit"):
        if not self.player_character:
            self._print_color("Cannot use items: Player character not set.", Colors.RED)
            return False

        item_to_use_name = None
        if item_name_input:
            for inv_item_obj in self.player_character.inventory:
                if inv_item_obj["name"].lower().startswith(item_name_input.lower()):
                    item_to_use_name = inv_item_obj["name"]; break
            if not item_to_use_name: 
                if self.player_character.has_item(item_name_input): 
                    item_to_use_name = item_name_input
                else:
                    self._print_color(f"You don't have '{item_name_input}' to {interaction_type.replace('_', ' ')}.", Colors.RED)
                    return False
        elif interaction_type != "use_self_implicit": 
             self._print_color(f"What do you want to {interaction_type.replace('_', ' ')}{(' on ' + target_name_input) if target_name_input else ''}?", Colors.RED)
             return False
        
        if not item_to_use_name : 
            self._print_color("You need to specify an item to use or read.", Colors.RED)
            return False

        item_props = DEFAULT_ITEMS.get(item_to_use_name, {})
        item_obj_in_inventory = next((item for item in self.player_character.inventory if item["name"] == item_to_use_name), None)
        used_successfully = False
        effect_key = item_props.get("use_effect_player")

        if interaction_type == "read":
            if not item_props.get("readable"):
                self._print_color(f"You can't read the {item_to_use_name}.", Colors.YELLOW)
                return False
            if item_to_use_name == "old newspaper" or item_to_use_name == "Fresh Newspaper":
                effect_key = "read_evolving_news_article" 
            elif item_to_use_name == "mother's letter":
                effect_key = "reread_letter_and_feel_familial_pressure"
            elif item_to_use_name == "Sonya's New Testament":
                effect_key = "read_testament_for_solace_or_guilt"
            elif item_to_use_name == "Anonymous Note": # This is a specific item for AI content
                effect_key = "read_generated_document" 
                if item_obj_in_inventory and "generated_content" in item_obj_in_inventory:
                    self._print_color(f"You read the {item_to_use_name}:", Colors.WHITE)
                    self._print_color(f"\"{item_obj_in_inventory['generated_content']}\"", Colors.CYAN)
                    self.player_character.add_journal_entry("Note", item_obj_in_inventory['generated_content'], self._get_current_game_time_period_str())
                    self.last_significant_event_summary = f"read an {item_to_use_name}."
                    used_successfully = True
                    if "watch" in item_obj_in_inventory['generated_content'].lower() or "know" in item_obj_in_inventory['generated_content'].lower():
                        self.player_character.apparent_state = "paranoid"
                    return True 
                else: 
                    self._print_color(f"The {item_to_use_name} seems to be blank or unreadable.", Colors.RED)
                    return False
            elif item_to_use_name == "IOU Slip": # New readable item
                 if item_obj_in_inventory and item_obj_in_inventory.get("content"):
                    self._print_color(f"You examine the {item_to_use_name}: \"{item_obj_in_inventory['content']}\"", Colors.YELLOW)
                 else:
                    self._print_color(f"You look at the {item_to_use_name}. It's a formal-looking slip of paper.", Colors.YELLOW)
                 self.last_significant_event_summary = f"read an {item_to_use_name}."
                 used_successfully = True
                 return True # Handled
            elif item_to_use_name == "Student's Dog-eared Book":
                # For a book, we might want a more dynamic description from Gemini if it doesn't have fixed content
                book_reflection = self.gemini_api.get_item_interaction_description(
                    self.player_character, item_to_use_name, item_props, "read",
                    self.current_location_name, self.get_current_time_period()
                )
                self._print_color(f"You open the {item_to_use_name}. {book_reflection}", Colors.YELLOW)
                self.last_significant_event_summary = f"read from a {item_to_use_name}."
                used_successfully = True
                return True # Handled

        
        if effect_key == "comfort_self_if_ill" and item_to_use_name == "tattered handkerchief":
            if self.player_character.apparent_state in ["feverish", "coughing", "ill", "haunted by dreams"]:
                self._print_color(f"You press the {item_to_use_name} to your brow. It offers little physical comfort, but it's something to cling to.", Colors.YELLOW)
                if self.player_character.apparent_state == "feverish" and random.random() < 0.2:
                    self.player_character.apparent_state = "less feverish"
                    self._print_color("The coolness, imagined or real, seems to lessen the fever's grip for a moment.", Colors.CYAN)
                self.last_significant_event_summary = f"used a {item_to_use_name} while feeling unwell."
                used_successfully = True
            else: self._print_color(f"You look at the {item_to_use_name}. It seems rather pointless to use it now.", Colors.YELLOW)

        elif effect_key == "examine_bottle_for_residue" and item_to_use_name == "dusty bottle":
            self._print_color(f"You peer into the {item_to_use_name}. A faint, stale smell of cheap spirits lingers. It's long empty.", Colors.YELLOW)
            self.last_significant_event_summary = f"examined a {item_to_use_name}."
            used_successfully = True
        
        elif effect_key == "read_evolving_news_article" and (item_to_use_name == "old newspaper" or item_to_use_name == "Fresh Newspaper"):
            self._print_color(f"You smooth out the creases of the {item_to_use_name} and scan the faded print.", Colors.WHITE)
            article_snippet = self.gemini_api.get_newspaper_article_snippet(
                self.current_day,
                self._get_recent_events_summary(),
                self._get_objectives_summary(self.player_character),
                self.player_character.apparent_state 
            )
            if article_snippet and not article_snippet.startswith("(OOC:"):
                self._print_color(f"An article catches your eye: \"{article_snippet}\"", Colors.YELLOW)
                self.player_character.add_journal_entry("News", article_snippet, self._get_current_game_time_period_str())
                if "crime" in article_snippet.lower() or "investigation" in article_snippet.lower() or "murder" in article_snippet.lower():
                    self.player_character.apparent_state = "thoughtful"
                    if self.player_character.name == "Rodion Raskolnikov":
                        self.player_character.add_player_memory("Read unsettling news about the recent crime.")
                        self.player_notoriety_level = min(self.player_notoriety_level + 0.1, 3) 
                self.last_significant_event_summary = f"read an {item_to_use_name}."
            else:
                self._print_color("The print is too faded or the news too mundane to hold your interest.", Colors.DIM)
            used_successfully = True

        elif effect_key == "grip_axe_and_reminisce_horror" and item_to_use_name == "Raskolnikov's axe":
            if self.player_character.name == "Rodion Raskolnikov":
                self._print_color(f"You grip the {item_to_use_name}. Its cold weight is a familiar dread. The memories, sharp and bloody, flood your mind. You feel a wave of nausea, then a chilling resolve, then utter despair.", Colors.RED + Colors.BOLD)
                self.player_character.apparent_state = random.choice(["dangerously agitated", "remorseful", "paranoid"])
                self.last_significant_event_summary = f"held the axe, tormented by memories."
                used_successfully = True
            else: self._print_color(f"You look at the {item_to_use_name}. It's a grim object, heavy and unsettling. Best left alone.", Colors.YELLOW); used_successfully = True
        
        elif effect_key == "read_testament_for_solace_or_guilt" and item_to_use_name == "Sonya's New Testament":
            self._print_color(f"You open {item_to_use_name}. The familiar words of the Gospels seem to both accuse and offer a sliver of hope.", Colors.GREEN)
            reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, self.get_current_time_period(), f"reading from {item_to_use_name}, pondering Lazarus, guilt, and salvation")
            self._print_color(f"\"{reflection}\"", Colors.CYAN)
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.apparent_state = random.choice(["contemplative", "remorseful", "thoughtful", "hopeful"])
                self.player_character.add_player_memory("Read from the New Testament, stirring deep thoughts of salvation and suffering.")
            self.last_significant_event_summary = f"read from {item_to_use_name}."
            used_successfully = True

        elif effect_key == "reflect_on_faith_and_redemption" and item_to_use_name == "Sonya's Cypress Cross":
             if self.player_character.name == "Rodion Raskolnikov": 
                self._print_color("You clutch the small cypress cross. It feels strangely significant in your hand, a stark contrast to the turmoil within you.", Colors.GREEN)
                self.player_character.apparent_state = random.choice(["remorseful", "contemplative", "hopeful"])
                self.last_significant_event_summary = f"held Sonya's cross, feeling its weight and Sonya's sacrifice."
                reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, self.get_current_time_period(), "Holding Sonya's cross, new thoughts about suffering and sacrifice surface.")
                self._print_color(f"\"{reflection}\"", Colors.CYAN)
                used_successfully = True
             else: self._print_color(f"You examine {item_to_use_name}. It seems to be a simple wooden cross, yet it emanates a certain potent feeling.", Colors.YELLOW); used_successfully = True

        elif effect_key == "examine_rag_and_spiral_into_paranoia" and item_to_use_name == "bloodied rag":
            self._print_color(f"You stare at the {item_to_use_name}. The dark stains seem to shift and spread before your eyes. Every sound, every shadow, feels like an accusation.", Colors.RED)
            self.player_character.apparent_state = "paranoid"
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.add_player_memory("The sight of the bloodied rag brought a fresh wave of paranoia.")
                self.player_notoriety_level = min(self.player_notoriety_level + 0.5, 3) 
            self.last_significant_event_summary = f"was deeply disturbed by a {item_to_use_name}."
            used_successfully = True
        
        elif effect_key == "reread_letter_and_feel_familial_pressure" and item_to_use_name == "mother's letter":
            self._print_color(f"You re-read your mother's letter. Her words of love and anxiety, Dunya's predicament... it all weighs heavily on you.", Colors.YELLOW)
            reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, self.get_current_time_period(), "re-reading mother's letter about Dunya and Luzhin, feeling guilt and responsibility")
            self._print_color(f"\"{reflection}\"", Colors.CYAN)
            self.player_character.apparent_state = random.choice(["burdened", "agitated", "resolved"])
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.add_player_memory("Re-reading mother's letter intensified feelings of duty and distress.")
            self.last_significant_event_summary = f"re-read the {item_to_use_name}."
            used_successfully = True

        elif effect_key == "drink_vodka_for_oblivion" and item_to_use_name == "cheap vodka":
            self._print_color(f"You take a long swig of the harsh vodka. It burns on the way down, offering a brief, false warmth and a dulling of the senses.", Colors.MAGENTA)
            self.player_character.apparent_state = "slightly drunk"
            if self.player_character.has_item("cheap vodka"):
                self.player_character.remove_from_inventory("cheap vodka", 1) 
            else: 
                self._print_color("Odd, the bottle seems to have vanished before you could drink it all.", Colors.DIM)
            self.last_significant_event_summary = "drank some cheap vodka to numb the thoughts."
            if self.player_character.apparent_state == "feverish":
                self.player_character.apparent_state = "agitated"; self._print_color("The vodka clashes terribly with your fever, making you feel worse.", Colors.RED)
            used_successfully = True
        
        elif effect_key == "examine_bundle_and_face_guilt_for_Lizaveta" and item_to_use_name == "Lizaveta's bundle":
            self._print_color(f"You hesitantly open {item_to_use_name}. Inside are a few pitiful belongings: a worn shawl, a child's small wooden toy, a copper coin... The sight is a fresh stab of guilt for the gentle Lizaveta.", Colors.YELLOW)
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.apparent_state = "remorseful"
                self.player_character.add_player_memory("Examined Lizaveta's bundle; the innocence of the items was a heavy burden.")
            self.last_significant_event_summary = f"examined Lizaveta's bundle, increasing the weight of guilt."
            used_successfully = True
        
        elif effect_key == "eat_bread_for_sustenance" and item_to_use_name == "Loaf of Black Bread":
            self._print_color(f"You tear off a piece of the dense {item_to_use_name}. It's coarse, but fills your stomach somewhat.", Colors.YELLOW)
            if self.player_character.apparent_state in ["burdened", "feverish", "despondent"]:
                self.player_character.apparent_state = "normal" # Or some other less severe state
                self._print_color("The bread provides a moment of simple relief.", Colors.CYAN)
            self.last_significant_event_summary = f"ate some {item_to_use_name}."
            used_successfully = True # This item should be consumable
        
        elif effect_key == "contemplate_icon" and item_to_use_name == "Small, Tarnished Icon":
            icon_reflection = self.gemini_api.get_item_interaction_description(
                self.player_character, item_to_use_name, item_props, "contemplate",
                self.current_location_name, self.get_current_time_period()
            )
            self._print_color(f"You gaze at the {item_to_use_name}. {icon_reflection}", Colors.YELLOW)
            self.last_significant_event_summary = f"contemplated a {item_to_use_name}."
            used_successfully = True


        elif item_to_use_name == "worn coin" and interaction_type == "give" and target_name_input:
            target_npc = next((npc for npc in self.npcs_in_current_location if npc.name.lower().startswith(target_name_input.lower())), None)
            if target_npc:
                if self.player_character.remove_from_inventory("worn coin", 1):
                    self._print_color(f"You offer a coin to {target_npc.name}.", Colors.WHITE)
                    relationship_text = self.get_relationship_text(target_npc.relationship_with_player)
                    reaction = self.gemini_api.get_npc_dialogue(
                        target_npc, self.player_character, 
                        f"(Offers a coin out of {random.choice(['pity', 'a sudden impulse', 'a desire to help', 'unease'])}.)", 
                        self.current_location_name, 
                        self.get_current_time_period(), 
                        relationship_text, 
                        target_npc.get_player_memory_summary(), 
                        self.player_character.apparent_state, 
                        self.player_character.get_notable_carried_items_summary(),
                        self._get_recent_events_summary(),
                        self._get_objectives_summary(target_npc),
                        self._get_objectives_summary(self.player_character)
                    )
                    self._print_color(f"{target_npc.name}: \"{reaction}\"", Colors.YELLOW)
                    target_npc.relationship_with_player += 1 
                    self.last_significant_event_summary = f"gave a coin to {target_npc.name}."
                    used_successfully = True
                else: self._print_color("You rummage through your pockets but find no coins to give.", Colors.RED)
            else: self._print_color(f"You don't see '{target_name_input}' here to give a coin to.", Colors.RED)

        if not used_successfully:
            # Check if it was a read attempt that didn't have a specific handler yet
            if interaction_type == "read" and item_props.get("readable"):
                 # Generic read for items without specific effect_key for reading
                read_reflection = self.gemini_api.get_item_interaction_description(
                    self.player_character, item_to_use_name, item_props, "read",
                    self.current_location_name, self.get_current_time_period()
                )
                self._print_color(f"You read the {item_to_use_name}. {read_reflection}", Colors.YELLOW)
                self.last_significant_event_summary = f"read the {item_to_use_name}."
                used_successfully = True # Count as used even if generic
            elif target_name_input and interaction_type != "give": 
                self._print_color(f"You try to use the {item_to_use_name} on {target_name_input}, but nothing specific happens.", Colors.YELLOW)
            elif interaction_type != "give": 
                self._print_color(f"You contemplate the {item_to_use_name}, but don't find a specific use for it right now.", Colors.YELLOW)
            
            if not used_successfully: return False # Return false if nothing happened

        if used_successfully and item_props.get("consumable", False) and item_to_use_name != "cheap vodka": 
            if self.player_character.remove_from_inventory(item_to_use_name, 1):
                self._print_color(f"The {item_to_use_name} is used up.", Colors.MAGENTA)
        return True
    
    # --- Main Game Loop Helper Methods ---
    def _initialize_game(self):
        """Handles the initial setup of the game, either loading or starting anew."""
        self.gemini_api.configure(self._print_color, self._input_color)
        self._print_color("\n--- Crime and Punishment: A Text Adventure ---", Colors.CYAN + Colors.BOLD)
        self._print_color("Type 'load' to load a saved game, or press Enter to start a new game.", Colors.MAGENTA)
        initial_action = self._input_color(f"{self.game_config.PROMPT_ARROW}", Colors.WHITE).strip().lower()

        game_loaded_successfully = False
        if initial_action == "load":
            if self.load_game():
                game_loaded_successfully = True
            else:
                self._print_color("Failed to load game. Starting a new game instead.", Colors.YELLOW)
        
        if not game_loaded_successfully:
            self.load_all_characters()
            if not self.select_player_character():
                self._print_color("Critical Error: Could not initialize player character. Exiting.", Colors.RED)
                return False # Indicate failure
        
        if not self.player_character or not self.current_location_name:
            self._print_color("Game initialization failed critically. Exiting.", Colors.RED)
            return False # Indicate failure

        if not game_loaded_successfully:
            self.update_current_location_details(from_explicit_look_cmd=False)
            self.display_atmospheric_details()
        
        self._print_color("\n--- Game Start ---", Colors.CYAN + Colors.BOLD)
        if not game_loaded_successfully:
            self.display_help()
        return True # Indicate success

    def _handle_ambient_rumors(self):
        """Checks for and displays ambient rumors if conditions are met."""
        if self.gemini_api.model and \
           self.current_location_name in ["Haymarket Square", "Tavern", "Squalid St. Petersburg Street"] and \
           random.random() < AMBIENT_RUMOR_CHANCE_PUBLIC_PLACE:
            
            source_npc = random.choice(self.npcs_in_current_location) if self.npcs_in_current_location \
                         else Character("A Passerby", "A typical St. Petersburg citizen.", "", self.current_location_name, [])
            
            relationship_score_for_rumor = 0
            if source_npc.name != "A Passerby" and hasattr(source_npc, 'relationship_with_player'):
                relationship_score_for_rumor = source_npc.relationship_with_player

            rumor_text = self.gemini_api.get_rumor_or_gossip(
                source_npc, self.current_location_name, self.get_current_time_period(),
                self._get_known_facts_summary(), self.player_notoriety_level,
                self.get_relationship_text(relationship_score_for_rumor),
                self._get_objectives_summary(source_npc)
            )
            if rumor_text and not rumor_text.startswith("(OOC:"):
                self._print_color(f"\n{Colors.DIM}(You overhear some chatter nearby: \"{rumor_text}\"){Colors.RESET}", Colors.DIM)
                self._print_color("", Colors.RESET) # Extra spacing
                if self.player_character: # Ensure player_character exists
                    self.player_character.add_journal_entry("Overheard Rumor", rumor_text, self._get_current_game_time_period_str())
                    if self.player_character.name == "Rodion Raskolnikov" and \
                       any(kw in rumor_text.lower() for kw in ["student", "axe", "pawnbroker", "murder", "police"]):
                        self.player_character.apparent_state = "paranoid"
                        self.player_notoriety_level = min(self.player_notoriety_level + 0.2, 3)

    def _get_player_input(self):
        """Gets and parses the player's raw input."""
        player_state_info = f"{self.player_character.apparent_state}" if self.player_character else "Unknown state"

        prompt_hint_objects = [] # Stores dicts: {'action_type': str, 'target': str, 'display_string': str}
        hint_types_added = set() # Stores more specific types like 'talk', 'item_take', 'item_examine', 'move'

        if hasattr(self, 'numbered_actions_context') and self.numbered_actions_context:
            # 1. Talk Hint
            if 'talk' not in hint_types_added and len(prompt_hint_objects) < 2:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'talk':
                        current_action_type = 'talk'
                        current_target = action_info['target']
                        display_string = f"Talk to {current_target}"

                        is_duplicate = False
                        for existing_hint in prompt_hint_objects:
                            if existing_hint['action_type'] == current_action_type and \
                               (existing_hint['target'].startswith(current_target) or current_target.startswith(existing_hint['target'])):
                                is_duplicate = True; break
                        if not is_duplicate:
                            prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string})
                            hint_types_added.add('talk')
                            break # Found one talk hint, move to next category if needed by outer logic

            # 2. Notable Item Hints (Take then Examine)
            if len(prompt_hint_objects) < 2 and 'item_take' not in hint_types_added:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'take' and self.game_config.DEFAULT_ITEMS.get(action_info['target'], {}).get('is_notable', False):
                        current_action_type = 'item_take'
                        current_target = action_info['target']
                        display_string = f"Take {current_target}"

                        is_duplicate = False
                        for existing_hint in prompt_hint_objects:
                            if existing_hint['action_type'] == current_action_type and \
                               (existing_hint['target'].startswith(current_target) or current_target.startswith(existing_hint['target'])):
                                is_duplicate = True; break
                        if not is_duplicate:
                            prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string})
                            hint_types_added.add('item_take')
                            break

            if len(prompt_hint_objects) < 2 and 'item_examine' not in hint_types_added:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'look_at_item' and self.game_config.DEFAULT_ITEMS.get(action_info['target'], {}).get('is_notable', False):
                        current_action_type = 'item_examine'
                        current_target = action_info['target']
                        display_string = f"Examine {current_target}"

                        is_duplicate = False
                        for existing_hint in prompt_hint_objects:
                            if existing_hint['action_type'] == current_action_type and \
                               (existing_hint['target'].startswith(current_target) or current_target.startswith(existing_hint['target'])):
                                is_duplicate = True; break
                        if not is_duplicate:
                            prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string})
                            hint_types_added.add('item_examine')
                            break

            # 3. Generic Item Hints (Take then Examine, if space and specific type not added)
            if len(prompt_hint_objects) < 2 and 'item_take' not in hint_types_added :
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'take': # No notable check here
                        current_action_type = 'item_take'
                        current_target = action_info['target']
                        display_string = f"Take {current_target}"

                        is_duplicate = False
                        for existing_hint in prompt_hint_objects:
                            if existing_hint['action_type'] == current_action_type and \
                               (existing_hint['target'].startswith(current_target) or current_target.startswith(existing_hint['target'])):
                                is_duplicate = True; break
                        if not is_duplicate:
                            prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string})
                            hint_types_added.add('item_take')
                            break

            if len(prompt_hint_objects) < 2 and 'item_examine' not in hint_types_added:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'look_at_item': # No notable check here
                        current_action_type = 'item_examine'
                        current_target = action_info['target']
                        display_string = f"Examine {current_target}"

                        is_duplicate = False
                        for existing_hint in prompt_hint_objects:
                            if existing_hint['action_type'] == current_action_type and \
                               (existing_hint['target'].startswith(current_target) or current_target.startswith(existing_hint['target'])):
                                is_duplicate = True; break
                        if not is_duplicate:
                            prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string})
                            hint_types_added.add('item_examine')
                            break

            # 4. Move Hint
            if 'move' not in hint_types_added and len(prompt_hint_objects) < 2:
                for action_info in self.numbered_actions_context:
                    if len(prompt_hint_objects) >= 2: break
                    if action_info['type'] == 'move':
                        current_action_type = 'move'
                        current_target = action_info['target'] # This is the location name
                        display_string = f"Go to {current_target}"

                        is_duplicate = False
                        for existing_hint in prompt_hint_objects:
                            if existing_hint['action_type'] == current_action_type and \
                               (existing_hint['target'].startswith(current_target) or current_target.startswith(existing_hint['target'])):
                                is_duplicate = True; break
                        if not is_duplicate:
                            prompt_hint_objects.append({'action_type': current_action_type, 'target': current_target, 'display_string': display_string})
                            hint_types_added.add('move')
                            break

        active_hint_display_strings = [h['display_string'] for h in prompt_hint_objects[:2]]
        hint_string = ""
        if active_hint_display_strings:
            hint_string = f" (Hint: {Colors.DIM}{' | '.join(active_hint_display_strings)}{Colors.RESET})"
        elif not (hasattr(self, 'numbered_actions_context') and self.numbered_actions_context): # Default hint if no actions context at all
            hint_string = f" (Hint: {Colors.DIM}type 'look' or 'help'{Colors.RESET})"

        time_info = self._get_current_game_time_period_str()
        prompt_text = f"\n[{Colors.DIM}{time_info}{Colors.RESET} | {Colors.CYAN}{self.current_location_name}{Colors.RESET} ({player_state_info})]{hint_string} What do you do? {self.game_config.PROMPT_ARROW}"
        raw_action_input = self._input_color(prompt_text, Colors.WHITE)

        try:
            action_number = int(raw_action_input)
            if 1 <= action_number <= len(self.numbered_actions_context):
                action_info = self.numbered_actions_context[action_number - 1]
                action_type = action_info['type']
                target = action_info['target']

                if action_type == 'move':
                    return 'move to', target
                elif action_type == 'talk':
                    return 'talk to', target
                elif action_type == 'take':
                    return 'take', target
                elif action_type == 'look_at_item':
                    return 'look', target
                elif action_type == 'look_at_npc':
                    return 'look', target
                # Add other action types if needed
            else:
                # Number out of range, treat as normal command
                return self.parse_action(raw_action_input)
        except ValueError:
            # Not a number, parse as normal command
            return self.parse_action(raw_action_input)

    def _process_command(self, command, argument):
        """Processes the parsed command and returns turn flags."""
        action_taken_this_turn = True
        time_to_advance = TIME_UNITS_PER_PLAYER_ACTION
        show_atmospherics_this_turn = True

        if command == "quit":
            self._print_color("Exiting game. Goodbye.", Colors.MAGENTA)
            return False, False, 0, True # quit_game = True

        elif command == "save":
            self.save_game()
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "load":
            if self.load_game():
                show_atmospherics_this_turn = True
            else:
                show_atmospherics_this_turn = False # Failed load shouldn't show new atmospherics
            action_taken_this_turn = False
            # Special case for load: it breaks the flow of the current turn by reloading state
            return action_taken_this_turn, show_atmospherics_this_turn, 0, "load_triggered"
        elif command == "help":
            self.display_help()
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "journal":
            if self.player_character:
                self._print_color(self.player_character.get_journal_summary(), Colors.CYAN)
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "look":
            self._handle_look_command(argument)
            # _handle_look_command sets its own atmospherics and action flags internally for now
            # action_taken_this_turn and show_atmospherics_this_turn are handled by it
        elif command == "inventory":
            self._handle_inventory_command()
            action_taken_this_turn = False # Viewing inventory doesn't take game time
            show_atmospherics_this_turn = False
        elif command == "take":
            action_taken_this_turn, show_atmospherics_this_turn = self._handle_take_command(argument)
        elif command == "drop":
            action_taken_this_turn, show_atmospherics_this_turn = self._handle_drop_command(argument)
        elif command == "use":
            action_taken_this_turn = self._handle_use_command(argument)
            show_atmospherics_this_turn = True # Usually show atmospherics after using an item
        elif command == "objectives":
            self.display_objectives()
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        elif command == "think":
            self._handle_think_command()
            show_atmospherics_this_turn = True
        elif command == "wait":
            time_to_advance = self._handle_wait_command()
            show_atmospherics_this_turn = True
        elif command == "talk to":
            action_taken_this_turn, show_atmospherics_this_turn = self._handle_talk_to_command(argument)
            # Time is advanced within _handle_talk_to_command
        elif command == "move to":
            action_taken_this_turn, show_atmospherics_this_turn = self._handle_move_to_command(argument)
        elif command == "persuade": # New command
            action_taken_this_turn, show_atmospherics_this_turn = self._handle_persuade_command(argument)
        elif command == "status":
            self._handle_status_command()
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        else:
            self._print_color(f"Unknown command: '{command}'. Type 'help' for a list of actions.", Colors.RED)
            action_taken_this_turn = False
            show_atmospherics_this_turn = False
        
        return action_taken_this_turn, show_atmospherics_this_turn, time_to_advance, False

    def _update_world_state_after_action(self, command, action_taken_this_turn, time_to_advance):
        """Updates game time, events, and NPC interactions after a player action."""
        if action_taken_this_turn:
            if command != "talk to": # Time advancement for 'talk to' is handled within its own method
                self.advance_time(time_to_advance)
            
            event_triggered = self.event_manager.check_and_trigger_events()
            if event_triggered and self.last_significant_event_summary and \
               self.last_significant_event_summary not in self.key_events_occurred[-3:]:
                self.key_events_occurred.append(self.last_significant_event_summary)
                if len(self.key_events_occurred) > 10:
                    self.key_events_occurred.pop(0)

            if self.gemini_api.model and command != "talk to" and \
               self.time_since_last_npc_interaction >= TIME_UNITS_FOR_NPC_INTERACTION_CHANCE:
                if len(self.npcs_in_current_location) >= 2 and random.random() < NPC_INTERACTION_CHANCE:
                    if self.event_manager.attempt_npc_npc_interaction():
                        self.last_significant_event_summary = "overheard an exchange between NPCs."
                self.time_since_last_npc_interaction = 0
    
    def _display_turn_feedback(self, show_atmospherics_this_turn, command):
        """Displays atmospheric details or other feedback at the end of a turn."""
        if show_atmospherics_this_turn:
            self.display_atmospheric_details()
        elif command == "load": # Clear summary if loading, as it's from a past state
            self.last_significant_event_summary = None

    def _check_game_ending_conditions(self):
        """Checks if any game ending conditions are met."""
        if self.player_character and self.player_character.name == "Rodion Raskolnikov":
            obj_grapple = self.player_character.get_objective_by_id("grapple_with_crime")
            if obj_grapple and obj_grapple.get("completed", False):
                current_stage = self.player_character.get_current_stage_for_objective("grapple_with_crime")
                if current_stage and current_stage.get("is_ending_stage"):
                    self._print_color(f"\n--- The story of {self.player_character.name} has reached a conclusion ({current_stage.get('description', 'an end')}) ---", Colors.CYAN + Colors.BOLD)
                    return True # Game should end
        return False

    def run(self):
        if not self._initialize_game():
            return # Initialization failed

        while True:
            if not LOCATIONS_DATA.get(self.current_location_name):
                 self._print_color(f"Critical Error: Current location '{self.current_location_name}' data not found. Exiting.", Colors.RED)
                 break

            self._handle_ambient_rumors()
            command, argument = self._get_player_input()

            if command is None and argument is None: # Handle empty input
                continue

            action_taken, show_atmospherics, time_units, special_flag = self._process_command(command, argument)
            
            if special_flag == "load_triggered": # If load command was processed
                continue # Restart loop to reflect new state immediately

            if special_flag: # For quit
                break

            self._update_world_state_after_action(command, action_taken, time_units)
            self._display_turn_feedback(show_atmospherics, command)

            if self._check_game_ending_conditions():
                break
    
    # --- Command Handler Methods ---
    def _handle_look_command(self, argument):
        """Handles the 'look' command and its variations."""
        self.numbered_actions_context.clear()
        action_number = 1

        current_location_data = LOCATIONS_DATA.get(self.current_location_name)
        is_general_look = (argument is None or argument.lower() in ["around", ""])
        self.update_current_location_details(from_explicit_look_cmd=is_general_look)
        
        if argument and not is_general_look:
            target_to_look_at = argument.lower()
            found_target = False
            # Look at item in location
            for item_info in self.dynamic_location_items.get(self.current_location_name, []):
                if item_info["name"].lower().startswith(target_to_look_at):
                    item_default = DEFAULT_ITEMS.get(item_info["name"])
                    base_desc_for_skill_check = "An ordinary item." # Default
                    if item_default:
                        self._print_color(f"You examine the {item_info['name']}:", Colors.GREEN)
                        gen_desc = None
                        if self.gemini_api.model:
                            gen_desc = self.gemini_api.get_item_interaction_description(
                                self.player_character, item_info['name'], item_default,
                                "examine closely in environment", self.current_location_name,
                                self.get_current_time_period())
                            self._print_color(f"\"{gen_desc}\"", Colors.GREEN if not gen_desc.startswith("(OOC:") else Colors.YELLOW)
                            base_desc_for_skill_check = gen_desc if not gen_desc.startswith("(OOC:") else item_default.get('description', base_desc_for_skill_check)
                        else:
                            base_desc_for_skill_check = item_default.get('description', base_desc_for_skill_check)
                            self._print_color(f"({base_desc_for_skill_check})", Colors.DIM)

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
                            for prop_str in properties_to_display:
                                self._print_color(f"- {prop_str}", Colors.BLUE)
                            self._print_color("", Colors.RESET) # Spacing after properties
                        
                        if self.player_character.check_skill("Observation", 1):
                            self._print_color("(Your keen eye picks up on finer details...)", Colors.CYAN + Colors.DIM)
                            observation_context = f"Player ({self.player_character.name}) succeeded an Observation skill check examining the {item_info['name']} in {self.current_location_name}. What subtle detail, past use, hidden inscription, or unusual characteristic do they notice that isn't immediately obvious?"
                            detailed_observation = self.gemini_api.get_enhanced_observation(
                                self.player_character,
                                target_name=item_info['name'],
                                target_category="item",
                                base_description=base_desc_for_skill_check,
                                skill_check_context=observation_context
                            )
                            if detailed_observation and not detailed_observation.startswith("(OOC:"):
                                self._print_color(f"Detail: \"{detailed_observation}\"", Colors.GREEN)

                            # NPC memory for observing player looking at specific items (from location)
                            sensitive_items_for_observation = {
                                "Raskolnikov's axe": {"sentiment": -2, "observer_specific": {"Porfiry Petrovich": -3}},
                                "bloodied rag": {"sentiment": -2, "observer_specific": {"Porfiry Petrovich": -2, "Sonya Marmeladova": -1}},
                                "Lizaveta's bundle": {"sentiment": -1, "observer_specific": {"Sonya Marmeladova": -2}}
                            }
                            if item_info["name"] in sensitive_items_for_observation:
                                item_sensitivity_data = sensitive_items_for_observation[item_info["name"]]
                                for npc_observer in self.npcs_in_current_location:
                                    if npc_observer.name != self.player_character.name:
                                        base_sentiment = item_sensitivity_data["sentiment"]
                                        observer_specific_sentiment = item_sensitivity_data.get("observer_specific", {}).get(npc_observer.name)
                                        final_sentiment = observer_specific_sentiment if observer_specific_sentiment is not None else base_sentiment
                                        npc_observer.add_player_memory(
                                            memory_type="player_action_observed",
                                            turn=self.game_time,
                                            content={
                                                "action": f"examined_item_in_location",
                                                "item_name": item_info["name"],
                                                "location": self.current_location_name
                                            },
                                            sentiment_impact=final_sentiment
                                        )
                        found_target = True; break
            # Look at item in inventory
            if not found_target and self.player_character:
                for inv_item_info in self.player_character.inventory:
                    if inv_item_info["name"].lower().startswith(target_to_look_at):
                        item_default = DEFAULT_ITEMS.get(inv_item_info["name"])
                        base_desc_for_skill_check = "An ordinary item."
                        if item_default:
                            self._print_color(f"You examine your {inv_item_info['name']}:", Colors.GREEN)
                            gen_desc = None
                            if self.gemini_api.model:
                                gen_desc = self.gemini_api.get_item_interaction_description(
                                    self.player_character, inv_item_info['name'], item_default,
                                    "examine closely from inventory", self.current_location_name,
                                    self.get_current_time_period())
                                self._print_color(f"\"{gen_desc}\"", Colors.GREEN if not gen_desc.startswith("(OOC:") else Colors.YELLOW)
                                base_desc_for_skill_check = gen_desc if not gen_desc.startswith("(OOC:") else item_default.get('description', base_desc_for_skill_check)
                            else:
                                base_desc_for_skill_check = item_default.get('description', base_desc_for_skill_check)
                                self._print_color(f"({base_desc_for_skill_check})", Colors.DIM)

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
                            for prop_str in properties_to_display:
                                self._print_color(f"- {prop_str}", Colors.BLUE)
                            self._print_color("", Colors.RESET) # Spacing after properties

                            if self.player_character.check_skill("Observation", 1):
                                self._print_color("(Your keen eye picks up on finer details...)", Colors.CYAN + Colors.DIM)
                                observation_context = f"Player ({self.player_character.name}) succeeded an Observation skill check examining their {inv_item_info['name']}. What subtle detail, past use, hidden inscription, or unusual characteristic do they notice that isn't immediately obvious?"
                                detailed_observation = self.gemini_api.get_enhanced_observation(
                                    self.player_character,
                                    target_name=inv_item_info['name'],
                                    target_category="item",
                                    base_description=base_desc_for_skill_check,
                                    skill_check_context=observation_context
                                )
                                if detailed_observation and not detailed_observation.startswith("(OOC:"):
                                    self._print_color(f"Detail: \"{detailed_observation}\"", Colors.GREEN)
                            
                            sensitive_items_for_observation = {
                                "Raskolnikov's axe": {"sentiment": -2, "observer_specific": {"Porfiry Petrovich": -3}},
                                "bloodied rag": {"sentiment": -2, "observer_specific": {"Porfiry Petrovich": -2, "Sonya Marmeladova": -1}},
                                "Lizaveta's bundle": {"sentiment": -1, "observer_specific": {"Sonya Marmeladova": -2}}
                            }
                            if inv_item_info["name"] in sensitive_items_for_observation:
                                item_sensitivity_data = sensitive_items_for_observation[inv_item_info["name"]]
                                for npc_observer in self.npcs_in_current_location:
                                    if npc_observer.name != self.player_character.name:
                                        base_sentiment = item_sensitivity_data["sentiment"]
                                        observer_specific_sentiment = item_sensitivity_data.get("observer_specific", {}).get(npc_observer.name)
                                        final_sentiment = observer_specific_sentiment if observer_specific_sentiment is not None else base_sentiment
                                        npc_observer.add_player_memory(
                                            memory_type="player_action_observed",
                                            turn=self.game_time,
                                            content={
                                                "action": f"examined_item_from_inventory",
                                                "item_name": inv_item_info["name"],
                                                "location": self.current_location_name
                                            },
                                            sentiment_impact=final_sentiment
                                        )
                            found_target = True; break
            # Look at NPC
            if not found_target:
                for npc in self.npcs_in_current_location:
                    if npc.name.lower().startswith(target_to_look_at):
                        self._print_color(f"You look closely at {Colors.YELLOW}{npc.name}{Colors.RESET} (appears {npc.apparent_state}):", Colors.WHITE)
                        base_desc_for_skill_check = f"{npc.name} appears {npc.apparent_state}." # Default
                        if self.gemini_api.model:
                            observation = self.gemini_api.get_player_reflection(
                                self.player_character, self.current_location_name, self.get_current_time_period(),
                                f"observing {npc.name} in {self.current_location_name}. They appear to be '{npc.apparent_state}'. You recall: {npc.get_player_memory_summary(self.game_time)}",
                                self.player_character.get_inventory_description(),
                                self._get_objectives_summary(self.player_character))
                            self._print_color(f"\"{observation}\"", Colors.GREEN if not observation.startswith("(OOC:") else Colors.YELLOW)
                            base_desc_for_skill_check = observation if not observation.startswith("(OOC:") else npc.persona[:100]
                        else:
                            base_desc_for_skill_check = npc.persona[:100]
                            self._print_color(f"({base_desc_for_skill_check})", Colors.DIM)
                        
                        if self.player_character.check_skill("Observation", 1): 
                            self._print_color("(Your keen observation notices something more...)", Colors.CYAN + Colors.DIM)
                            observation_context = f"Player ({self.player_character.name}) succeeded an Observation skill check while looking at {npc.name} (appears {npc.apparent_state}). What subtle, non-obvious detail does {self.player_character.name} notice about {npc.name}'s demeanor, clothing, a hidden object, or a subtle emotional cue? This should be something beyond the obvious, a deeper insight."
                            detailed_observation = self.gemini_api.get_enhanced_observation(
                                self.player_character, 
                                target_name=npc.name, 
                                target_category="person", 
                                base_description=base_desc_for_skill_check,
                                skill_check_context=observation_context
                            )
                            if detailed_observation and not detailed_observation.startswith("(OOC:"):
                                self._print_color(f"Insight: \"{detailed_observation}\"", Colors.GREEN)
                        found_target = True; break
            # Look at scenery
            if not found_target:
                loc_data = LOCATIONS_DATA.get(self.current_location_name, {})
                loc_desc_lower = loc_data.get("description", "").lower()
                is_scenery = any(keyword in target_to_look_at for keyword in GENERIC_SCENERY_KEYWORDS) or \
                             target_to_look_at in loc_desc_lower
                
                if is_scenery:
                    self._print_color(f"You focus on the {target_to_look_at}...", Colors.WHITE)
                    base_desc_for_skill_check = f"The general scenery of {self.current_location_name}, focusing on {target_to_look_at}."
                    if self.gemini_api.model:
                        observation = self.gemini_api.get_scenery_observation(
                            self.player_character, target_to_look_at, self.current_location_name,
                            self.get_current_time_period(), self._get_objectives_summary(self.player_character))
                        if observation and not observation.startswith("(OOC:"):
                            self._print_color(f"\"{observation}\"", Colors.CYAN)
                            base_desc_for_skill_check = observation # Use AI generated base for better context
                        else:
                            self._print_color(f"The {target_to_look_at} offers no particular insight beyond its mundane presence.", Colors.DIM)
                    else:
                        self._print_color(f"The {target_to_look_at} is just as it seems.", Colors.DIM)

                    if self.player_character.check_skill("Observation", 0): 
                        self._print_color("(You scan the area more intently...)", Colors.CYAN + Colors.DIM)
                        observation_context = f"Player ({self.player_character.name}) passed an Observation check while looking at '{target_to_look_at}' in {self.current_location_name}. What specific, easily missed detail about '{target_to_look_at}' or its immediate surroundings catches their eye, perhaps hinting at a past event, a hidden element, or the general atmosphere in a more profound way?"
                        detailed_observation = self.gemini_api.get_enhanced_observation(
                            self.player_character,
                            target_name=target_to_look_at, 
                            target_category="scenery",
                            base_description=base_desc_for_skill_check,
                            skill_check_context=observation_context
                        )
                        if detailed_observation and not detailed_observation.startswith("(OOC:"):
                            self._print_color(f"You also notice: \"{detailed_observation}\"", Colors.GREEN)
                    found_target = True
            
            if not found_target:
                self._print_color(f"You don't see '{argument}' here to look at specifically.", Colors.RED)
            # Add a separator after specific look details, before general lists
            self._print_color(self.game_config.SEPARATOR_LINE, Colors.DIM)


        # --- General Look: People, Items, Exits ---
        # (This part will also execute after a specific look, to list other interactables)

        # NPCs
        self._print_color("", Colors.RESET) # Extra spacing
        self._print_color("--- People Here ---", Colors.YELLOW + Colors.BOLD)
        npcs_present_for_hint = False
        if self.npcs_in_current_location:
            for npc in self.npcs_in_current_location:
                look_at_npc_display = f"Look at {npc.name}"
                self.numbered_actions_context.append({'type': 'look_at_npc', 'target': npc.name, 'display': look_at_npc_display})
                self._print_color(f"{action_number}. {look_at_npc_display}", Colors.YELLOW, end="")
                print(f" (Appears: {npc.apparent_state}, Relationship: {self.get_relationship_text(npc.relationship_with_player)})")
                action_number += 1
                npcs_present_for_hint = True

                talk_to_npc_display = f"Talk to {npc.name}"
                self.numbered_actions_context.append({'type': 'talk', 'target': npc.name, 'display': talk_to_npc_display})
                self._print_color(f"{action_number}. {talk_to_npc_display}", Colors.YELLOW)
                action_number += 1
        else:
            self._print_color("You see no one else of note here.", Colors.DIM)

        # Items
        self._print_color("", Colors.RESET) # Extra spacing
        self._print_color("--- Items Here ---", Colors.YELLOW + Colors.BOLD)
        current_loc_items = self.dynamic_location_items.get(self.current_location_name, [])
        items_present_for_hint = False
        if current_loc_items:
            for item_info in current_loc_items:
                item_name = item_info["name"]; item_qty = item_info.get("quantity", 1)
                item_default_info = DEFAULT_ITEMS.get(item_name, {})
                desc_snippet = item_default_info.get('description', 'an item')[:40]
                qty_str = f" (x{item_qty})" if (item_default_info.get("stackable") or item_default_info.get("value") is not None) and item_qty > 1 else ""

                look_at_display = f"Look at {item_name}"
                self.numbered_actions_context.append({'type': 'look_at_item', 'target': item_name, 'display': look_at_display})
                self._print_color(f"{action_number}. {look_at_display}", Colors.GREEN, end="")
                print(f" - {desc_snippet}...")
                action_number += 1
                items_present_for_hint = True

                if item_default_info.get("takeable", False):
                    take_display = f"Take {item_name}"
                    self.numbered_actions_context.append({'type': 'take', 'target': item_name, 'display': take_display})
                    self._print_color(f"{action_number}. {take_display}{qty_str}", Colors.GREEN)
                    action_number += 1
        else:
            self._print_color("No loose items of interest here.", Colors.DIM)

        # Exits
        self._print_color("", Colors.RESET) # Extra spacing
        self._print_color("--- Exits ---", Colors.BLUE + Colors.BOLD)
        has_accessible_exits = False
        if current_location_data and current_location_data.get("exits"):
            for exit_target_loc, exit_desc in current_location_data["exits"].items():
                display_text = f"{exit_desc} (to {exit_target_loc})"
                self.numbered_actions_context.append({'type': 'move', 'target': exit_target_loc, 'description': exit_desc, 'display': display_text})
                self._print_color(f"{action_number}. {display_text}", Colors.BLUE)
                action_number += 1
                has_accessible_exits = True
        if not has_accessible_exits:
            self._print_color("There are no obvious exits from here.", Colors.DIM)

        # Contextual Hints (moved to the end)
        self._print_color("", Colors.RESET) # Extra spacing before hints
        if items_present_for_hint:
            self._print_color("(Hint: You can 'take [item name]', 'look at [item name]', or use a number to interact with items.)", Colors.DIM)
        if npcs_present_for_hint:
            self._print_color("(Hint: You can 'talk to [npc name]', 'look at [npc name]', or use a number to interact with people.)", Colors.DIM)

    def _handle_status_command(self):
        """Displays the player character's current status."""
        if not self.player_character:
            self._print_color("No player character loaded.", Colors.RED)
            return

        self._print_color("\n--- Your Status ---", Colors.CYAN + Colors.BOLD)

        # Basic Info
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

        # Skills
        self._print_color("\n--- Skills ---", Colors.CYAN + Colors.BOLD)
        if self.player_character.skills:
            for skill_name, value in self.player_character.skills.items():
                self._print_color(f"- {skill_name.capitalize()}: {value}", Colors.WHITE)
        else:
            self._print_color("No specialized skills.", Colors.DIM)

        # Active Objectives
        self._print_color("\n--- Active Objectives ---", Colors.CYAN + Colors.BOLD)
        active_objectives = [obj for obj in self.player_character.objectives if obj.get("active", False) and not obj.get("completed", False)]
        if active_objectives:
            for obj in active_objectives:
                self._print_color(f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE)
                current_stage = self.player_character.get_current_stage_for_objective(obj.get('id'))
                if current_stage:
                    self._print_color(f"  Current Stage: {current_stage.get('description', 'No stage description')}", Colors.CYAN)
        else:
            self._print_color("No active objectives.", Colors.DIM)

        # Inventory Highlights
        self._print_color("\n--- Inventory Highlights ---", Colors.CYAN + Colors.BOLD)
        if self.player_character.inventory:
            highlights = []
            for item_obj in self.player_character.inventory:
                item_name = item_obj["name"]
                item_qty = item_obj.get("quantity", 1)
                item_default_props = self.game_config.DEFAULT_ITEMS.get(item_name, {})
                if (item_default_props.get("stackable") or item_default_props.get("value") is not None) and item_qty > 1:
                    highlights.append(f"{item_name} (x{item_qty})")
                else:
                    highlights.append(item_name)
            if highlights:
                self._print_color(", ".join(highlights), Colors.GREEN)
            else: # Should not happen if inventory has items, but as a fallback
                self._print_color("Carrying some items.", Colors.DIM)
        else:
            self._print_color("Carrying nothing of note.", Colors.DIM)

        # Relationships
        self._print_color("\n--- Relationships ---", Colors.CYAN + Colors.BOLD)
        meaningful_relationships = False
        for char_name, char_obj in self.all_character_objects.items():
            if char_obj.is_player:
                continue
            if hasattr(char_obj, 'relationship_with_player') and char_obj.relationship_with_player != 0:
                relationship_text = self.get_relationship_text(char_obj.relationship_with_player)
                self._print_color(f"- {char_name}: {relationship_text}", Colors.WHITE)
                meaningful_relationships = True

        if not meaningful_relationships:
            self._print_color("No significant relationships established yet.", Colors.DIM)

        self._print_color("", Colors.RESET) # Trailing space for readability


    def _handle_inventory_command(self):
        """Handles the 'inventory' command."""
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
                        # Remove trailing period if present before printing
                        self._print_color(f"- {item_with_details.rstrip('.')}", Colors.GREEN)
                    if items_list: # If there were items
                        self._print_color("(Hint: You can 'use [item]', 'read [item]', 'drop [item]', or 'give [item] to [person]'.)", Colors.DIM)
            elif inv_desc.lower() == "you are carrying nothing.": # Alternative phrasing from character_module
                 self._print_color("- Nothing", Colors.DIM)
            else: # Fallback if format is unexpected
                print(inv_desc)
        else:
            self._print_color("Cannot display inventory: Player character not available.", Colors.RED)

    def _handle_take_command(self, argument):
        """Handles the 'take' command."""
        if not argument:
            self._print_color("What do you want to take?", Colors.RED)
            return False, False # action_taken, show_atmospherics
        if not self.player_character:
            self._print_color("Cannot take items: Player character not available.", Colors.RED)
            return False, False

        item_to_take_name = argument.lower()
        location_items = self.dynamic_location_items.get(self.current_location_name, [])
        item_found_in_loc = None
        item_idx_in_loc = -1

        for idx, item_info in enumerate(location_items):
            if item_info["name"].lower().startswith(item_to_take_name):
                item_found_in_loc = item_info
                item_idx_in_loc = idx
                break
        
        if item_found_in_loc:
            item_default_props = DEFAULT_ITEMS.get(item_found_in_loc["name"], {})
            if item_default_props.get("takeable", False):
                take_quantity = 1 # Default to taking 1 unit
                actual_taken_qty = 0
                if item_default_props.get("stackable") or item_default_props.get("value") is not None:
                    current_qty_in_loc = item_found_in_loc.get("quantity", 1)
                    actual_taken_qty = min(take_quantity, current_qty_in_loc)
                    item_found_in_loc["quantity"] -= actual_taken_qty
                    if item_found_in_loc["quantity"] <= 0:
                        location_items.pop(item_idx_in_loc)
                else: # Non-stackable
                    actual_taken_qty = 1
                    location_items.pop(item_idx_in_loc)
                
                if self.player_character.add_to_inventory(item_found_in_loc["name"], actual_taken_qty):
                    self._print_color(f"You take the {item_found_in_loc['name']}" + \
                                      (f" (x{actual_taken_qty})" if actual_taken_qty > 1 and \
                                       (item_default_props.get("stackable") or item_default_props.get("value") is not None) else "") + ".", Colors.GREEN)
                    self.last_significant_event_summary = f"took the {item_found_in_loc['name']}."
                    if item_default_props.get("is_notable"):
                        self.player_character.apparent_state = random.choice(["thoughtful", "burdened"])
                    
                    # --- Notoriety Change for taking Raskolnikov's axe ---
                    if self.player_character.name == "Rodion Raskolnikov" and item_found_in_loc["name"] == "Raskolnikov's axe":
                        self.player_notoriety_level = min(3, max(0, self.player_notoriety_level + 0.5))
                        self._print_color("(Reclaiming the axe sends a shiver down your spine, a feeling of being marked.)", Colors.RED + Colors.DIM)
                        # print(f"[DEBUG] Notoriety changed to: {self.player_notoriety_level}") # Keep debug for now
                    # --- End Notoriety Change ---

                    # Add memory for NPCs in the same location
                    for npc in self.npcs_in_current_location:
                        if npc.name != self.player_character.name: # Don't record memory for self
                            npc.add_player_memory(
                                memory_type="player_action_observed",
                                turn=self.game_time,
                                content={
                                    "action": "took_item",
                                    "item_name": item_found_in_loc["name"],
                                    "quantity": actual_taken_qty,
                                    "location": self.current_location_name
                                },
                                sentiment_impact= -1 if item_default_props.get("is_notable") else 0 # Taking notable items might be seen negatively
                            )
                            # self._print_color(f"[DEBUG] {npc.name} remembers player taking {item_found_in_loc['name']}", Colors.DIM)

                    # Add contextual hint for taken item
                    taken_item_name = item_found_in_loc["name"]
                    taken_item_props = self.game_config.DEFAULT_ITEMS.get(taken_item_name, {})
                    if taken_item_props.get("readable"):
                        self._print_color(f"(Hint: You can now 'read {taken_item_name}'.)", Colors.DIM)
                    elif taken_item_props.get("use_effect_player") and taken_item_name != "worn coin": # Avoid "use worn coin" hint unless it has other specific uses
                        self._print_color(f"(Hint: You can try to 'use {taken_item_name}'.)", Colors.DIM)

                    return True, True
                else:
                    self._print_color(f"Failed to add {item_found_in_loc['name']} to inventory.", Colors.RED)
                    # If adding failed, revert quantity change in location (tricky, might need to re-add)
                    # For now, assume add_to_inventory is robust or this is an acceptable loss of item from loc.
                    return False, True 
            else:
                self._print_color(f"You can't take the {item_found_in_loc['name']}.", Colors.YELLOW)
                return False, True
        else:
            self._print_color(f"You don't see any '{item_to_take_name}' here to take.", Colors.RED)
            return False, False # No item found, no atmospherics change needed
        
    def _handle_drop_command(self, argument):
        """Handles the 'drop' command."""
        if not argument:
            self._print_color("What do you want to drop?", Colors.RED)
            return False, False
        if not self.player_character:
            self._print_color("Cannot drop items: Player character not available.", Colors.RED)
            return False, False

        item_to_drop_name_input = argument.lower()
        item_in_inventory_obj = None
        for inv_item in self.player_character.inventory:
            if inv_item["name"].lower().startswith(item_to_drop_name_input):
                item_in_inventory_obj = inv_item
                break
        
        if item_in_inventory_obj:
            item_name_to_drop = item_in_inventory_obj["name"]
            item_default_props = DEFAULT_ITEMS.get(item_name_to_drop, {})
            drop_quantity = 1 # Default to dropping 1 unit

            if self.player_character.remove_from_inventory(item_name_to_drop, drop_quantity):
                location_items = self.dynamic_location_items.setdefault(self.current_location_name, [])
                existing_loc_item = None
                for loc_item in location_items:
                    if loc_item["name"] == item_name_to_drop:
                        existing_loc_item = loc_item
                        break
                
                if existing_loc_item and (item_default_props.get("stackable") or item_default_props.get("value") is not None):
                    existing_loc_item["quantity"] = existing_loc_item.get("quantity", 0) + drop_quantity
                else:
                    location_items.append({"name": item_name_to_drop, "quantity": drop_quantity})
                
                self._print_color(f"You drop the {item_name_to_drop}.", Colors.GREEN)
                self.last_significant_event_summary = f"dropped the {item_name_to_drop}."

                # Add memory for NPCs in the same location
                for npc in self.npcs_in_current_location:
                    if npc.name != self.player_character.name: # Don't record memory for self
                        npc.add_player_memory(
                            memory_type="player_action_observed",
                            turn=self.game_time,
                            content={
                                "action": "dropped_item",
                                "item_name": item_name_to_drop,
                                "quantity": drop_quantity, # This is usually 1
                                "location": self.current_location_name
                            },
                            sentiment_impact=0 # Dropping items is generally neutral unless it's something offensive/weird
                        )
                        # self._print_color(f"[DEBUG] {npc.name} remembers player dropping {item_name_to_drop}", Colors.DIM)
                return True, True
            else:
                self._print_color(f"You try to drop {item_name_to_drop}, but something is wrong.", Colors.RED)
                return False, True
        else:
            self._print_color(f"You don't have '{item_to_drop_name_input}' to drop.", Colors.RED)
            return False, False

    def _handle_use_command(self, argument):
        """Handles the 'use' command by delegating to handle_use_item."""
        if not self.player_character:
            self._print_color("Cannot use items: Player character not available.", Colors.RED)
            return False # action_taken
        
        if isinstance(argument, tuple): # For complex use commands like "use item on target" or "give item to target"
            item_name_input, target_name_input, interaction_mode = argument
            return self.handle_use_item(item_name_input, target_name_input, interaction_mode)
        elif argument: # For simple "use item"
            return self.handle_use_item(argument, None, "use_self_implicit")
        else:
            self._print_color("What do you want to use or read?", Colors.RED)
            return False

    def _handle_think_command(self):
        """Handles the 'think' command."""
        if not self.player_character:
            self._print_color("Cannot think: Player character not available.", Colors.RED)
            return
        
        self._print_color("You pause to reflect...", Colors.MAGENTA)
        full_reflection_context = self._get_objectives_summary(self.player_character) + \
                                f"\nInventory: {self.player_character.get_inventory_description()}" + \
                                f"\nYour current apparent state is '{self.player_character.apparent_state}'." + \
                                f"\nRecent notable events: {self._get_recent_events_summary()}"
        if self.gemini_api.model:
            reflection = self.gemini_api.get_player_reflection(
                self.player_character, self.current_location_name,
                self.get_current_time_period(), full_reflection_context)
            self._print_color(f"Inner thought: \"{reflection}\"", Colors.GREEN if not reflection.startswith("(OOC:") else Colors.YELLOW)
        else:
            self._print_color(f"Inner thought: (Your mind is a whirl of thoughts, too complex to articulate now without deeper reflection.)", Colors.DIM)
        self.last_significant_event_summary = "was lost in thought."

    def _handle_wait_command(self):
        """Handles the 'wait' command and returns time_to_advance."""
        self._print_color("You wait for a while...", Colors.MAGENTA)
        self.last_significant_event_summary = "waited, letting time and thoughts drift."
        return TIME_UNITS_PER_PLAYER_ACTION * random.randint(3, 6) # Return time_to_advance
    
    def _handle_talk_to_command(self, argument):
        """Handles the 'talk to [npc]' command."""
        if not argument:
            self._print_color("Who do you want to talk to?", Colors.RED)
            return False, False # action_taken, show_atmospherics
        if not self.npcs_in_current_location:
            print("There's no one here to talk to.")
            return False, False
        if not self.player_character:
            self._print_color("Cannot talk: Player character not available.", Colors.RED)
            return False, False

        target_name_input = argument
        target_npc = next((npc for npc in self.npcs_in_current_location if npc.name.lower().startswith(target_name_input.lower())), None)

        if target_npc:
            if target_npc.name == "Porfiry Petrovich":
                solve_murders_obj = target_npc.get_objective_by_id("solve_murders")
                if solve_murders_obj and solve_murders_obj.get("active"):
                    current_stage_obj = target_npc.get_current_stage_for_objective("solve_murders")
                    if current_stage_obj and current_stage_obj.get("stage_id") == "encourage_confession":
                        new_state = "intensely persuasive"
                        if target_npc.apparent_state != new_state:
                            target_npc.apparent_state = new_state
                            self._print_color(f"({target_npc.name} seems to adopt a new demeanor, his gaze sharpening. He now appears {target_npc.apparent_state}.)", self.game_config.Colors.MAGENTA + self.game_config.Colors.DIM)

            self.current_conversation_log = [] 
            MAX_CONVERSATION_LOG_LINES = 20 

            self._print_color(f"\nYou approach {Colors.YELLOW}{target_npc.name}{Colors.RESET} (appears {target_npc.apparent_state}).", Colors.WHITE)
            
            # ==== MODIFICATION FOR DYNAMIC GREETING STARTS HERE ====
            should_print_static_greeting = True
            if self.player_character.name == "Rodion Raskolnikov" and target_npc.name == "Dmitri Razumikhin":
                should_print_static_greeting = False # Let AI generate the first line for this specific interaction
            # ==== MODIFICATION FOR DYNAMIC GREETING ENDS HERE ====

            if should_print_static_greeting and hasattr(target_npc, 'greeting') and target_npc.greeting:
                 initial_greeting_text = f"{target_npc.name}: \"{target_npc.greeting}\""
                 self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end=""); print(f"\"{target_npc.greeting}\"")
                 self.current_conversation_log.append(initial_greeting_text)
                 if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES: self.current_conversation_log.pop(0)

            conversation_active = True
            while conversation_active:
                player_dialogue = self._input_color(f"You ({Colors.GREEN}{self.player_character.name}{Colors.RESET}): {self.game_config.PROMPT_ARROW}", Colors.GREEN).strip()

                if player_dialogue.lower() in ['history', 'review', 'log']:
                    self._print_color("\n--- Recent Conversation History ---", Colors.CYAN + Colors.BOLD)
                    if not self.current_conversation_log:
                        self._print_color("No history recorded yet for this conversation.", Colors.DIM)
                    else:
                        history_to_show = self.current_conversation_log[-10:] 
                        for line in history_to_show:
                            if line.startswith("You:"):
                                self._print_color(line, Colors.GREEN)
                            elif ":" in line:
                                speaker, rest_of_line = line.split(":", 1)
                                self._print_color(f"{speaker}:", Colors.YELLOW, end="")
                                print(rest_of_line)
                            else:
                                self._print_color(line, Colors.DIM)
                    self._print_color("--- End of History ---", Colors.CYAN + Colors.BOLD)
                    continue 
                
                logged_player_dialogue = f"You: {player_dialogue}"
                self.current_conversation_log.append(logged_player_dialogue)
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES: self.current_conversation_log.pop(0)

                if self.check_conversation_conclusion(player_dialogue):
                    self._print_color(f"You end the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.", Colors.WHITE)
                    conversation_active = False
                    break
                if not player_dialogue: 
                    self._print_color("You remain silent for a moment.", Colors.DIM)
                    pass


                if self.gemini_api.model:
                    self._print_color("Thinking...", Colors.DIM + Colors.MAGENTA)
                    ai_response = self.gemini_api.get_npc_dialogue(
                        target_npc, self.player_character, player_dialogue,
                        self.current_location_name, self.get_current_time_period(),
                        self.get_relationship_text(target_npc.relationship_with_player),
                        target_npc.get_player_memory_summary(self.game_time), 
                        self.player_character.apparent_state,
                        self.player_character.get_notable_carried_items_summary(),
                        self._get_recent_events_summary(),
                        self._get_objectives_summary(target_npc),
                        self._get_objectives_summary(self.player_character)
                    )
                else: 
                    ai_response = random.choice([
                        "Yes?", "Hmm.", "What is it?", "I am busy.",
                        f"{target_npc.greeting if hasattr(target_npc, 'greeting') else '...'}"
                    ])
                    self._print_color(f"{Colors.DIM}(Using placeholder dialogue){Colors.RESET}", Colors.DIM)

                target_npc.update_relationship(player_dialogue, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS, self.game_time)
                self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end=""); print(f"\"{ai_response}\"")

                logged_ai_response = f"{target_npc.name}: \"{ai_response}\""
                self.current_conversation_log.append(logged_ai_response)
                if len(self.current_conversation_log) > MAX_CONVERSATION_LOG_LINES: self.current_conversation_log.pop(0)

                self.last_significant_event_summary = f"spoke with {target_npc.name} who said: \"{ai_response[:50]}...\""
                
                if self.check_conversation_conclusion(ai_response):
                    self._print_color(f"\nThe conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET} seems to have concluded.", Colors.MAGENTA)
                    conversation_active = False
                
                self.advance_time(TIME_UNITS_PER_PLAYER_ACTION) 
                if self.event_manager.check_and_trigger_events(): 
                    self.last_significant_event_summary = "an event occurred during conversation."

            unusual_states = ["feverish", "slightly drunk", "paranoid", "agitated", "dangerously agitated", "remorseful", "haunted by dreams", "injured"]
            current_player_state = self.player_character.apparent_state
            if current_player_state in unusual_states:
                sentiment = 0
                if current_player_state in ["dangerously agitated", "paranoid"]:
                    sentiment = -1
                target_npc.add_player_memory(
                    memory_type="observed_player_state",
                    turn=self.game_time,
                    content={"state": current_player_state, "context": "during conversation"},
                    sentiment_impact=sentiment
                )

            for item_in_inventory in self.player_character.inventory:
                item_name = item_in_inventory.get("name")
                if item_name in self.game_config.HIGHLY_NOTABLE_ITEMS_FOR_MEMORY:
                    sentiment = 0
                    if item_name in ["Raskolnikov's axe", "bloodied rag"]:
                        sentiment = -1
                    elif item_name == "Sonya's Cypress Cross" and target_npc.name != "Sonya Marmeladova":
                        if target_npc.name == "Porfiry Petrovich" and self.player_character.name == "Rodion Raskolnikov":
                            sentiment = -1

                    target_npc.add_player_memory(
                        memory_type="observed_player_inventory",
                        turn=self.game_time,
                        content={"item_name": item_name, "context": "player was carrying during conversation"},
                        sentiment_impact=sentiment
                    )
            
            if self.player_character.name == "Rodion Raskolnikov" and target_npc and target_npc.name == "Porfiry Petrovich":
                self.player_notoriety_level = min(3, max(0, self.player_notoriety_level + 0.15))
                self._print_color("(Your conversation with Porfiry seems to have drawn some attention...)", Colors.YELLOW + Colors.DIM)
                # print(f"[DEBUG] Notoriety changed to: {self.player_notoriety_level}") # Kept for dev testing if needed
            return True, True 
        else:
            self._print_color(f"You don't see anyone named '{target_name_input}' here.", Colors.RED)
            return False, False

    def _handle_move_to_command(self, argument):
        """Handles the 'move to [location]' command."""
        if not argument:
            self._print_color("Where do you want to move to?", Colors.RED)
            return False, False # action_taken, show_atmospherics
        if not self.player_character:
            self._print_color("Cannot move: Player character not available.", Colors.RED)
            return False, False

        target_exit_input = argument.lower()
        moved = False
        potential_target_loc_name = None
        
        current_location_data = LOCATIONS_DATA.get(self.current_location_name)
        if not current_location_data: # Should not happen if game state is consistent
             self._print_color(f"Error: Data for current location '{self.current_location_name}' is missing.", Colors.RED)
             return False, False

        location_exits = current_location_data.get("exits", {})
        for target_loc_key, desc_text in location_exits.items():
            if target_loc_key.lower() == target_exit_input or \
               desc_text.lower().startswith(target_exit_input) or \
               target_exit_input in desc_text.lower():
                potential_target_loc_name = target_loc_key
                break
        
        if potential_target_loc_name:
            old_location = self.current_location_name
            self.current_location_name = potential_target_loc_name
            self.player_character.current_location = potential_target_loc_name
            self.current_location_description_shown_this_visit = False
            self.last_significant_event_summary = f"moved from {old_location} to {self.current_location_name}."
            
            # --- Notoriety Change for visiting Pawnbroker's Apartment ---
            if self.player_character.name == "Rodion Raskolnikov" and \
               potential_target_loc_name in ["Pawnbroker's Apartment", "Pawnbroker's Apartment Building"]:
                self.player_notoriety_level = min(3, max(0, self.player_notoriety_level + 0.25))
                self._print_color("(Your presence in this place feels heavy with unseen eyes...)", Colors.YELLOW + Colors.DIM)
                print(f"[DEBUG] Notoriety changed to: {self.player_notoriety_level}")
            # --- End Notoriety Change ---
                
            self.update_current_location_details(from_explicit_look_cmd=False)
            moved = True
            return True, True # action_taken, show_atmospherics (as new location details are shown)
        else:
            self._print_color(f"You can't find a way to '{target_exit_input}' from here.", Colors.RED)
            return False, False # No move, no new atmospherics needed beyond current
            

    # --- Refactored handle_use_item and its helpers ---

    def _handle_read_item(self, item_to_use_name, item_props, item_obj_in_inventory):
        """Handles reading a readable item."""
        if not item_props.get("readable"):
            self._print_color(f"You can't read the {item_to_use_name}.", Colors.YELLOW)
            return False

        effect_key = item_props.get("use_effect_player") # Original effect key

        if item_to_use_name == "old newspaper" or item_to_use_name == "Fresh Newspaper":
            self._print_color(f"You smooth out the creases of the {item_to_use_name} and scan the faded print.", Colors.WHITE)
            article_snippet = self.gemini_api.get_newspaper_article_snippet(
                self.current_day, self._get_recent_events_summary(),
                self._get_objectives_summary(self.player_character), self.player_character.apparent_state)
            if article_snippet and not article_snippet.startswith("(OOC:"):
                self._print_color(f"An article catches your eye: \"{article_snippet}\"", Colors.YELLOW)
                self.player_character.add_journal_entry("News", article_snippet, self._get_current_game_time_period_str())
                if "crime" in article_snippet.lower() or "investigation" in article_snippet.lower() or "murder" in article_snippet.lower():
                    self.player_character.apparent_state = "thoughtful"
                    if self.player_character.name == "Rodion Raskolnikov":
                        self.player_character.add_player_memory(memory_type="read_news_crime", turn=self.game_time, content={"summary": "Read unsettling news about the recent crime."}, sentiment_impact=0)
                        self.player_notoriety_level = min(self.player_notoriety_level + 0.1, 3)
                self.last_significant_event_summary = f"read an {item_to_use_name}."
            else:
                self._print_color("The print is too faded or the news too mundane to hold your interest.", Colors.DIM)
            return True
        
        elif item_to_use_name == "mother's letter":
            self._print_color(f"You re-read your mother's letter. Her words of love and anxiety, Dunya's predicament... it all weighs heavily on you.", Colors.YELLOW)
            reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, self.get_current_time_period(), "re-reading mother's letter about Dunya and Luzhin, feeling guilt and responsibility")
            self._print_color(f"\"{reflection}\"", Colors.CYAN)
            self.player_character.apparent_state = random.choice(["burdened", "agitated", "resolved"])
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.add_player_memory(memory_type="reread_mother_letter", turn=self.game_time, content={"summary": "Re-reading mother's letter intensified feelings of duty and distress."}, sentiment_impact=-1)
            self.last_significant_event_summary = f"re-read the {item_to_use_name}."
            return True

        elif item_to_use_name == "Sonya's New Testament":
            self._print_color(f"You open {item_to_use_name}. The familiar words of the Gospels seem to both accuse and offer a sliver of hope.", Colors.GREEN)
            reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, self.get_current_time_period(), f"reading from {item_to_use_name}, pondering Lazarus, guilt, and salvation")
            self._print_color(f"\"{reflection}\"", Colors.CYAN)
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.apparent_state = random.choice(["contemplative", "remorseful", "thoughtful", "hopeful"])
                self.player_character.add_player_memory(memory_type="read_testament_sonya", turn=self.game_time, content={"summary": "Read from the New Testament, stirring deep thoughts of salvation and suffering."}, sentiment_impact=0)
            self.last_significant_event_summary = f"read from {item_to_use_name}."
            return True

        elif item_to_use_name == "Anonymous Note":
            if item_obj_in_inventory and "generated_content" in item_obj_in_inventory:
                self._print_color(f"You read the {item_to_use_name}:", Colors.WHITE)
                self._print_color(f"\"{item_obj_in_inventory['generated_content']}\"", Colors.CYAN)
                self.player_character.add_journal_entry("Note", item_obj_in_inventory['generated_content'], self._get_current_game_time_period_str())
                self.last_significant_event_summary = f"read an {item_to_use_name}."
                if "watch" in item_obj_in_inventory['generated_content'].lower() or "know" in item_obj_in_inventory['generated_content'].lower():
                    self.player_character.apparent_state = "paranoid"
                return True
            else:
                self._print_color(f"The {item_to_use_name} seems to be blank or unreadable.", Colors.RED)
                return False
        
        elif item_to_use_name == "IOU Slip":
            if item_obj_in_inventory and item_obj_in_inventory.get("content"):
                self._print_color(f"You examine the {item_to_use_name}: \"{item_obj_in_inventory['content']}\"", Colors.YELLOW)
            else:
                self._print_color(f"You look at the {item_to_use_name}. It's a formal-looking slip of paper.", Colors.YELLOW)
            self.last_significant_event_summary = f"read an {item_to_use_name}."
            return True
            
        elif item_to_use_name == "Student's Dog-eared Book":
            book_reflection = self.gemini_api.get_item_interaction_description(
                self.player_character, item_to_use_name, item_props, "read",
                self.current_location_name, self.get_current_time_period())
            self._print_color(f"You open the {item_to_use_name}. {book_reflection}", Colors.YELLOW)
            self.last_significant_event_summary = f"read from a {item_to_use_name}."
            return True
        
        # Generic fallback for other readable items without specific handlers
        read_reflection = self.gemini_api.get_item_interaction_description(
            self.player_character, item_to_use_name, item_props, "read",
            self.current_location_name, self.get_current_time_period())
        self._print_color(f"You read the {item_to_use_name}. {read_reflection}", Colors.YELLOW)
        self.last_significant_event_summary = f"read the {item_to_use_name}."
        return True


    def _handle_self_use_item(self, item_to_use_name, item_props, effect_key):
        """Handles using an item on the player character itself."""
        used_successfully = False
        if effect_key == "comfort_self_if_ill" and item_to_use_name == "tattered handkerchief":
            if self.player_character.apparent_state in ["feverish", "coughing", "ill", "haunted by dreams"]:
                self._print_color(f"You press the {item_to_use_name} to your brow. It offers little physical comfort, but it's something to cling to.", Colors.YELLOW)
                if self.player_character.apparent_state == "feverish" and random.random() < 0.2:
                    self.player_character.apparent_state = "less feverish"
                    self._print_color("The coolness, imagined or real, seems to lessen the fever's grip for a moment.", Colors.CYAN)
                self.last_significant_event_summary = f"used a {item_to_use_name} while feeling unwell."
                used_successfully = True
            else:
                self._print_color(f"You look at the {item_to_use_name}. It seems rather pointless to use it now.", Colors.YELLOW)
        
        elif effect_key == "examine_bottle_for_residue" and item_to_use_name == "dusty bottle":
            self._print_color(f"You peer into the {item_to_use_name}. A faint, stale smell of cheap spirits lingers. It's long empty.", Colors.YELLOW)
            self.last_significant_event_summary = f"examined a {item_to_use_name}."
            used_successfully = True

        elif effect_key == "grip_axe_and_reminisce_horror" and item_to_use_name == "Raskolnikov's axe":
            if self.player_character.name == "Rodion Raskolnikov":
                self._print_color(f"You grip the {item_to_use_name}. Its cold weight is a familiar dread. The memories, sharp and bloody, flood your mind. You feel a wave of nausea, then a chilling resolve, then utter despair.", Colors.RED + Colors.BOLD)
                self.player_character.apparent_state = random.choice(["dangerously agitated", "remorseful", "paranoid"])
                self.last_significant_event_summary = f"held the axe, tormented by memories."
                used_successfully = True
            else:
                self._print_color(f"You look at the {item_to_use_name}. It's a grim object, heavy and unsettling. Best left alone.", Colors.YELLOW)
                used_successfully = True
        
        elif effect_key == "reflect_on_faith_and_redemption" and item_to_use_name == "Sonya's Cypress Cross":
            if self.player_character.name == "Rodion Raskolnikov": 
                self._print_color("You clutch the small cypress cross. It feels strangely significant in your hand, a stark contrast to the turmoil within you.", Colors.GREEN)
                self.player_character.apparent_state = random.choice(["remorseful", "contemplative", "hopeful"])
                self.last_significant_event_summary = f"held Sonya's cross, feeling its weight and Sonya's sacrifice."
                reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, self.get_current_time_period(), "Holding Sonya's cross, new thoughts about suffering and sacrifice surface.")
                self._print_color(f"\"{reflection}\"", Colors.CYAN)
                used_successfully = True
            else:
                 self._print_color(f"You examine {item_to_use_name}. It seems to be a simple wooden cross, yet it emanates a certain potent feeling.", Colors.YELLOW)
                 used_successfully = True
        
        elif effect_key == "examine_rag_and_spiral_into_paranoia" and item_to_use_name == "bloodied rag":
            self._print_color(f"You stare at the {item_to_use_name}. The dark stains seem to shift and spread before your eyes. Every sound, every shadow, feels like an accusation.", Colors.RED)
            self.player_character.apparent_state = "paranoid"
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.add_player_memory(memory_type="observed_bloodied_rag", turn=self.game_time, content={"summary": "The sight of the bloodied rag brought a fresh wave of paranoia."}, sentiment_impact=-1) # Paranoia suggests negative sentiment
                self.player_notoriety_level = min(self.player_notoriety_level + 0.5, 3)
            self.last_significant_event_summary = f"was deeply disturbed by a {item_to_use_name}."
            used_successfully = True

        elif effect_key == "drink_vodka_for_oblivion" and item_to_use_name == "cheap vodka":
            self._print_color(f"You take a long swig of the harsh vodka. It burns on the way down, offering a brief, false warmth and a dulling of the senses.", Colors.MAGENTA)
            self.player_character.apparent_state = "slightly drunk"
            if self.player_character.has_item("cheap vodka"):
                self.player_character.remove_from_inventory("cheap vodka", 1) # Consumed
            else:
                 self._print_color("Odd, the bottle seems to have vanished before you could drink it all.", Colors.DIM) # Should not happen if logic is correct
            self.last_significant_event_summary = "drank some cheap vodka to numb the thoughts."
            if self.player_character.apparent_state == "feverish":
                self.player_character.apparent_state = "agitated"
                self._print_color("The vodka clashes terribly with your fever, making you feel worse.", Colors.RED)
            used_successfully = True
            # Note: consumable is handled by main handle_use_item, but vodka is special here
            return True #Vodka consumption handled, return True

        elif effect_key == "examine_bundle_and_face_guilt_for_Lizaveta" and item_to_use_name == "Lizaveta's bundle":
            self._print_color(f"You hesitantly open {item_to_use_name}. Inside are a few pitiful belongings: a worn shawl, a child's small wooden toy, a copper coin... The sight is a fresh stab of guilt for the gentle Lizaveta.", Colors.YELLOW)
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.apparent_state = "remorseful"
                self.player_character.add_player_memory(memory_type="examined_lizavetas_bundle", turn=self.game_time, content={"summary": "Examined Lizaveta's bundle; the innocence of the items was a heavy burden."}, sentiment_impact=-1) # "Heavy burden" suggests negative sentiment
            self.last_significant_event_summary = f"examined Lizaveta's bundle, increasing the weight of guilt."
            used_successfully = True
        
        elif effect_key == "eat_bread_for_sustenance" and item_to_use_name == "Loaf of Black Bread":
            self._print_color(f"You tear off a piece of the dense {item_to_use_name}. It's coarse, but fills your stomach somewhat.", Colors.YELLOW)
            if self.player_character.apparent_state in ["burdened", "feverish", "despondent"]:
                self.player_character.apparent_state = "normal"
                self._print_color("The bread provides a moment of simple relief.", Colors.CYAN)
            self.last_significant_event_summary = f"ate some {item_to_use_name}."
            used_successfully = True # This item will be consumed by the main handler

        elif effect_key == "contemplate_icon" and item_to_use_name == "Small, Tarnished Icon":
            icon_reflection = self.gemini_api.get_item_interaction_description(
                self.player_character, item_to_use_name, item_props, "contemplate",
                self.current_location_name, self.get_current_time_period())
            self._print_color(f"You gaze at the {item_to_use_name}. {icon_reflection}", Colors.YELLOW)
            self.last_significant_event_summary = f"contemplated a {item_to_use_name}."
            used_successfully = True
        
        # Fallback for unhandled self-use items
        if not used_successfully:
            self._print_color(f"You contemplate the {item_to_use_name}, but don't find a specific use for it right now.", Colors.YELLOW)
            return False # No specific action taken
            
        return used_successfully


    def _handle_persuade_command(self, argument):
        """Handles the 'persuade [npc] that/to [statement]' command."""
        if not argument or not isinstance(argument, tuple) or len(argument) != 2:
            self._print_color("How do you want to persuade them? Use: persuade [person] that/to [your argument]", Colors.RED)
            return False, False # action_taken, show_atmospherics

        target_npc_name, statement_text = argument

        if not self.player_character:
            self._print_color("Cannot persuade: Player character not available.", Colors.RED)
            return False, False

        target_npc = next((npc for npc in self.npcs_in_current_location if npc.name.lower().startswith(target_npc_name.lower())), None)

        if not target_npc:
            self._print_color(f"You don't see anyone named '{target_npc_name}' here to persuade.", Colors.RED)
            return False, False

        self._print_color(f"\nYou attempt to persuade {Colors.YELLOW}{target_npc.name}{Colors.RESET} that \"{statement_text}\"...", Colors.WHITE)

        # Determine difficulty - can be more dynamic later
        difficulty = 2 # Base difficulty for persuasion
        
        # Consider NPC's current state or relationship for difficulty? (Future enhancement)
        # Example: if target_npc.apparent_state == "agitated": difficulty += 1
        # Example: if target_npc.relationship_with_player < 0: difficulty +=1

        success = self.player_character.check_skill("Persuasion", difficulty)
        
        persuasion_skill_check_result_text = ""
        if success:
            persuasion_skill_check_result_text = "SUCCESS due to their skillful argument"
            # Could add critical success later based on roll margin
        else:
            persuasion_skill_check_result_text = "FAILURE despite their efforts"
            # Could add critical failure later

        # Construct context for AI
        # This will be passed to the new Gemini method
        # For now, we'll call the existing get_npc_dialogue but append the persuasion result.
        # Later, replace with get_npc_dialogue_persuasion_attempt
        
        # Placeholder for the new method call structure:
        # ai_response = self.gemini_api.get_npc_dialogue_persuasion_attempt(
        #     npc_character=target_npc,
        #     player_character=self.player_character,
        #     player_persuasive_statement=statement_text,
        #     current_location_name=self.current_location_name,
        #     current_time_period=self.get_current_time_period(),
        #     relationship_status_text=self.get_relationship_text(target_npc.relationship_with_player),
        #     npc_memory_summary=target_npc.get_player_memory_summary(self.game_time),
        #     player_apparent_state=self.player_character.apparent_state,
        #     player_notable_items_summary=self.player_character.get_notable_carried_items_summary(),
        #     recent_game_events_summary=self._get_recent_events_summary(),
        #     npc_objectives_summary=self._get_objectives_summary(target_npc),
        #     player_objectives_summary=self._get_objectives_summary(self.player_character),
        #     persuasion_skill_check_result_text=persuasion_skill_check_result_text
        # )
        
        # Using existing dialogue function for now, and just appending skill check result to player statement for context
        # This will be replaced by the call to the specialized persuasion method in gemini_interactions.py later
        # modified_player_statement_for_ai = f"{statement_text} (Attempting Persuasion: {persuasion_skill_check_result_text})"

        if self.gemini_api.model:
            self._print_color("Thinking...", Colors.DIM + Colors.MAGENTA)
            ai_response = self.gemini_api.get_npc_dialogue_persuasion_attempt(
                npc_character=target_npc,
                player_character=self.player_character,
                player_persuasive_statement=statement_text,
                current_location_name=self.current_location_name,
                current_time_period=self.get_current_time_period(),
                relationship_status_text=self.get_relationship_text(target_npc.relationship_with_player),
                npc_memory_summary=target_npc.get_player_memory_summary(self.game_time), # Pass current_turn
                player_apparent_state=self.player_character.apparent_state,
                player_notable_items_summary=self.player_character.get_notable_carried_items_summary(),
                recent_game_events_summary=self._get_recent_events_summary(),
                npc_objectives_summary=self._get_objectives_summary(target_npc),
                player_objectives_summary=self._get_objectives_summary(self.player_character),
                persuasion_skill_check_result_text=persuasion_skill_check_result_text
            )
        else:
            ai_response = f"Hmm, '{statement_text}', you say? That's... something to consider. (Skill: {persuasion_skill_check_result_text})"
            self._print_color(f"{Colors.DIM}(Using placeholder dialogue for persuasion){Colors.RESET}", Colors.DIM)

        self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end=""); print(f"\"{ai_response}\"")
        
        sentiment_impact_base = 0
        if success:
            self._print_color(f"Your argument seems to have had an effect!", Colors.GREEN)
            sentiment_impact_base = 1 # Persuasion success is positive
            target_npc.relationship_with_player += 1 # Small bonus for successful persuasion
        else:
            self._print_color(f"Your words don't seem to convince {target_npc.name}.", Colors.RED)
            sentiment_impact_base = -1 # Persuasion failure can be negative
            target_npc.relationship_with_player -= 1 # Small penalty

        # Add memory to NPC
        target_npc.add_player_memory(
            memory_type="persuasion_attempt",
            turn=self.game_time,
            content={
                "statement": statement_text[:100], # Truncate for brevity
                "outcome": "success" if success else "failure",
                "npc_response_snippet": ai_response[:70]
            },
            sentiment_impact=sentiment_impact_base 
        )
        
        self.last_significant_event_summary = f"attempted to persuade {target_npc.name} regarding '{statement_text[:30]}...'."

        # Record player state and items after persuasion attempt
        unusual_states = ["feverish", "slightly drunk", "paranoid", "agitated", "dangerously agitated", "remorseful", "haunted by dreams", "injured"]
        current_player_state = self.player_character.apparent_state
        if current_player_state in unusual_states:
            sentiment = 0
            if current_player_state in ["dangerously agitated", "paranoid"]:
                sentiment = -1
            target_npc.add_player_memory(
                memory_type="observed_player_state",
                turn=self.game_time, # Time already advanced for persuasion, or use current if not
                content={"state": current_player_state, "context": "during persuasion attempt"},
                sentiment_impact=sentiment
            )

        for item_in_inventory in self.player_character.inventory:
            item_name = item_in_inventory.get("name")
            if item_name in self.game_config.HIGHLY_NOTABLE_ITEMS_FOR_MEMORY:
                sentiment = 0
                if item_name in ["Raskolnikov's axe", "bloodied rag"]:
                    sentiment = -1
                elif item_name == "Sonya's Cypress Cross" and target_npc.name != "Sonya Marmeladova":
                    if target_npc.name == "Porfiry Petrovich" and self.player_character.name == "Rodion Raskolnikov":
                        sentiment = -1

                target_npc.add_player_memory(
                    memory_type="observed_player_inventory",
                    turn=self.game_time, # Time already advanced for persuasion
                    content={"item_name": item_name, "context": "player was carrying during persuasion attempt"},
                    sentiment_impact=sentiment
                )

        self.advance_time(TIME_UNITS_PER_PLAYER_ACTION) # Persuasion takes time
        return True, True # action_taken, show_atmospherics

    def _handle_give_item(self, item_to_use_name, item_props, target_name_input):
        """Handles giving an item to an NPC."""
        # This method currently only implements giving "worn coin".
        # It could be expanded for other items if "give" becomes a more general mechanic.
        if item_to_use_name == "worn coin":
            target_npc = next((npc for npc in self.npcs_in_current_location if npc.name.lower().startswith(target_name_input.lower())), None)
            if target_npc:
                if self.player_character.remove_from_inventory("worn coin", 1):
                    self._print_color(f"You offer a coin to {target_npc.name}.", Colors.WHITE)
                    relationship_text = self.get_relationship_text(target_npc.relationship_with_player)
                    reaction = self.gemini_api.get_npc_dialogue(
                        target_npc, self.player_character,
                        f"(Offers a coin out of {random.choice(['pity', 'a sudden impulse', 'a desire to help', 'unease'])}.)",
                        self.current_location_name, self.get_current_time_period(), relationship_text,
                        target_npc.get_player_memory_summary(self.game_time), self.player_character.apparent_state,
                        self.player_character.get_notable_carried_items_summary(),
                        self._get_recent_events_summary(),
                        self._get_objectives_summary(target_npc),
                        self._get_objectives_summary(self.player_character)
                    )
                    self._print_color(f"{target_npc.name}: \"{reaction}\"", Colors.YELLOW)
                    target_npc.relationship_with_player += 1 # Basic relationship update
                    target_npc.add_player_memory(
                        memory_type="received_item",
                        turn=self.game_time,
                        content={"item_name": item_to_use_name, "quantity": 1, "from_player": True},
                        sentiment_impact=1 # Giving a coin is generally positive
                    )
                    self.last_significant_event_summary = f"gave a coin to {target_npc.name}."
                    return True # Successfully gave item
                else:
                    self._print_color("You rummage through your pockets but find no coins to give.", Colors.RED)
                    return False
            else:
                self._print_color(f"You don't see '{target_name_input}' here to give a coin to.", Colors.RED)
                return False
        else:
            self._print_color(f"You can't give the {item_to_use_name} in this way.", Colors.YELLOW)
            return False

    def handle_use_item(self, item_name_input, target_name_input=None, interaction_type="use_self_implicit"):
        if not self.player_character:
            self._print_color("Cannot use items: Player character not set.", Colors.RED)
            return False

        item_to_use_name = None
        item_obj_in_inventory = None # Store the actual inventory object

        if item_name_input:
            for inv_item_obj_loop in self.player_character.inventory: # Renamed to avoid conflict
                if inv_item_obj_loop["name"].lower().startswith(item_name_input.lower()):
                    item_to_use_name = inv_item_obj_loop["name"]
                    item_obj_in_inventory = inv_item_obj_loop # Store it
                    break
            if not item_to_use_name:
                # Check if the exact name was provided, even if not starting with it (covers case sensitivity if startswith failed)
                if self.player_character.has_item(item_name_input):
                     item_to_use_name = item_name_input
                     item_obj_in_inventory = next((item for item in self.player_character.inventory if item["name"] == item_to_use_name), None)
                else:
                    self._print_color(f"You don't have '{item_name_input}' to {interaction_type.replace('_', ' ')}.", Colors.RED)
                    return False
        elif interaction_type != "use_self_implicit": # e.g. "give" or "use on" without item
             self._print_color(f"What do you want to {interaction_type.replace('_', ' ')}{(' on ' + target_name_input) if target_name_input else ''}?", Colors.RED)
             return False
        
        if not item_to_use_name : 
            self._print_color("You need to specify an item to use or read.", Colors.RED)
            return False

        item_props = DEFAULT_ITEMS.get(item_to_use_name, {})
        used_successfully = False

        if interaction_type == "read":
            used_successfully = self._handle_read_item(item_to_use_name, item_props, item_obj_in_inventory)
        elif interaction_type == "give" and target_name_input:
            used_successfully = self._handle_give_item(item_to_use_name, item_props, target_name_input)
        elif interaction_type == "use_on" and target_name_input:
            # Placeholder for "use on target" - currently no items have this specific effect.
            # This would require more complex logic, potentially new effect keys or a target_effect_key.
            self._print_color(f"You try to use the {item_to_use_name} on {target_name_input}, but nothing specific happens.", Colors.YELLOW)
            used_successfully = False # Or True if a generic "attempt" is considered a success
        else: # Default to self_use_implicit or general use
            effect_key = item_props.get("use_effect_player")
            if effect_key: # If there's a defined effect key for player
                used_successfully = self._handle_self_use_item(item_to_use_name, item_props, effect_key)
            else: # No specific effect_key, generic contemplation
                self._print_color(f"You contemplate the {item_to_use_name}, but don't find a specific use for it right now.", Colors.YELLOW)
                used_successfully = False # No actual game state change or time passes

        if used_successfully and item_props.get("consumable", False) and item_to_use_name != "cheap vodka":
            # Special handling for vodka is inside _handle_self_use_item to avoid double removal.
            # The check "item_to_use_name != "cheap vodka"" is now in the main if.
            if self.player_character.remove_from_inventory(item_to_use_name, 1):
                self._print_color(f"The {item_to_use_name} is used up.", Colors.MAGENTA)
            # else: Error removing consumed item? Should be rare.
        
        return used_successfully