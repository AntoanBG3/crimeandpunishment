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

        # New state variables for AI features
        self.player_notoriety_level = 0 # 0: unknown, 1: odd, 2: suspicious, 3: very suspicious
        self.known_facts_about_crime = ["An old pawnbroker and her sister were murdered recently."] # Initial fact
        self.key_events_occurred = ["Game started."] # Tracks major plot points for AI context

    def _get_current_game_time_period_str(self):
        return f"Day {self.current_day}, {self.get_current_time_period()}"

    def _get_objectives_summary(self, character):
        if not character or not character.objectives:
            return "No particular objectives."
        active_obj_descs = [obj.get('description', 'An unknown goal.') for obj in character.objectives if obj.get("active") and not obj.get("completed")]
        if not active_obj_descs:
            return "Currently pursuing no specific objectives."
        return "Current objectives: " + "; ".join(active_obj_descs)

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
            # Dream sequence check for Raskolnikov
            if self.player_character and self.player_character.name == "Rodion Raskolnikov":
                troubled_states = ["feverish", "dangerously agitated", "remorseful", "paranoid", "haunted by dreams", "agitated"]
                dream_chance = DREAM_CHANCE_TROUBLED_STATE if self.player_character.apparent_state in troubled_states else DREAM_CHANCE_NORMAL_STATE
                if random.random() < dream_chance:
                    self._print_color(f"\n{Colors.MAGENTA}As morning struggles to break, unsettling images from the night still cling to your mind...{Colors.RESET}", Colors.MAGENTA)
                    dream_text = self.gemini_api.get_dream_sequence(
                        self.player_character,
                        self._get_recent_events_summary(),
                        self._get_objectives_summary(self.player_character)
                    )
                    self._print_color(f"{Colors.CYAN}Dream: \"{dream_text}\"{Colors.RESET}", Colors.CYAN)
                    self.player_character.add_journal_entry("Dream", dream_text, self._get_current_game_time_period_str())
                    self.player_character.add_player_memory(f"Had a disturbing dream: {dream_text[:50]}...")
                    # Affect state based on dream - could be more nuanced
                    if "terror" in dream_text.lower() or "blood" in dream_text.lower() or "axe" in dream_text.lower():
                        self.player_character.apparent_state = random.choice(["paranoid", "agitated", "haunted by dreams"])
                    elif "sonya" in dream_text.lower() or "hope" in dream_text.lower() or "cross" in dream_text.lower():
                        self.player_character.apparent_state = random.choice(["thoughtful", "remorseful", "hopeful"])
                    else:
                        self.player_character.apparent_state = "haunted by dreams"
                    self._print_color(f"(The dream leaves you feeling {self.player_character.apparent_state}.)", Colors.YELLOW)
                    self.last_significant_event_summary = "awoke troubled by a vivid dream."


        current_period = self.get_current_time_period()
        # self._print_color(f"(Time: Day {self.current_day}, {current_period}, Unit: {self.game_time % MAX_TIME_UNITS_PER_DAY})", Colors.MAGENTA) # Can be verbose

        self.time_since_last_npc_interaction += units
        self.time_since_last_npc_schedule_update += units

        if self.time_since_last_npc_schedule_update >= TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE:
            self.update_npc_locations_by_schedule()
            self.time_since_last_npc_schedule_update = 0
            
    # ... (Other helper methods like display_atmospheric_details, initialize_dynamic_location_items etc. as before) ...
    def display_atmospheric_details(self):
        if self.player_character and self.current_location_name:
            details = self.gemini_api.get_atmospheric_details(
                self.player_character,
                self.current_location_name,
                self.get_current_time_period(),
                self.last_significant_event_summary
            )
            if details and not details.startswith("(OOC:"):
                self._print_color(f"\n{details}", Colors.CYAN)
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
                    # Ensure item is not already there (e.g. from a previous initialization or save)
                    if not any(loc_item["name"] == item_name for loc_item in location_items):
                        # For stackable items, quantity might be defined in DEFAULT_ITEMS, otherwise 1
                        qty_to_add = item_props.get("quantity", 1) if item_props.get("stackable", False) or item_props.get("value") is not None else 1
                        location_items.append({"name": item_name, "quantity": qty_to_add})
                else:
                    self._print_color(f"Warning: Location '{hidden_loc}' for hidden item '{item_name}' not found in LOCATIONS_DATA.", Colors.YELLOW)


    def load_all_characters(self, from_save=False):
        if from_save: return 

        self.all_character_objects = {}
        for name, data in CHARACTERS_DATA.items():
            static_data_copy = copy.deepcopy(data) 
            if static_data_copy.get("default_location") not in static_data_copy.get("accessible_locations", []):
                if "accessible_locations" not in static_data_copy: 
                    static_data_copy["accessible_locations"] = []
                static_data_copy["accessible_locations"].append(static_data_copy["default_location"])

            self.all_character_objects[name] = Character(
                name, static_data_copy["persona"], static_data_copy["greeting"], static_data_copy["default_location"], 
                static_data_copy.get("accessible_locations", [static_data_copy["default_location"]]),
                static_data_copy.get("objectives", []),
                static_data_copy.get("inventory_items", []), static_data_copy.get("schedule", {})
            )
        self.initialize_dynamic_location_items() 


    def select_player_character(self):
        # ... (as before)
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
        # ... (as before)
        current_time_period = self.get_current_time_period()
        if current_time_period == "Unknown":
            self._print_color("Warning: NPC schedules not updated due to unknown time period.", Colors.YELLOW)
            return

        moved_npcs_info = []
        for npc_name, npc_obj in self.all_character_objects.items():
            if npc_obj.is_player or not npc_obj.schedule:
                continue
            scheduled_location = npc_obj.schedule.get(current_time_period)
            if scheduled_location and scheduled_location != npc_obj.current_location:
                if scheduled_location in npc_obj.accessible_locations:
                    if random.random() < NPC_MOVE_CHANCE:
                        old_location = npc_obj.current_location
                        npc_obj.current_location = scheduled_location
                        if old_location == self.current_location_name and scheduled_location != self.current_location_name:
                            moved_npcs_info.append(f"{npc_obj.name} has left.")
                        elif scheduled_location == self.current_location_name and old_location != self.current_location_name:
                             moved_npcs_info.append(f"{npc_obj.name} has arrived.")
        if moved_npcs_info:
            self._print_color("\n(As time passes...)", Colors.MAGENTA)
            for info in moved_npcs_info:
                self._print_color(info, Colors.MAGENTA)
        self.update_npcs_in_current_location()


    def update_current_location_details(self, display_atmospherics=True):
        # ... (as before)
        if not self.current_location_name:
            self._print_color("Error: Current location not set. Attempting to recover.", Colors.RED)
            if self.player_character and self.player_character.current_location:
                self.current_location_name = self.player_character.current_location
                self._print_color(f"Recovered current location to: {self.current_location_name}", Colors.YELLOW)
            else:
                self._print_color("Critical Error: Cannot determine current location.", Colors.RED)
                return

        location_data = LOCATIONS_DATA.get(self.current_location_name)
        if not location_data:
            self._print_color(f"Error: Unknown location: {self.current_location_name}. Data missing.", Colors.RED)
            return

        time_str = f"({self._get_current_game_time_period_str()})" # Using helper
        self._print_color(f"\n--- {self.current_location_name} {time_str} ---", Colors.CYAN + Colors.BOLD)

        base_description = location_data.get("description", "A non-descript place.")
        time_effect_desc = location_data.get("time_effects", {}).get(self.get_current_time_period(), "")
        print(base_description + " " + time_effect_desc)

        if display_atmospherics:
            self.display_atmospheric_details()
        self.update_npcs_in_current_location()


    def update_npcs_in_current_location(self):
        # ... (as before)
        self.npcs_in_current_location = []
        if not self.current_location_name: return
        for char_name, char_obj in self.all_character_objects.items():
            if not char_obj.is_player and char_obj.current_location == self.current_location_name:
                if char_obj not in self.npcs_in_current_location:
                    self.npcs_in_current_location.append(char_obj)


    def get_relationship_text(self, score):
        # ... (as before)
        if score > 5: return "very positive"
        if score > 2: return "positive"
        if score < -5: return "very negative"
        if score < -2: return "negative"
        return "neutral"

    def check_conversation_conclusion(self, text):
        # ... (as before)
        for phrase_regex in CONCLUDING_PHRASES:
            if re.search(phrase_regex, text, re.IGNORECASE):
                return True
        return False

    def display_objectives(self):
        # ... (as before)
        self._print_color("\n--- Your Objectives ---", Colors.CYAN + Colors.BOLD)
        if not self.player_character or not self.player_character.objectives:
            print("You have no specific objectives at the moment.")
            return
        has_active = False
        for obj in self.player_character.objectives:
            if obj.get("active", False) and not obj.get("completed", False):
                if not has_active: self._print_color("Ongoing:", Colors.YELLOW)
                has_active = True
                self._print_color(f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE)
                current_stage = self.player_character.get_current_stage_for_objective(obj.get('id'))
                if current_stage:
                    self._print_color(f"  Current Stage: {current_stage.get('description', 'No stage description')}", Colors.CYAN)
        if not has_active:
             print("You have no active objectives right now.")
        completed_objectives = [obj for obj in self.player_character.objectives if obj.get("completed", False)]
        if completed_objectives:
            self._print_color("\nCompleted:", Colors.GREEN)
            for obj in completed_objectives:
                self._print_color(f"- {obj.get('description', 'Unnamed objective')}", Colors.WHITE)


    def display_help(self):
        # ... (as before, but include 'read' if added to synonyms)
        self._print_color("\n--- Available Actions ---", Colors.CYAN + Colors.BOLD)
        actions = [
            ("look / l / examine / observe", "Examine surroundings, see people, items, and exits."),
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
            ("journal / notes", "Review your journal entries (rumors, news, etc.)."), # New command
            ("save", "Save your current game progress."),
            ("load", "Load a previously saved game."),
            ("help / commands", "Show this help message."),
            ("quit / exit / q", "Exit the game.")
        ]
        for cmd, desc in actions:
            self._print_color(f"{cmd:<65} {Colors.WHITE}- {desc}{Colors.RESET}", Colors.MAGENTA)


    def parse_action(self, raw_input):
        # ... (as before, with 'read' parsing)
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

        if " on " in action:
            parts = action.split(" on ", 1)
            potential_cmd_part = parts[0].split(" ", 1)
            cmd_candidate = potential_cmd_part[0]
            item_name_candidate = potential_cmd_part[1] if len(potential_cmd_part) > 1 else None
            target_name = parts[1]
            for base_cmd, synonyms in COMMAND_SYNONYMS.items():
                if base_cmd == "use": 
                    if cmd_candidate == base_cmd or cmd_candidate in synonyms:
                        return base_cmd, (item_name_candidate.strip() if item_name_candidate else None, target_name.strip(), "use_on")

        matched_command = None
        best_match_synonym = ""
        for base_cmd, synonyms in COMMAND_SYNONYMS.items():
            if action == base_cmd or action in synonyms:
                return base_cmd, None
            for syn_to_check in [base_cmd] + synonyms:
                if action.startswith(syn_to_check + " "):
                    if len(syn_to_check) > len(best_match_synonym):
                        matched_command = base_cmd
                        best_match_synonym = syn_to_check
        if matched_command:
            parsed_arg = action[len(best_match_synonym):].strip()
            return matched_command, parsed_arg

        parts = action.split(" ", 1)
        command_candidate = parts[0]
        for base_cmd, synonyms_list in COMMAND_SYNONYMS.items():
            if command_candidate == base_cmd or command_candidate in synonyms_list:
                 # Handle new "journal" command here if it's simple
                if base_cmd == "journal" and (command_candidate == "journal" or command_candidate in synonyms_list.get("journal", [])):
                    return "journal", None
                return base_cmd, parts[1] if len(parts) > 1 else None
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
            # Save new AI-related state
            "player_notoriety_level": self.player_notoriety_level,
            "known_facts_about_crime": self.known_facts_about_crime,
            "key_events_occurred": self.key_events_occurred
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
            # Load new AI-related state
            self.player_notoriety_level = game_state_data.get("player_notoriety_level", 0)
            self.known_facts_about_crime = game_state_data.get("known_facts_about_crime", ["An old pawnbroker and her sister were murdered recently."])
            self.key_events_occurred = game_state_data.get("key_events_occurred", ["Game loaded."])


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
            self.update_current_location_details()
            return True
        except Exception as e:
            self._print_color(f"Error loading game: {e}", Colors.RED)
            self.player_character = None; return False

    def handle_use_item(self, item_name_input, target_name_input=None, interaction_type="use_self_implicit"):
        # ... (Most of handle_use_item logic from previous response remains,
        # ensure it correctly calls the item_props.get("use_effect_player")
        # and handles the new "read" interaction_type for newspapers/notes)

        if not self.player_character:
            self._print_color("Cannot use items: Player character not set.", Colors.RED)
            return False

        item_to_use_name = None
        if item_name_input:
            for inv_item_obj in self.player_character.inventory:
                if inv_item_obj["name"].lower().startswith(item_name_input.lower()):
                    item_to_use_name = inv_item_obj["name"]; break
            if not item_to_use_name:
                self._print_color(f"You don't have '{item_name_input}' to {interaction_type.replace('_', ' ')}.", Colors.RED)
                return False
        elif interaction_type != "use_self_implicit":
             self._print_color(f"What do you want to {interaction_type.replace('_', ' ')}{(' on ' + target_name_input) if target_name_input else ''}?", Colors.RED)
             return False
        
        # If item_to_use_name is still None here, it implies an action like "read" without specifying an item after "read"
        # Or an implicit self-use without a specified item - this case should be rare with current parsing.
        if not item_to_use_name and item_name_input: # Could happen if startswith failed but item_name_input was passed
            item_to_use_name = item_name_input # Try to use the raw input if no inventory match but it was provided

        if not item_to_use_name: # Final check if we truly have no item
            self._print_color("You need to specify an item to use or read.", Colors.RED)
            return False


        item_props = DEFAULT_ITEMS.get(item_to_use_name, {})
        item_obj_in_inventory = next((item for item in self.player_character.inventory if item["name"] == item_to_use_name), None)

        used_successfully = False
        effect_key = item_props.get("use_effect_player")

        # Handle "read" interaction type specifically for readable items
        if interaction_type == "read":
            if not item_props.get("readable"):
                self._print_color(f"You can't read the {item_to_use_name}.", Colors.YELLOW)
                return False
            # Fall through to specific item logic based on effect_key or name
            if item_to_use_name == "old newspaper" or item_to_use_name == "Fresh Newspaper":
                effect_key = "read_evolving_news_article" # Force this effect for read
            elif item_to_use_name == "mother's letter":
                effect_key = "reread_letter_and_feel_familial_pressure"
            elif item_to_use_name == "Sonya's New Testament":
                effect_key = "read_testament_for_solace_or_guilt"
            elif item_to_use_name == "Anonymous Note":
                effect_key = "read_generated_document"
                if item_obj_in_inventory and "generated_content" in item_obj_in_inventory:
                    # Display pre-generated content for this specific note instance
                    self._print_color(f"You read the {item_to_use_name}:", Colors.WHITE)
                    self._print_color(f"\"{item_obj_in_inventory['generated_content']}\"", Colors.CYAN)
                    self.player_character.add_journal_entry("Note", item_obj_in_inventory['generated_content'], self._get_current_game_time_period_str())
                    self.last_significant_event_summary = f"read an {item_to_use_name}."
                    used_successfully = True
                    # Potentially change player state based on note content if desired (e.g. more paranoid)
                    if "watch" in item_obj_in_inventory['generated_content'].lower() or "know" in item_obj_in_inventory['generated_content'].lower():
                        self.player_character.apparent_state = "paranoid"
                    return True # Handled specific AI document
                else: # Should not happen if item was generated correctly
                    self._print_color(f"The {item_to_use_name} seems to be blank or unreadable.", Colors.RED)
                    return False


        # --- Item use logic from previous detailed implementation ---
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
                self._get_objectives_summary(self.player_character) # Raskolnikov's themes for context
            )
            if article_snippet and not article_snippet.startswith("(OOC:"):
                self._print_color(f"An article catches your eye: \"{article_snippet}\"", Colors.YELLOW)
                self.player_character.add_journal_entry("News", article_snippet, self._get_current_game_time_period_str())
                if "crime" in article_snippet.lower() or "investigation" in article_snippet.lower() or "murder" in article_snippet.lower():
                    self.player_character.apparent_state = "thoughtful"
                    if self.player_character.name == "Rodion Raskolnikov":
                        self.player_character.add_player_memory("Read unsettling news about the recent crime.")
                        self.player_notoriety_level = min(self.player_notoriety_level + 0.1, 3) # Slight increase if crime is mentioned
                self.last_significant_event_summary = f"read an {item_to_use_name}."
            else:
                self._print_color("The print is too faded or the news too mundane to hold your interest.", Colors.DIM)
            used_successfully = True


        elif effect_key == "grip_axe_and_reminisce_horror" and item_to_use_name == "Raskolnikov's axe":
            # ... (same as before)
            if self.player_character.name == "Rodion Raskolnikov":
                self._print_color(f"You grip the {item_to_use_name}. Its cold weight is a familiar dread. The memories, sharp and bloody, flood your mind. You feel a wave of nausea, then a chilling resolve, then utter despair.", Colors.RED + Colors.BOLD)
                self.player_character.apparent_state = random.choice(["dangerously agitated", "remorseful", "paranoid"])
                self.last_significant_event_summary = f"held the axe, tormented by memories."
                used_successfully = True
            else: self._print_color(f"You look at the {item_to_use_name}. It's a grim object, heavy and unsettling. Best left alone.", Colors.YELLOW); used_successfully = True
        
        elif effect_key == "read_testament_for_solace_or_guilt" and item_to_use_name == "Sonya's New Testament":
            # ... (same as before)
            self._print_color(f"You open {item_to_use_name}. The familiar words of the Gospels seem to both accuse and offer a sliver of hope.", Colors.GREEN)
            testament_reflection_prompt = f"{self.player_character.name} ({self.player_character.apparent_state}) reads from Sonya's New Testament. Generate a brief (1-2 sentences) Dostoevskian reflection on guilt, suffering, forgiveness, or the story of Lazarus, as Raskolnikov might experience it."
            reflection = self.gemini_api.model.generate_content(testament_reflection_prompt).text.strip() # Simplified direct call
            self._print_color(f"\"{reflection}\"", Colors.CYAN)
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.apparent_state = random.choice(["contemplative", "remorseful", "thoughtful", "hopeful"])
                self.player_character.add_player_memory("Read from the New Testament, stirring deep thoughts of salvation and suffering.")
                obj_grapple = self.player_character.get_objective_by_id("grapple_with_crime")
                if obj_grapple and obj_grapple.get("active") and obj_grapple.get("current_stage_id") in ["seek_sonya", "confessed_to_sonya", "received_cross_from_sonya"]:
                    if self.player_character.get_objective_by_id("ponder_redemption"): # Check if ponder_redemption exists
                       self.player_character.advance_objective_stage("ponder_redemption", "path_to_confession_clearer")
            self.last_significant_event_summary = f"read from {item_to_use_name}."
            used_successfully = True

        elif effect_key == "reflect_on_faith_and_redemption" and item_to_use_name == "Sonya's Cypress Cross":
            # ... (same as before)
            if self.player_character.name == "Rodion Raskolnikov": 
                self._print_color("You clutch the small cypress cross. It feels strangely significant in your hand, a stark contrast to the turmoil within you.", Colors.GREEN)
                self.player_character.apparent_state = random.choice(["remorseful", "contemplative", "hopeful"])
                self.last_significant_event_summary = f"held Sonya's cross, feeling its weight and Sonya's sacrifice."
                obj_ponder = self.player_character.get_objective_by_id("ponder_redemption")
                if obj_ponder:
                    if not obj_ponder.get("active"): self.player_character.activate_objective("ponder_redemption")
                    elif obj_ponder.get("current_stage_id") == "initial_reflection": self.player_character.advance_objective_stage("ponder_redemption", "glimmer_of_hope")
                    elif obj_ponder.get("current_stage_id") == "glimmer_of_hope": self.player_character.advance_objective_stage("ponder_redemption", "path_to_confession_clearer")
                self._print_color(self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, "Holding Sonya's cross, new thoughts about suffering and sacrifice surface.", self.get_current_time_period()), Colors.CYAN)
                used_successfully = True
            else: self._print_color(f"You examine {item_to_use_name}. It seems to be a simple wooden cross, yet it emanates a certain potent feeling.", Colors.YELLOW); used_successfully = True

        elif effect_key == "examine_rag_and_spiral_into_paranoia" and item_to_use_name == "bloodied rag":
            # ... (same as before)
            self._print_color(f"You stare at the {item_to_use_name}. The dark stains seem to shift and spread before your eyes. Every sound, every shadow, feels like an accusation.", Colors.RED)
            self.player_character.apparent_state = "paranoid"
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.add_player_memory("The sight of the bloodied rag brought a fresh wave of paranoia.")
                self.player_notoriety_level = min(self.player_notoriety_level + 0.5, 3) # Examining evidence is risky
            self.last_significant_event_summary = f"was deeply disturbed by a {item_to_use_name}."
            used_successfully = True
        
        elif effect_key == "reread_letter_and_feel_familial_pressure" and item_to_use_name == "mother's letter":
            # ... (same as before)
            self._print_color(f"You re-read your mother's letter. Her words of love and anxiety, Dunya's predicament... it all weighs heavily on you.", Colors.YELLOW)
            letter_reflection_prompt = f"{self.player_character.name} ({self.player_character.apparent_state}) re-reads the letter from his mother detailing family troubles and Dunya's engagement. Generate a short, poignant internal reflection (1-2 sentences) about his feelings of responsibility, guilt, or protectiveness."
            reflection = self.gemini_api.model.generate_content(letter_reflection_prompt).text.strip() # Simplified direct call
            self._print_color(f"\"{reflection}\"", Colors.CYAN)
            self.player_character.apparent_state = random.choice(["burdened", "agitated", "resolved"])
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.add_player_memory("Re-reading mother's letter intensified feelings of duty and distress.")
            self.last_significant_event_summary = f"re-read the {item_to_use_name}."
            used_successfully = True

        elif effect_key == "drink_vodka_for_oblivion" and item_to_use_name == "cheap vodka":
            # ... (same as before)
            self._print_color(f"You take a long swig of the harsh vodka. It burns on the way down, offering a brief, false warmth and a dulling of the senses.", Colors.MAGENTA)
            self.player_character.apparent_state = "slightly drunk"
            if self.player_character.has_item("cheap vodka"):
                self.player_character.remove_from_inventory("cheap vodka", 1)
            self.last_significant_event_summary = "drank some cheap vodka to numb the thoughts."
            if self.player_character.apparent_state == "feverish":
                self.player_character.apparent_state = "agitated"; self._print_color("The vodka clashes terribly with your fever, making you feel worse.", Colors.RED)
            used_successfully = True
        
        elif effect_key == "examine_bundle_and_face_guilt_for_Lizaveta" and item_to_use_name == "Lizaveta's bundle":
            # ... (same as before)
            self._print_color(f"You hesitantly open {item_to_use_name}. Inside are a few pitiful belongings: a worn shawl, a child's small wooden toy, a copper coin... The sight is a fresh stab of guilt for the gentle Lizaveta.", Colors.YELLOW)
            if self.player_character.name == "Rodion Raskolnikov":
                self.player_character.apparent_state = "remorseful"
                self.player_character.add_player_memory("Examined Lizaveta's bundle; the innocence of the items was a heavy burden.")
            self.last_significant_event_summary = f"examined Lizaveta's bundle, increasing the weight of guilt."
            used_successfully = True

        # Handle "give" interaction type for "worn coin"
        elif item_to_use_name == "worn coin" and interaction_type == "give" and target_name_input:
            target_npc = next((npc for npc in self.npcs_in_current_location if npc.name.lower().startswith(target_name_input.lower())), None)
            if target_npc:
                if self.player_character.remove_from_inventory("worn coin", 1):
                    self._print_color(f"You offer a coin to {target_npc.name}.", Colors.WHITE)
                    reaction = self.gemini_api.get_npc_dialogue(target_npc, self.player_character, f"(Offers a coin out of {random.choice(['pity', 'a sudden impulse', 'a desire to help', 'unease'])}.)", self.current_location_name, self.get_relationship_text(target_npc.relationship_with_player), target_npc.get_player_memory_summary(), self.player_character.apparent_state, self.player_character.get_notable_carried_items_summary())
                    self._print_color(f"{target_npc.name}: \"{reaction}\"", Colors.YELLOW)
                    target_npc.relationship_with_player += 1
                    self.last_significant_event_summary = f"gave a coin to {target_npc.name}."
                    used_successfully = True
                else: self._print_color("You rummage through your pockets but find no coins to give.", Colors.RED)
            else: self._print_color(f"You don't see '{target_name_input}' here to give a coin to.", Colors.RED)

        # Default fallback
        if not used_successfully:
            if target_name_input and interaction_type != "give": # "use item on target"
                self._print_color(f"You try to use the {item_to_use_name} on {target_name_input}, but nothing specific happens.", Colors.YELLOW)
            elif interaction_type != "give": # "use item" (implicitly on self) or "read item" with no specific handler
                self._print_color(f"You contemplate the {item_to_use_name}, but don't find a specific use for it right now.", Colors.YELLOW)
            # "give" already has fallback if target not found or no coins.
            return False

        if used_successfully and item_props.get("consumable", False) and not (item_to_use_name == "cheap vodka"):
            if self.player_character.remove_from_inventory(item_to_use_name, 1):
                self._print_color(f"The {item_to_use_name} is used up.", Colors.MAGENTA)
        return True

    def run(self):
        # ... (Setup from previous, including API config, character load/select) ...
        self.gemini_api.configure(self._print_color, self._input_color)
        self._print_color("\n--- Crime and Punishment: A Text Adventure ---", Colors.CYAN + Colors.BOLD)
        self._print_color("Type 'load' to load a saved game, or press Enter to start a new game.", Colors.MAGENTA)
        initial_action = self._input_color(f"{self.game_config.PROMPT_ARROW}", Colors.WHITE).strip().lower()

        game_loaded_successfully = False
        if initial_action == "load":
            if self.load_game(): game_loaded_successfully = True
            else: self._print_color("Failed to load game. Starting a new game instead.", Colors.YELLOW)
        
        if not game_loaded_successfully:
            self.load_all_characters()
            if not self.select_player_character():
                self._print_color("Critical Error: Could not initialize player character. Exiting.", Colors.RED); return
        
        if not self.player_character or not self.current_location_name:
            self._print_color("Game initialization failed critically. Exiting.", Colors.RED); return

        if not game_loaded_successfully: self.update_current_location_details()
        self._print_color("\n--- Game Start ---", Colors.CYAN + Colors.BOLD)
        self.display_help()

        while True:
            current_location_data = LOCATIONS_DATA.get(self.current_location_name)
            if not current_location_data:
                 self._print_color(f"Critical Error: Current location '{self.current_location_name}' data not found. Exiting.", Colors.RED); break

            # Ambient Rumor Check (before player prompt)
            if self.current_location_name in ["Haymarket Square", "Tavern"] and random.random() < AMBIENT_RUMOR_CHANCE_PUBLIC_PLACE:
                # Pick a random NPC in the location (if any) to be the "source" or just general ambiance
                source_npc = random.choice(self.npcs_in_current_location) if self.npcs_in_current_location else None
                rumor_text = self.gemini_api.get_rumor_or_gossip(
                    source_npc if source_npc else Character("A Passerby", "A typical St. Petersburg citizen.", "", self.current_location_name, []), # Dummy NPC if none present
                    self.current_location_name,
                    self._get_known_facts_summary(),
                    self.player_notoriety_level
                )
                if rumor_text and not rumor_text.startswith("(OOC:"):
                    self._print_color(f"\n{Colors.DIM}(You overhear some chatter nearby: \"{rumor_text}\"){Colors.RESET}", Colors.DIM)
                    self.player_character.add_journal_entry("Overheard Rumor", rumor_text, self._get_current_game_time_period_str())
                    if self.player_character.name == "Rodion Raskolnikov" and any(kw in rumor_text.lower() for kw in ["student", "axe", "pawnbroker", "murder", "police"]):
                        self.player_character.apparent_state = "paranoid"
                        self.player_notoriety_level = min(self.player_notoriety_level + 0.2, 3)


            player_state_info = f"{self.player_character.apparent_state}" if self.player_character else "Unknown state"
            prompt_text = f"\n[{Colors.CYAN}{self.current_location_name}{Colors.RESET} ({player_state_info})] What do you do? {self.game_config.PROMPT_ARROW}"
            raw_action_input = self._input_color(prompt_text, Colors.WHITE)
            command, argument = self.parse_action(raw_action_input)

            if command is None and argument is None: continue

            action_taken_this_turn = True
            time_to_advance = TIME_UNITS_PER_PLAYER_ACTION
            display_atmospherics_after_action = True


            if command == "quit": self._print_color("Exiting game. Goodbye.", Colors.MAGENTA); break
            elif command == "save": self.save_game(); action_taken_this_turn = False
            elif command == "load": self.load_game(); action_taken_this_turn = False; display_atmospherics_after_action = False; continue
            elif command == "help": self.display_help(); action_taken_this_turn = False
            elif command == "journal":
                self._print_color(self.player_character.get_journal_summary(), Colors.CYAN)
                action_taken_this_turn = False


            elif command == "look":
                self.update_current_location_details(display_atmospherics=True); display_atmospherics_after_action = False
                # ... (rest of look command as before, including look at item/NPC) ...
                if argument: # look at [target]
                    target_to_look_at = argument.lower(); found_target = False
                    # 1. Items in room
                    for item_info in self.dynamic_location_items.get(self.current_location_name, []):
                        if item_info["name"].lower().startswith(target_to_look_at):
                            item_default = DEFAULT_ITEMS.get(item_info["name"])
                            if item_default:
                                self._print_color(f"You examine the {item_info['name']}:", Colors.GREEN)
                                gen_desc = self.gemini_api.get_item_interaction_description(self.player_character, item_info['name'], item_default, "examine closely in environment")
                                self._print_color(f"\"{gen_desc}\"", Colors.GREEN if not gen_desc.startswith("(OOC:") else Colors.YELLOW)
                                found_target = True; break
                    # 2. Items in inventory
                    if not found_target and self.player_character:
                        for inv_item_info in self.player_character.inventory:
                             if inv_item_info["name"].lower().startswith(target_to_look_at):
                                item_default = DEFAULT_ITEMS.get(inv_item_info["name"])
                                if item_default:
                                    self._print_color(f"You examine your {inv_item_info['name']}:", Colors.GREEN)
                                    gen_desc = self.gemini_api.get_item_interaction_description(self.player_character, inv_item_info['name'], item_default, "examine closely from inventory")
                                    self._print_color(f"\"{gen_desc}\"", Colors.GREEN if not gen_desc.startswith("(OOC:") else Colors.YELLOW)
                                    found_target = True; break
                    # 3. NPCs
                    if not found_target:
                        for npc in self.npcs_in_current_location:
                            if npc.name.lower().startswith(target_to_look_at):
                                self._print_color(f"You look closely at {Colors.YELLOW}{npc.name}{Colors.RESET} (appears {npc.apparent_state}):", Colors.WHITE)
                                observation = self.gemini_api.get_player_reflection(self.player_character, f"observing {npc.name} in {self.current_location_name}", f"You are trying to discern more about {npc.name}'s demeanor and thoughts. They appear to be '{npc.apparent_state}'. You recall: {npc.get_player_memory_summary()}", self.get_current_time_period())
                                self._print_color(f"\"{observation}\"", Colors.GREEN if not observation.startswith("(OOC:") else Colors.YELLOW)
                                found_target = True; break
                    # 4. Generic Scenery
                    if not found_target:
                        # Check if argument matches any part of location description or generic keywords
                        loc_desc_lower = LOCATIONS_DATA.get(self.current_location_name, {}).get("description", "").lower()
                        is_scenery = any(keyword in target_to_look_at for keyword in GENERIC_SCENERY_KEYWORDS) or target_to_look_at in loc_desc_lower

                        if is_scenery: # Simplified check, can be more robust
                            self._print_color(f"You focus on the {target_to_look_at}...", Colors.WHITE)
                            observation = self.gemini_api.get_scenery_observation(
                                self.player_character, target_to_look_at,
                                self.current_location_name, self.get_current_time_period()
                            )
                            if observation and not observation.startswith("(OOC:"):
                                self._print_color(f"\"{observation}\"", Colors.CYAN)
                                found_target = True
                            else:
                                self._print_color(f"The {target_to_look_at} offers no particular insight beyond its mundane presence.", Colors.DIM)
                                found_target = True # Still counts as looking
                        
                    if not found_target: self._print_color(f"You don't see '{argument}' here to look at specifically.", Colors.RED)
                # Display items, NPCs, exits (as before)
                current_loc_items = self.dynamic_location_items.get(self.current_location_name, [])
                if current_loc_items:
                    self._print_color("\nYou also see here:", Colors.YELLOW)
                    for item_info in current_loc_items:
                        item_name = item_info["name"]; item_qty = item_info.get("quantity", 1)
                        item_default_info = DEFAULT_ITEMS.get(item_name, {})
                        desc_snippet = item_default_info.get('description', 'an item')[:40]
                        qty_str = f" (x{item_qty})" if (item_default_info.get("stackable") or item_default_info.get("value") is not None) and item_qty > 1 else ""
                        print(f"- {Colors.GREEN}{item_name}{Colors.RESET}{qty_str} - {desc_snippet}...")
                else: print("\nYou see no loose items of interest here.")
                if self.npcs_in_current_location:
                    self._print_color("\nPeople here:", Colors.YELLOW)
                    for npc in self.npcs_in_current_location: print(f"- {Colors.YELLOW}{npc.name}{Colors.RESET} (Appears: {npc.apparent_state}, Relationship: {self.get_relationship_text(npc.relationship_with_player)})")
                else: print("\nYou see no one else of note here.")
                self._print_color("\nExits:", Colors.BLUE)
                has_accessible_exits = False
                if current_location_data.get("exits"):
                    for exit_target_loc, exit_desc in current_location_data["exits"].items():
                        if self.player_character and exit_target_loc in self.player_character.accessible_locations:
                            print(f"- {Colors.BLUE}{exit_desc} (to {Colors.CYAN}{exit_target_loc}{Colors.BLUE}){Colors.RESET}"); has_accessible_exits = True
                if not has_accessible_exits: print(f"{Colors.BLUE}There are no exits you can use from here.{Colors.RESET}")
                action_taken_this_turn = True


            # ... (inventory, take, drop, use, objectives, think, wait, talk to, move to commands mostly as before,
            # but ensuring they call the updated handle_use_item and that talk_to might trigger rumors) ...
            elif command == "inventory": # from before
                if self.player_character: self._print_color("\n--- Your Inventory ---", Colors.CYAN + Colors.BOLD); print(self.player_character.get_inventory_description())
                else: self._print_color("Cannot display inventory: Player character not available.", Colors.RED)
                action_taken_this_turn = False

            elif command == "take": # from before
                if not argument: self._print_color("What do you want to take?", Colors.RED); action_taken_this_turn = False
                elif not self.player_character: self._print_color("Cannot take items: Player character not available.", Colors.RED); action_taken_this_turn = False
                else:
                    item_to_take_name = argument.lower()
                    location_items = self.dynamic_location_items.get(self.current_location_name, [])
                    item_found_in_loc = None; item_idx_in_loc = -1
                    for idx, item_info in enumerate(location_items):
                        if item_info["name"].lower().startswith(item_to_take_name): item_found_in_loc = item_info; item_idx_in_loc = idx; break
                    if item_found_in_loc:
                        item_default_props = DEFAULT_ITEMS.get(item_found_in_loc["name"], {})
                        if item_default_props.get("takeable", False):
                            take_quantity = 1 
                            actual_taken_qty = 0
                            if item_default_props.get("stackable") or item_default_props.get("value") is not None:
                                current_qty_in_loc = item_found_in_loc.get("quantity", 1)
                                actual_taken_qty = min(take_quantity, current_qty_in_loc)
                                item_found_in_loc["quantity"] -= actual_taken_qty
                                if item_found_in_loc["quantity"] <= 0: location_items.pop(item_idx_in_loc)
                            else: actual_taken_qty = 1; location_items.pop(item_idx_in_loc)
                            if self.player_character.add_to_inventory(item_found_in_loc["name"], actual_taken_qty):
                                self._print_color(f"You take the {item_found_in_loc['name']}" + (f" (x{actual_taken_qty})" if actual_taken_qty > 1 and (item_default_props.get("stackable") or item_default_props.get("value") is not None) else "") + ".", Colors.GREEN)
                                self.last_significant_event_summary = f"took the {item_found_in_loc['name']}."
                                if item_default_props.get("is_notable"): self.player_character.apparent_state = random.choice(["thoughtful", "burdened"])
                            else: self._print_color(f"Failed to add {item_found_in_loc['name']} to inventory.", Colors.RED); action_taken_this_turn = False
                        else: self._print_color(f"You can't take the {item_found_in_loc['name']}.", Colors.YELLOW); action_taken_this_turn = False
                    else: self._print_color(f"You don't see any '{item_to_take_name}' here to take.", Colors.RED); action_taken_this_turn = False

            elif command == "drop": # from before
                if not argument: self._print_color("What do you want to drop?", Colors.RED); action_taken_this_turn = False
                elif not self.player_character: self._print_color("Cannot drop items: Player character not available.", Colors.RED); action_taken_this_turn = False
                else:
                    item_to_drop_name_input = argument.lower()
                    item_in_inventory_obj = None
                    for inv_item in self.player_character.inventory:
                        if inv_item["name"].lower().startswith(item_to_drop_name_input): item_in_inventory_obj = inv_item; break
                    if item_in_inventory_obj:
                        item_name_to_drop = item_in_inventory_obj["name"]
                        item_default_props = DEFAULT_ITEMS.get(item_name_to_drop, {})
                        drop_quantity = 1 
                        if self.player_character.remove_from_inventory(item_name_to_drop, drop_quantity):
                            location_items = self.dynamic_location_items.setdefault(self.current_location_name, [])
                            existing_loc_item = None
                            for loc_item in location_items:
                                if loc_item["name"] == item_name_to_drop: existing_loc_item = loc_item; break
                            if existing_loc_item and (item_default_props.get("stackable") or item_default_props.get("value") is not None):
                                existing_loc_item["quantity"] = existing_loc_item.get("quantity", 0) + drop_quantity
                            else: location_items.append({"name": item_name_to_drop, "quantity": drop_quantity})
                            self._print_color(f"You drop the {item_name_to_drop}.", Colors.GREEN)
                            self.last_significant_event_summary = f"dropped the {item_name_to_drop}."
                        else: self._print_color(f"You try to drop {item_name_to_drop}, but something is wrong.", Colors.RED); action_taken_this_turn = False
                    else: self._print_color(f"You don't have '{item_to_drop_name_input}' to drop.", Colors.RED); action_taken_this_turn = False

            elif command == "use":
                if not self.player_character: self._print_color("Cannot use items: Player character not available.", Colors.RED); action_taken_this_turn = False
                elif isinstance(argument, tuple): 
                    item_name_input, target_name_input, interaction_mode = argument
                    action_taken_this_turn = self.handle_use_item(item_name_input, target_name_input, interaction_mode)
                elif argument: 
                    action_taken_this_turn = self.handle_use_item(argument, None, "use_self_implicit")
                else: self._print_color("What do you want to use or read?", Colors.RED); action_taken_this_turn = False
            
            elif command == "objectives": self.display_objectives(); action_taken_this_turn = False
            elif command == "think": # from before
                if not self.player_character: self._print_color("Cannot think: Player character not available.", Colors.RED); action_taken_this_turn = False
                else:
                    self._print_color("You pause to reflect...", Colors.MAGENTA)
                    # ... (rest of think logic using helpers)
                    full_reflection_context = self._get_objectives_summary(self.player_character) + \
                                            f"\n{self.player_character.get_inventory_description()}" + \
                                            f"\nYour current apparent state is '{self.player_character.apparent_state}'." + \
                                            f"\nRecent notable events: {self._get_recent_events_summary()}"
                    reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, full_reflection_context, self.get_current_time_period())
                    self._print_color(f"Inner thought: \"{reflection}\"", Colors.GREEN if not reflection.startswith("(OOC:") else Colors.YELLOW)
                    self.last_significant_event_summary = "was lost in thought."
                    if not reflection.startswith("(OOC:"):
                        if any(kw in reflection.lower() for kw in ["paranoia", "fear", "fever", "panic", "torment", "watched"]): self.player_character.apparent_state = random.choice(["agitated", "feverish", "suspiciously calm", "paranoid"])
                        elif any(kw in reflection.lower() for kw in ["hope", "calm", "peace", "resolve", "clarity", "faith", "confess"]): self.player_character.apparent_state = random.choice(["calm", "contemplative", "resolved", "less feverish", "hopeful"])

            elif command == "wait": # Updated for dream chance
                self._print_color("You wait for a while, observing the flow of life around you, or perhaps lost in your own troubled thoughts...", Colors.MAGENTA)
                time_to_advance = TIME_UNITS_PER_PLAYER_ACTION * random.randint(3, 6) # Longer wait
                self.last_significant_event_summary = "waited, letting time and thoughts drift."
                
                # Dream sequence check for Raskolnikov during long wait if troubled
                if self.player_character and self.player_character.name == "Rodion Raskolnikov":
                    troubled_states = ["feverish", "dangerously agitated", "remorseful", "paranoid", "haunted by dreams", "agitated"]
                    if self.player_character.apparent_state in troubled_states and random.random() < DREAM_CHANCE_TROUBLED_STATE * 0.5: # Reduced chance for wait vs new day
                        self._print_color(f"\n{Colors.MAGENTA}As you drift in uncomfortable idleness, your mind conjures unsettling images...{Colors.RESET}", Colors.MAGENTA)
                        dream_text = self.gemini_api.get_dream_sequence(
                            self.player_character,
                            self._get_recent_events_summary(),
                            self._get_objectives_summary(self.player_character)
                        )
                        self._print_color(f"{Colors.CYAN}Vision: \"{dream_text}\"{Colors.RESET}", Colors.CYAN)
                        self.player_character.add_journal_entry("Waking Dream/Vision", dream_text, self._get_current_game_time_period_str())
                        self.player_character.add_player_memory(f"Had a troubling vision while waiting: {dream_text[:50]}...")
                        self.player_character.apparent_state = "haunted by dreams"
                        self._print_color(f"(The vision leaves you feeling {self.player_character.apparent_state}.)", Colors.YELLOW)
                        self.last_significant_event_summary = "was plagued by a waking vision."

                if self.player_character.apparent_state in ["agitated", "feverish", "dangerously agitated", "slightly drunk", "paranoid"]:
                    if random.random() < 0.3:
                        new_states = {"agitated": "normal", "feverish": "less feverish", "dangerously agitated": "agitated", "slightly drunk": "normal", "paranoid": "suspiciously calm"}
                        old_state = self.player_character.apparent_state
                        self.player_character.apparent_state = new_states.get(old_state, "normal")
                        if old_state != self.player_character.apparent_state: self._print_color(f"(You feel a bit {self.player_character.apparent_state} now.)", Colors.CYAN)
            
            elif command == "talk to": # Updated for rumor chance
                # ... (target NPC selection as before) ...
                if not argument: self._print_color("Who do you want to talk to?", Colors.RED); action_taken_this_turn = False
                elif not self.npcs_in_current_location: print("There's no one here to talk to."); action_taken_this_turn = False
                elif not self.player_character: self._print_color("Cannot talk: Player character not available.", Colors.RED); action_taken_this_turn = False
                else:
                    target_name_input = argument; target_npc = None
                    for npc_obj in self.npcs_in_current_location:
                        if npc_obj.name.lower() == target_name_input.lower(): target_npc = npc_obj; break
                    if not target_npc:
                        for npc_obj in self.npcs_in_current_location:
                            if npc_obj.name.lower().startswith(target_name_input.lower()): target_npc = npc_obj; break
                    if target_npc:
                        self._print_color(f"\nYou approach {Colors.YELLOW}{target_npc.name}{Colors.RESET} (appears {target_npc.apparent_state}).", Colors.WHITE)
                        # ... (greeting and conversation loop as before) ...
                        conversation_active = True
                        first_exchange = True
                        while conversation_active:
                            # Rumor chance on first exchange or periodically
                            if first_exchange or random.random() < RUMOR_CHANCE_PER_NPC_INTERACTION * 0.2: # Lower chance after first exchange
                                if target_npc.relationship_with_player >= NPC_SHARE_RUMOR_MIN_RELATIONSHIP and \
                                   self.current_location_name in ["Haymarket Square", "Tavern"]: # Only in public-ish places
                                    rumor_text = self.gemini_api.get_rumor_or_gossip(
                                        target_npc, self.current_location_name,
                                        self._get_known_facts_summary(), self.player_notoriety_level
                                    )
                                    if rumor_text and not rumor_text.startswith("(OOC:"):
                                        self._print_color(f"{target_npc.name} leans in conspiratorially: \"{Colors.DIM}{rumor_text}{Colors.RESET}\"", Colors.YELLOW)
                                        self.player_character.add_journal_entry("Rumor from " + target_npc.name, rumor_text, self._get_current_game_time_period_str())
                                        if self.player_character.name == "Rodion Raskolnikov" and any(kw in rumor_text.lower() for kw in ["student", "axe", "crime", "police", "murder"]):
                                            self.player_character.apparent_state = random.choice(["paranoid", "intrigued by rumors"])
                                            self.player_notoriety_level = min(self.player_notoriety_level + 0.3, 3) # Rumors about him increase notoriety
                                        self.last_significant_event_summary = f"heard a rumor from {target_npc.name}."
                            first_exchange = False
                            
                            player_apparent_state_info = f" ({self.player_character.apparent_state})" if self.player_character.apparent_state != "normal" else ""
                            player_dialogue = self._input_color(f"You ({Colors.GREEN}{self.player_character.name}{Colors.RESET}{player_apparent_state_info}): {self.game_config.PROMPT_ARROW}", Colors.GREEN).strip()
                            # ... (rest of dialogue handling as before) ...
                            if player_dialogue.lower() in ["leave", "goodbye", "end chat", "back", "enough", "farewell"]:
                                self._print_color(f"You end the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.", Colors.WHITE)
                                target_npc.add_to_history(self.player_character.name, self.player_character.name, "(Leaves the conversation)")
                                self.player_character.add_to_history(target_npc.name, self.player_character.name, "(Leaves the conversation)")
                                self.last_significant_event_summary = f"ended a conversation with {target_npc.name}."
                                conversation_active = False; break
                            if not player_dialogue: self._print_color("You remain silent for a moment.", Colors.DIM); continue
                            self._print_color("Thinking...", Colors.DIM + Colors.MAGENTA)
                            player_items_summary = self.player_character.get_notable_carried_items_summary()
                            ai_response = self.gemini_api.get_npc_dialogue(target_npc, self.player_character, player_dialogue, self.current_location_name, self.get_relationship_text(target_npc.relationship_with_player), target_npc.get_player_memory_summary(), self.player_character.apparent_state, player_items_summary)
                            target_npc.update_relationship(player_dialogue, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS)
                            self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end=""); print(f"\"{ai_response}\"")
                            self.last_significant_event_summary = f"spoke with {target_npc.name} who said: \"{ai_response[:50]}...\""
                            if self.check_conversation_conclusion(ai_response) or self.check_conversation_conclusion(player_dialogue):
                                self._print_color(f"\nThe conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET} seems to have concluded.", Colors.MAGENTA)
                                target_npc.add_to_history(self.player_character.name, "System", "(Conversation concludes naturally)")
                                self.player_character.add_to_history(target_npc.name, "System", "(Conversation concludes naturally)")
                                conversation_active = False
                            self.advance_time(TIME_UNITS_PER_PLAYER_ACTION)
                            if self.event_manager.check_and_trigger_events(): self.last_significant_event_summary = "an event occurred during conversation."
                        action_taken_this_turn = True
                    else: self._print_color(f"You don't see anyone named '{target_name_input}' here to talk to.", Colors.RED); action_taken_this_turn = False


            elif command == "move to": # from before
                if not argument: self._print_color("Where do you want to move to?", Colors.RED); action_taken_this_turn = False
                elif not self.player_character: self._print_color("Cannot move: Player character not available.", Colors.RED); action_taken_this_turn = False
                else:
                    target_exit_input = argument.lower(); moved = False; potential_target_loc_name = None
                    location_exits = current_location_data.get("exits", {})
                    for target_loc_key_exact in location_exits.keys():
                        if target_loc_key_exact.lower() == target_exit_input: potential_target_loc_name = target_loc_key_exact; break
                    if not potential_target_loc_name:
                        for target_loc_key_startswith in location_exits.keys():
                            if target_loc_key_startswith.lower().startswith(target_exit_input): potential_target_loc_name = target_loc_key_startswith; break
                    if not potential_target_loc_name:
                        for target_loc_key_desc, desc_text in location_exits.items():
                            if desc_text.lower().startswith(target_exit_input): potential_target_loc_name = target_loc_key_desc; break
                    if potential_target_loc_name:
                        if potential_target_loc_name in self.player_character.accessible_locations:
                            old_location = self.current_location_name
                            self.current_location_name = potential_target_loc_name
                            self.player_character.current_location = potential_target_loc_name
                            self.last_significant_event_summary = f"moved from {old_location} to {self.current_location_name}."
                            self.update_current_location_details(display_atmospherics=True); display_atmospherics_after_action = False; moved = True
                        else: self._print_color(f"You consider going to {Colors.CYAN}{potential_target_loc_name}{Colors.RESET}, but it doesn't feel right or possible for you to go there now.", Colors.YELLOW); action_taken_this_turn = False
                    else: self._print_color(f"You can't find a way to '{target_exit_input}' from here or it's not a known destination.", Colors.RED); action_taken_this_turn = False
            else: self._print_color(f"Unknown command: '{command}'. Type 'help' for a list of actions.", Colors.RED); action_taken_this_turn = False


            if action_taken_this_turn:
                if command != "talk to": self.advance_time(time_to_advance)
                event_triggered = self.event_manager.check_and_trigger_events()
                if event_triggered:
                    # Add event description to key_events_occurred
                    # Event manager should set self.last_significant_event_summary
                    # which can then be added to self.key_events_occurred if appropriate.
                    if self.last_significant_event_summary and self.last_significant_event_summary not in self.key_events_occurred[-3:]: # Avoid too much repetition
                        self.key_events_occurred.append(self.last_significant_event_summary)
                        if len(self.key_events_occurred) > 10: self.key_events_occurred.pop(0) # Keep list manageable


                if command != "talk to" and self.time_since_last_npc_interaction >= TIME_UNITS_FOR_NPC_INTERACTION_CHANCE:
                    if len(self.npcs_in_current_location) >= 2 and random.random() < NPC_INTERACTION_CHANCE:
                        if self.event_manager.attempt_npc_npc_interaction(): self.last_significant_event_summary = "overheard an exchange between NPCs."
                    self.time_since_last_npc_interaction = 0
            if display_atmospherics_after_action and action_taken_this_turn and command not in ["load"]: self.display_atmospheric_details()
            elif command == "load": self.last_significant_event_summary = None

            # Game ending condition check (as before)
            if self.player_character and self.player_character.name == "Rodion Raskolnikov":
                obj_grapple = self.player_character.get_objective_by_id("grapple_with_crime")
                if obj_grapple and obj_grapple.get("completed", False):
                    current_stage = self.player_character.get_current_stage_for_objective("grapple_with_crime")
                    if current_stage and current_stage.get("is_ending_stage"):
                        self._print_color(f"\n--- The story of {self.player_character.name} has reached a conclusion ({current_stage.get('description', 'an end')}) ---", Colors.CYAN + Colors.BOLD); break