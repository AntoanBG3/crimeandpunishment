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
                         DEFAULT_ITEMS, COMMAND_SYNONYMS, PLAYER_APPARENT_STATES) # Added PLAYER_APPARENT_STATES
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
        self.last_significant_event_summary = None # For atmospheric details

    def _print_color(self, text, color_code, end="\n"):
        print(f"{color_code}{text}{Colors.RESET}", end=end)

    def _input_color(self, prompt_text, color_code):
        return input(f"{color_code}{prompt_text}{Colors.RESET}")

    def get_current_time_period(self):
        time_in_day = self.game_time % MAX_TIME_UNITS_PER_DAY
        for period, (start, end) in TIME_PERIODS.items():
            if start <= time_in_day <= end:
                return period
        return "Unknown" 

    def advance_time(self, units=TIME_UNITS_PER_PLAYER_ACTION):
        self.game_time += units
        if (self.game_time // MAX_TIME_UNITS_PER_DAY) + 1 > self.current_day:
            self.current_day = (self.game_time // MAX_TIME_UNITS_PER_DAY) + 1
            self._print_color(f"\nA new day dawns. It is Day {self.current_day}.", Colors.CYAN + Colors.BOLD)
            # Potentially reset daily limits or trigger daily events here
        
        current_period = self.get_current_time_period()
        self._print_color(f"(Time: Day {self.current_day}, {current_period}, Unit: {self.game_time % MAX_TIME_UNITS_PER_DAY})", Colors.MAGENTA)
        
        self.time_since_last_npc_interaction += units
        self.time_since_last_npc_schedule_update += units

        if self.time_since_last_npc_schedule_update >= TIME_UNITS_FOR_NPC_SCHEDULE_UPDATE:
            self.update_npc_locations_by_schedule()
            self.time_since_last_npc_schedule_update = 0

    def display_atmospheric_details(self):
        """Gets and displays atmospheric details from Gemini."""
        if self.player_character and self.current_location_name:
            details = self.gemini_api.get_atmospheric_details(
                self.player_character,
                self.current_location_name,
                self.get_current_time_period(),
                self.last_significant_event_summary 
            )
            if details:
                self._print_color(f"\n{details}", Colors.CYAN)
            self.last_significant_event_summary = None # Reset after displaying


    def initialize_dynamic_location_items(self):
        self.dynamic_location_items = {}
        for loc_name, loc_data in LOCATIONS_DATA.items():
            self.dynamic_location_items[loc_name] = copy.deepcopy(loc_data.get("items_present", []))
        
        for item_name, item_props in DEFAULT_ITEMS.items():
            if "hidden_in_location" in item_props and item_props["hidden_in_location"] in self.dynamic_location_items:
                location_items = self.dynamic_location_items[item_props["hidden_in_location"]]
                if not any(loc_item["name"] == item_name for loc_item in location_items):
                    location_items.append({"name": item_name, "quantity": item_props.get("quantity", 1)})


    def load_all_characters(self, from_save=False):
        if from_save: return 

        self.all_character_objects = {}
        for name, data in CHARACTERS_DATA.items():
            if data["default_location"] not in data["accessible_locations"]:
                data["accessible_locations"].append(data["default_location"])

            self.all_character_objects[name] = Character(
                name, data["persona"], data["greeting"], data["default_location"], 
                data["accessible_locations"], data.get("objectives", []),
                data.get("inventory_items", []), data.get("schedule", {})
            )
            # Initialize player character's apparent state if they are Raskolnikov (prone to fever)
            if name == "Rodion Raskolnikov":
                 self.all_character_objects[name].apparent_state = random.choice(["normal", "feverish", "agitated"])


        self.initialize_dynamic_location_items() 


    def select_player_character(self):
        self._print_color("\n--- Choose Your Character ---", Colors.CYAN + Colors.BOLD)
        character_names = list(CHARACTERS_DATA.keys())
        for i, name in enumerate(character_names):
            print(f"{Colors.MAGENTA}{i + 1}. {Colors.WHITE}{name}{Colors.RESET}")

        while True:
            try:
                choice_str = self._input_color("Enter the number of your choice: ", Colors.MAGENTA)
                choice = int(choice_str) - 1
                if 0 <= choice < len(character_names):
                    chosen_name = character_names[choice]
                    self.player_character = self.all_character_objects[chosen_name]
                    self.player_character.is_player = True
                    self.current_location_name = self.player_character.default_location 
                    self.player_character.current_location = self.current_location_name 
                    
                    self._print_color(f"\nYou are playing as {Colors.GREEN}{self.player_character.name}{Colors.RESET}.", Colors.WHITE)
                    self._print_color(f"You start in: {Colors.CYAN}{self.current_location_name}{Colors.RESET}", Colors.WHITE)
                    self._print_color(f"Your current state appears: {Colors.YELLOW}{self.player_character.apparent_state}{Colors.RESET}.", Colors.WHITE)
                    break
                else:
                    self._print_color("Invalid choice. Please enter a number from the list.", Colors.RED)
            except ValueError:
                self._print_color("Invalid input. Please enter a number.", Colors.RED)

    def update_npc_locations_by_schedule(self):
        current_time_period = self.get_current_time_period()
        moved_npcs_info = [] # To store info about NPCs who moved relevant to player
        for npc_name, npc_obj in self.all_character_objects.items():
            if npc_obj.is_player or not npc_obj.schedule:
                continue

            scheduled_location = npc_obj.schedule.get(current_time_period)
            if scheduled_location and scheduled_location != npc_obj.current_location:
                if scheduled_location in npc_obj.accessible_locations:
                    if random.random() < NPC_MOVE_CHANCE: 
                        old_location = npc_obj.current_location
                        npc_obj.current_location = scheduled_location
                        
                        # Check if this move is relevant to the player
                        if old_location == self.current_location_name and scheduled_location != self.current_location_name:
                            moved_npcs_info.append(f"{npc_obj.name} has left.")
                        elif scheduled_location == self.current_location_name and old_location != self.current_location_name:
                             moved_npcs_info.append(f"{npc_obj.name} has arrived.")
        
        if moved_npcs_info:
            self._print_color("\n(As time passes...)", Colors.MAGENTA)
            for info in moved_npcs_info:
                self._print_color(info, Colors.MAGENTA)
        
        self.update_npcs_in_current_location()


    def update_current_location_details(self, display_atmospherics=True): # Added flag
        if not self.current_location_name:
            self._print_color("Error: Current location not set.", Colors.RED)
            return

        location_data = LOCATIONS_DATA.get(self.current_location_name)
        if not location_data:
            self._print_color(f"Error: Unknown location: {self.current_location_name}", Colors.RED)
            return

        self._print_color(f"\n--- {self.current_location_name} ({self.get_current_time_period()}) ---", Colors.CYAN + Colors.BOLD)
        
        base_description = location_data["description"]
        time_effect_desc = location_data.get("time_effects", {}).get(self.get_current_time_period(), "")
        print(base_description + " " + time_effect_desc)

        if display_atmospherics:
            self.display_atmospheric_details() # Display atmospheric details after location desc

        self.update_npcs_in_current_location()


    def update_npcs_in_current_location(self):
        self.npcs_in_current_location = []
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
        for phrase_regex in CONCLUDING_PHRASES:
            if re.search(phrase_regex, text, re.IGNORECASE):
                return True
        return False

    def display_objectives(self):
        self._print_color("\n--- Your Objectives ---", Colors.CYAN + Colors.BOLD)
        if not self.player_character.objectives:
            print("You have no specific objectives at the moment.")
            return

        has_active = False
        for obj in self.player_character.objectives:
            if obj.get("active", False) and not obj["completed"]:
                if not has_active: self._print_color("Ongoing:", Colors.YELLOW)
                has_active = True
                self._print_color(f"- {obj['description']}", Colors.WHITE)
                current_stage = self.player_character.get_current_stage_for_objective(obj['id'])
                if current_stage:
                    self._print_color(f"  Current Stage: {current_stage['description']}", Colors.CYAN)
        if not has_active:
             print("You have no active objectives right now.")


        completed_objectives = [obj for obj in self.player_character.objectives if obj["completed"]]
        if completed_objectives:
            self._print_color("\nCompleted:", Colors.GREEN)
            for obj in completed_objectives:
                self._print_color(f"- {obj['description']}", Colors.WHITE)


    def display_help(self):
        self._print_color("\n--- Available Actions ---", Colors.CYAN + Colors.BOLD)
        actions = [
            ("look / l / examine / observe", "Examine surroundings, see people, items, and exits. May reveal atmospheric details."),
            ("look at [thing/person]", "Examine a specific item or person more closely."),
            ("talk to [name] / speak to [name]", "Speak with someone here."),
            ("move to [exit desc] / go to [location name]", "Change locations."),
            ("inventory / inv / i", "Check your possessions."),
            ("take [item name] / get [item name]", "Pick up an item from the location."),
            ("drop [item name]", "Leave an item from your inventory in the location."),
            ("use [item name]", "Attempt to use an item from your inventory."),
            ("use [item name] on [target name/item]", "Attempt to use an item on something or someone."),
            ("objectives / obj / purpose", "See your current goals and their stages."),
            ("think / reflect / contemplate", "Access your character's inner thoughts, possibly affecting state or revealing insights."),
            ("wait", "Pass some time."),
            ("save", "Save your current game progress."),
            ("load", "Load a previously saved game."),
            ("help / commands", "Show this help message."),
            ("quit / exit / q", "Exit the game.")
        ]
        for cmd, desc in actions:
            self._print_color(f"{cmd:<45} {Colors.WHITE}- {desc}{Colors.RESET}", Colors.MAGENTA)

    def parse_action(self, raw_input):
        action = raw_input.strip().lower()
        if not action: return None, None

        matched_command = None
        best_match_synonym = "" 
        parsed_arg = None

        # Check for commands with " on " structure first (e.g., "use item on target")
        if " on " in action:
            parts = action.split(" on ", 1)
            potential_cmd_part = parts[0].split(" ", 1)
            cmd_candidate = potential_cmd_part[0]
            item_name_candidate = potential_cmd_part[1] if len(potential_cmd_part) > 1 else None
            target_name = parts[1]

            for base_cmd, synonyms in COMMAND_SYNONYMS.items():
                if base_cmd == "use": # Only 'use' command uses 'on' structure for now
                    if cmd_candidate == base_cmd or cmd_candidate in synonyms:
                        if item_name_candidate:
                             # Return command, item name, and target name
                            return base_cmd, (item_name_candidate.strip(), target_name.strip())
                        else: # "use on target" - ambiguous, treat as error for now or prompt for item
                            return base_cmd, (None, target_name.strip()) # Or handle differently

        # Standard command parsing
        for base_cmd, synonyms in COMMAND_SYNONYMS.items():
            if action == base_cmd or action in synonyms: # Full match for command without args
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
            "last_significant_event_summary": self.last_significant_event_summary
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

            self.game_time = game_state_data["game_time"]
            self.current_day = game_state_data["current_day"]
            self.current_location_name = game_state_data["current_location_name"]
            self.dynamic_location_items = game_state_data.get("dynamic_location_items", {})
            self.event_manager.triggered_events = set(game_state_data.get("triggered_events", [])) 
            self.last_significant_event_summary = game_state_data.get("last_significant_event_summary")


            self.all_character_objects = {}
            saved_char_states = game_state_data["all_character_objects_state"]
            for char_name, char_state_data in saved_char_states.items():
                if char_name not in CHARACTERS_DATA:
                    self._print_color(f"Warning: Character '{char_name}' from save file not found in current CHARACTERS_DATA. Skipping.", Colors.YELLOW)
                    continue
                static_data = CHARACTERS_DATA[char_name] 
                self.all_character_objects[char_name] = Character.from_dict(char_state_data, static_data)

            player_name = game_state_data["player_character_name"]
            if player_name in self.all_character_objects:
                self.player_character = self.all_character_objects[player_name]
                self.player_character.is_player = True 
            else:
                self._print_color(f"Error: Saved player character '{player_name}' not found. Load failed.", Colors.RED)
                return False 

            if not self.dynamic_location_items:
                self.initialize_dynamic_location_items()
            
            self.update_npcs_in_current_location()

            self._print_color("Game loaded successfully.", Colors.GREEN)
            self.update_current_location_details() 
            return True

        except Exception as e:
            self._print_color(f"Error loading game: {e}", Colors.RED)
            return False

    def handle_use_item(self, item_name_input, target_name_input=None):
        """Handles the 'use' command logic."""
        item_to_use = None
        for inv_item in self.player_character.inventory:
            if inv_item["name"].lower().startswith(item_name_input.lower()):
                item_to_use = inv_item
                break
        
        if not item_to_use:
            self._print_color(f"You don't have '{item_name_input}' to use.", Colors.RED)
            return False # Action not successfully taken

        item_name = item_to_use["name"]
        item_props = DEFAULT_ITEMS.get(item_name, {})
        
        # --- Specific Item Use Logic ---
        # This will become a large part of the game's unique interactions
        used_successfully = False
        interaction_message = f"You contemplate using the {item_name}"
        if target_name_input:
            interaction_message += f" on {target_name_input}"
        interaction_message += "."

        # Example: Using Sonya's New Testament (perhaps on Raskolnikov or self)
        if item_name == "Sonya's New Testament":
            if target_name_input:
                target_npc = None
                if target_name_input.lower() == self.player_character.name.lower(): # Use on self
                     self._print_color(f"You open Sonya's New Testament, its worn pages offering a silent rebuke to your tormented thoughts.", Colors.GREEN)
                     # Potentially change player state, trigger reflection
                     self.player_character.apparent_state = "contemplative"
                     self.last_significant_event_summary = f"read from Sonya's New Testament, feeling its weight."
                     used_successfully = True
                else: # Use on NPC
                    for npc in self.npcs_in_current_location:
                        if npc.name.lower().startswith(target_name_input.lower()):
                            target_npc = npc
                            break
                    if target_npc:
                        self._print_color(f"You show Sonya's New Testament to {target_npc.name}.", Colors.WHITE)
                        # Gemini generates NPC reaction
                        reaction = self.gemini_api.get_item_interaction_description(
                            target_npc, item_name, item_props, f"reacts to player showing it"
                        )
                        self._print_color(f"{target_npc.name}: \"{reaction}\"", Colors.YELLOW)
                        self.last_significant_event_summary = f"showed {item_name} to {target_npc.name}."
                        used_successfully = True
                    else:
                        self._print_color(f"You don't see '{target_name_input}' here.", Colors.RED)
            else: # Use on self (default for some items)
                self._print_color(f"You hold Sonya's New Testament. Its presence is a heavy comfort, or a sharp reminder.", Colors.GREEN)
                self.last_significant_event_summary = f"contemplated Sonya's New Testament."
                used_successfully = True
        
        elif item_name == "Raskolnikov's axe":
            if self.player_character.name == "Rodion Raskolnikov":
                self._print_color(f"You grip the axe. Its cold weight is a familiar dread. What are you thinking?", Colors.RED)
                self.player_character.apparent_state = "dangerously agitated"
                self.last_significant_event_summary = f"held the axe, a dark impulse stirring."
                # No specific "use" here, but changes state. Actual use would be an attack or specific plot action.
                used_successfully = True # In the sense that an interaction occurred
            else: # Other characters can't really "use" it in the same way
                 self._print_color(f"You look at the axe. It's a grim object.", Colors.YELLOW)

        # Add more item use cases here...
        # elif item_name == "worn coin":
        #   if target_name_input and target is a beggar or vendor...

        else: # Generic "use" attempt
            self._print_color(interaction_message, Colors.YELLOW)
            self._print_color(f"Nothing specific seems to happen with the {item_name} right now.", Colors.YELLOW)
            # No time passes if nothing happens
            return False 

        if used_successfully:
            # Some items might be consumed upon use
            if item_props.get("consumable", False):
                self.player_character.remove_from_inventory(item_name, 1)
                self._print_color(f"The {item_name} is used up.", Colors.MAGENTA)
            return True # Action taken, time should pass
        return False


    def run(self):
        self.gemini_api.configure(self._print_color, self._input_color) 
        
        self._print_color("\n--- Crime and Punishment: A Text Adventure ---", Colors.CYAN + Colors.BOLD)
        self._print_color("Type 'load' to load a saved game, or press Enter to start a new game.", Colors.MAGENTA)
        initial_action = self._input_color("> ", Colors.WHITE).strip().lower()

        if initial_action == "load":
            if not self.load_game():
                self._print_color("Failed to load game. Starting a new game instead.", Colors.YELLOW)
                self.load_all_characters() 
                self.select_player_character()
        else:
            self.load_all_characters() 
            self.select_player_character()

        if not self.player_character or not self.current_location_name:
            self._print_color("Game initialization failed. Exiting.", Colors.RED)
            return
        
        self.update_current_location_details() # Initial look around

        self._print_color("\n--- Game Start ---", Colors.CYAN + Colors.BOLD)
        self._print_color(f"Day {self.current_day}, {self.get_current_time_period()}", Colors.MAGENTA)
        self.display_help() 


        while True:
            current_location_data = LOCATIONS_DATA.get(self.current_location_name)
            if not current_location_data:
                 self._print_color(f"Critical Error: Current location '{self.current_location_name}' data not found. Exiting.", Colors.RED)
                 break

            raw_action_input = self._input_color(f"\n[{Colors.CYAN}{self.current_location_name}{Colors.RESET} ({self.player_character.apparent_state})] What do you do? ", Colors.WHITE)
            command, argument = self.parse_action(raw_action_input)

            if command is None: continue

            action_taken_this_turn = True 
            time_to_advance = TIME_UNITS_PER_PLAYER_ACTION 
            display_atmospherics_after_action = True


            if command == "quit":
                self._print_color("Exiting game. Goodbye.", Colors.MAGENTA)
                break
            elif command == "save":
                self.save_game()
                action_taken_this_turn = False 
            elif command == "load":
                self.load_game() 
                action_taken_this_turn = False 
                display_atmospherics_after_action = False # Load already calls update_current_location_details
                continue 
            elif command == "help":
                self.display_help()
                action_taken_this_turn = False
            
            elif command == "look":
                # 'look' itself will call update_current_location_details which handles atmospherics
                self.update_current_location_details(display_atmospherics=True) 
                display_atmospherics_after_action = False # Already displayed
                
                current_loc_items = self.dynamic_location_items.get(self.current_location_name, [])
                if current_loc_items:
                    self._print_color("\nYou also see here:", Colors.YELLOW)
                    for item_info in current_loc_items:
                        item_name = item_info["name"]
                        item_qty = item_info.get("quantity", 1)
                        item_default_info = DEFAULT_ITEMS.get(item_name, {})
                        desc_snippet = item_default_info.get('description', 'an item')[:40] 
                        if item_qty > 1:
                            print(f"- {Colors.GREEN}{item_name}{Colors.RESET} (x{item_qty}) - {desc_snippet}...")
                        else:
                            print(f"- {Colors.GREEN}{item_name}{Colors.RESET} - {desc_snippet}...")
                else:
                    print("\nYou see no loose items of interest here.")

                if self.npcs_in_current_location:
                    self._print_color("\nPeople here:", Colors.YELLOW)
                    for npc in self.npcs_in_current_location:
                        print(f"- {Colors.YELLOW}{npc.name}{Colors.RESET} (Appears: {npc.apparent_state}, Relationship: {self.get_relationship_text(npc.relationship_with_player)})")
                else:
                    print("\nYou see no one else of note here.")
                
                self._print_color("\nExits:", Colors.BLUE)
                # ... (rest of exit display logic) ...
                has_accessible_exits = False
                if current_location_data["exits"]:
                    for exit_target_loc, exit_desc in current_location_data["exits"].items():
                        if exit_target_loc in self.player_character.accessible_locations:
                            print(f"- {Colors.BLUE}{exit_desc} (to {Colors.CYAN}{exit_target_loc}{Colors.BLUE}){Colors.RESET}")
                            has_accessible_exits = True
                if not has_accessible_exits:
                    print(f"{Colors.BLUE}There are no exits you can use from here.{Colors.RESET}")

                if argument: # look at [target]
                    target_to_look_at = argument.lower()
                    found_target = False
                    # Check items in room
                    for item_info in self.dynamic_location_items.get(self.current_location_name, []):
                        if item_info["name"].lower().startswith(target_to_look_at):
                            item_default = DEFAULT_ITEMS.get(item_info["name"])
                            if item_default:
                                self._print_color(f"You examine the {item_info['name']}:", Colors.GREEN)
                                # Use Gemini for a more evocative description
                                gen_desc = self.gemini_api.get_item_interaction_description(self.player_character, item_info['name'], item_default, "examine closely")
                                self._print_color(f"\"{gen_desc}\"", Colors.GREEN)
                                if not gen_desc or "OOC" in gen_desc : # Fallback if Gemini fails
                                     print(item_default.get('description', "It's just a common item."))
                                found_target = True
                                break
                    # Check items in inventory
                    if not found_target:
                        for inv_item_info in self.player_character.inventory:
                             if inv_item_info["name"].lower().startswith(target_to_look_at):
                                item_default = DEFAULT_ITEMS.get(inv_item_info["name"])
                                if item_default:
                                    self._print_color(f"You examine your {inv_item_info['name']}:", Colors.GREEN)
                                    gen_desc = self.gemini_api.get_item_interaction_description(self.player_character, inv_item_info['name'], item_default, "examine closely from inventory")
                                    self._print_color(f"\"{gen_desc}\"", Colors.GREEN)
                                    if not gen_desc or "OOC" in gen_desc : # Fallback
                                        print(item_default.get('description', "It's one of your belongings."))
                                    found_target = True
                                    break
                    # Check NPCs
                    if not found_target:
                        for npc in self.npcs_in_current_location:
                            if npc.name.lower().startswith(target_to_look_at):
                                self._print_color(f"You look closely at {Colors.YELLOW}{npc.name}{Colors.RESET} (appears {npc.apparent_state}):", Colors.WHITE)
                                # Gemini call for detailed observation of NPC
                                observation = self.gemini_api.get_player_reflection( # Re-using reflection for observation
                                    self.player_character, 
                                    f"observing {npc.name} in {self.current_location_name}", 
                                    f"You are trying to discern more about {npc.name}'s demeanor and thoughts. They appear to be '{npc.apparent_state}'.",
                                    self.get_current_time_period()
                                )
                                self._print_color(f"\"{observation}\"", Colors.GREEN)
                                found_target = True
                                break
                    if not found_target:
                        self._print_color(f"You don't see '{argument}' here to look at specifically.", Colors.RED)
                action_taken_this_turn = False 
            
            elif command == "inventory":
                self._print_color("\n--- Your Inventory ---", Colors.CYAN + Colors.BOLD)
                print(self.player_character.get_inventory_description())
                action_taken_this_turn = False

            elif command == "take":
                if not argument:
                    self._print_color("What do you want to take?", Colors.RED)
                    action_taken_this_turn = False
                else:
                    # ... (take logic remains largely the same, but can set last_significant_event_summary) ...
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
                            take_quantity = 1 # For now, take one at a time if stackable
                            
                            if item_found_in_loc.get("quantity", 1) > take_quantity:
                                item_found_in_loc["quantity"] -= take_quantity
                            else:
                                location_items.pop(item_idx_in_loc)
                            
                            self.player_character.add_to_inventory(item_found_in_loc["name"], take_quantity)
                            self._print_color(f"You take the {item_found_in_loc['name']}.", Colors.GREEN)
                            self.last_significant_event_summary = f"took the {item_found_in_loc['name']}."
                            # Potentially change player state if item is ominous
                            if item_default_props.get("is_notable"):
                                self.player_character.apparent_state = "thoughtful" # or "burdened"
                        else:
                            self._print_color(f"You can't take the {item_found_in_loc['name']}.", Colors.YELLOW)
                            action_taken_this_turn = False
                    else:
                        self._print_color(f"You don't see any '{item_to_take_name}' here to take.", Colors.RED)
                        action_taken_this_turn = False


            elif command == "drop":
                if not argument:
                    self._print_color("What do you want to drop?", Colors.RED)
                    action_taken_this_turn = False
                else:
                    # ... (drop logic, can set last_significant_event_summary) ...
                    item_to_drop_name = argument.lower()
                    item_in_inventory = None
                    for inv_item in self.player_character.inventory:
                        if inv_item["name"].lower().startswith(item_to_drop_name):
                            item_in_inventory = inv_item
                            break
                    
                    if item_in_inventory:
                        drop_quantity = 1 
                        removed_successfully = self.player_character.remove_from_inventory(item_in_inventory["name"], drop_quantity)
                        
                        if removed_successfully:
                            location_items = self.dynamic_location_items.setdefault(self.current_location_name, [])
                            # ... (add to location logic) ...
                            existing_loc_item = None
                            for loc_item in location_items:
                                if loc_item["name"] == item_in_inventory["name"]:
                                    existing_loc_item = loc_item
                                    break
                            if existing_loc_item:
                                existing_loc_item["quantity"] = existing_loc_item.get("quantity", 1) + drop_quantity
                            else:
                                location_items.append({"name": item_in_inventory["name"], "quantity": drop_quantity})

                            self._print_color(f"You drop the {item_in_inventory['name']}.", Colors.GREEN)
                            self.last_significant_event_summary = f"dropped the {item_in_inventory['name']}."
                        else:
                            self._print_color(f"You try to drop {item_in_inventory['name']}, but something is wrong.", Colors.RED)
                            action_taken_this_turn = False
                    else:
                        self._print_color(f"You don't have '{item_to_drop_name}' in your inventory to drop.", Colors.RED)
                        action_taken_this_turn = False
            
            elif command == "use":
                if isinstance(argument, tuple): # "use item on target"
                    item_name_input, target_name_input = argument
                    if item_name_input is None: # "use on target" was parsed
                        self._print_color(f"What do you want to use on {target_name_input}?", Colors.RED)
                        action_taken_this_turn = False
                    else:
                        action_taken_this_turn = self.handle_use_item(item_name_input, target_name_input)
                elif argument: # "use item"
                    action_taken_this_turn = self.handle_use_item(argument)
                else: # "use"
                    self._print_color("What do you want to use?", Colors.RED)
                    action_taken_this_turn = False


            elif command == "objectives":
                self.display_objectives()
                action_taken_this_turn = False 

            elif command == "think":
                self._print_color("You pause to reflect...", Colors.MAGENTA)
                active_objectives = [obj for obj in self.player_character.objectives if obj.get("active", False) and not obj["completed"]]
                obj_summary_list = []
                for obj in active_objectives:
                    desc = obj['description']
                    stage_info = self.player_character.get_current_stage_for_objective(obj['id'])
                    if stage_info:
                        desc += f" (Currently: {stage_info['description']})"
                    obj_summary_list.append(f"- {desc}")

                objectives_text = "\nYour current objectives:\n" + "\n".join(obj_summary_list) if obj_summary_list else "\nYou have no pressing objectives."
                inventory_summary = self.player_character.get_inventory_description()
                full_reflection_context = objectives_text + f"\n{inventory_summary}\nYour current apparent state is '{self.player_character.apparent_state}'."

                reflection = self.gemini_api.get_player_reflection(
                    self.player_character, 
                    self.current_location_name, 
                    full_reflection_context,
                    self.get_current_time_period()
                )
                self._print_color(f"Inner thought: \"{reflection}\"", Colors.GREEN)
                self.last_significant_event_summary = "was lost in thought."
                # Thinking might change apparent state
                if "paranoia" in reflection.lower() or "fear" in reflection.lower() or "fever" in reflection.lower():
                    self.player_character.apparent_state = random.choice(["agitated", "feverish", "suspiciously calm"])
                elif "hope" in reflection.lower() or "calm" in reflection.lower():
                     self.player_character.apparent_state = "calm" # or "normal" after some time
            
            elif command == "wait":
                self._print_color("You wait for a while, observing the flow of life around you.", Colors.MAGENTA)
                time_to_advance = TIME_UNITS_PER_PLAYER_ACTION * random.randint(2,4) # Wait a bit longer and more variably
                self.last_significant_event_summary = "waited, letting time pass."
                # Waiting might change apparent state if agitated
                if self.player_character.apparent_state in ["agitated", "feverish"]:
                    if random.random() < 0.3: # Chance to calm down a bit
                        self.player_character.apparent_state = "normal" if self.player_character.apparent_state == "agitated" else "less feverish" # new state
            
            elif command == "talk to":
                if not argument:
                    self._print_color("Who do you want to talk to?", Colors.RED)
                    action_taken_this_turn = False
                elif not self.npcs_in_current_location:
                    print("There's no one here to talk to.")
                    action_taken_this_turn = False
                else:
                    target_name_input = argument
                    target_npc = None
                    for npc_obj in self.npcs_in_current_location:
                        if npc_obj.name.lower().startswith(target_name_input.lower()): 
                            target_npc = npc_obj
                            break
                    
                    if target_npc:
                        self._print_color(f"\nYou approach {Colors.YELLOW}{target_npc.name}{Colors.RESET} (appears {target_npc.apparent_state}).", Colors.WHITE)
                        
                        history_key_player = self.player_character.name 
                        if not target_npc.conversation_histories.get(history_key_player): 
                             self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end="")
                             print(f"\"{target_npc.greeting}\"")
                             target_npc.add_to_history(self.player_character.name, target_npc.name, target_npc.greeting)
                             self.player_character.add_to_history(target_npc.name, target_npc.name, target_npc.greeting)

                        conversation_active = True
                        while conversation_active: 
                            player_dialogue = self._input_color(f"You ({Colors.GREEN}{self.player_character.name}{Colors.RESET}, {self.player_character.apparent_state}): ", Colors.GREEN).strip()
                            if player_dialogue.lower() in ["leave", "goodbye", "end chat", "back"]:
                                self._print_color(f"You end the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.", Colors.WHITE)
                                # ... (add leave to history) ...
                                target_npc.add_to_history(self.player_character.name, self.player_character.name, "(Leaves the conversation)")
                                self.player_character.add_to_history(target_npc.name, self.player_character.name, "(Leaves the conversation)")
                                self.last_significant_event_summary = f"ended a conversation with {target_npc.name}."
                                conversation_active = False
                                break 
                            if not player_dialogue:
                                print("You say nothing.")
                                # Don't advance time or call AI for empty input
                                continue 
                            
                            self._print_color("Thinking...", Colors.MAGENTA) 
                            # Get player's notable items summary
                            player_items_summary = self.player_character.get_notable_carried_items_summary()

                            ai_response = self.gemini_api.get_npc_dialogue(
                                target_npc, self.player_character, player_dialogue, 
                                self.current_location_name, 
                                self.get_relationship_text(target_npc.relationship_with_player),
                                target_npc.get_player_memory_summary(),
                                self.player_character.apparent_state, # Pass player's state
                                player_items_summary # Pass notable items
                            )
                            target_npc.update_relationship(player_dialogue, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS) 

                            self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end="")
                            print(f"\"{ai_response}\"")
                            self.last_significant_event_summary = f"spoke with {target_npc.name} who said: \"{ai_response[:50]}...\""


                            # Objective check/update based on dialogue could go here
                            # e.g., if ai_response or player_dialogue contains keywords related to an objective stage condition

                            if self.check_conversation_conclusion(ai_response) or self.check_conversation_conclusion(player_dialogue):
                                self._print_color(f"\nThe conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET} seems to have concluded.", Colors.MAGENTA)
                                # ... (add conclusion to history) ...
                                target_npc.add_to_history(self.player_character.name, "System", "(Conversation concludes naturally)")
                                self.player_character.add_to_history(target_npc.name, "System", "(Conversation concludes naturally)")
                                conversation_active = False
                                break 
                            
                            # Only advance time if conversation is still active and input was given
                            self.advance_time(TIME_UNITS_PER_PLAYER_ACTION) 
                            # Events can be triggered during conversation
                            event_triggered_in_convo = self.event_manager.check_and_trigger_events()
                            if event_triggered_in_convo:
                                self.last_significant_event_summary = "an event occurred during conversation."
                                # Potentially break conversation if event is disruptive
                                # For now, just note it and continue
                    else:
                        self._print_color(f"You don't see anyone named '{target_name_input}' here to talk to.", Colors.RED)
                        action_taken_this_turn = False
            
            elif command == "move to":
                if not argument:
                    self._print_color("Where do you want to move to?", Colors.RED)
                    action_taken_this_turn = False
                else:
                    target_exit_desc_input = argument.lower()
                    moved = False
                    potential_target_loc_name = None

                    if current_location_data["exits"]:
                        # Attempt 1: Exact match with target location name (canonical name)
                        for target_loc_key_exact in current_location_data["exits"].keys():
                            if target_loc_key_exact.lower() == target_exit_desc_input:
                                potential_target_loc_name = target_loc_key_exact
                                break
                        
                        # Attempt 2: Starts with match for target location name
                        if not potential_target_loc_name:
                            for target_loc_key_startswith in current_location_data["exits"].keys():
                                if target_loc_key_startswith.lower().startswith(target_exit_desc_input):
                                    potential_target_loc_name = target_loc_key_startswith
                                    break 

                        # Attempt 3: Starts with match for exit description text
                        if not potential_target_loc_name:
                            for target_loc_key_desc, desc_text in current_location_data["exits"].items():
                                if desc_text.lower().startswith(target_exit_desc_input):
                                    potential_target_loc_name = target_loc_key_desc
                                    break 
                    
                    if potential_target_loc_name:
                        if potential_target_loc_name in self.player_character.accessible_locations:
                            old_location = self.current_location_name
                            self.current_location_name = potential_target_loc_name
                            self.player_character.current_location = potential_target_loc_name 
                            self.last_significant_event_summary = f"moved from {old_location} to {self.current_location_name}."
                            self.update_current_location_details() 
                            display_atmospherics_after_action = False 
                            moved = True
                        else:
                            self._print_color(f"You consider going to {Colors.CYAN}{potential_target_loc_name}{Colors.RESET}, but it doesn't feel right or possible for you to go there now.", Colors.YELLOW)
                            action_taken_this_turn = False 
                    else: 
                        self._print_color(f"You can't find a way to '{target_exit_desc_input}' from here or it's not a known destination.", Colors.RED)
                        action_taken_this_turn = False
            

            else: 
                self._print_color(f"Unknown command: '{command}'. Type 'help' for a list of actions.", Colors.RED)
                action_taken_this_turn = False

            if action_taken_this_turn:
                self.advance_time(time_to_advance) 
                event_triggered = self.event_manager.check_and_trigger_events()
                if event_triggered: 
                    pass 
                
                if self.time_since_last_npc_interaction >= TIME_UNITS_FOR_NPC_INTERACTION_CHANCE:
                    if len(self.npcs_in_current_location) >= 2 and random.random() < NPC_INTERACTION_CHANCE:
                        npc_interaction_text = self.event_manager.attempt_npc_npc_interaction()
                        if npc_interaction_text:
                             self.last_significant_event_summary = "overheard an exchange between NPCs."
                    self.time_since_last_npc_interaction = 0 
            
            if display_atmospherics_after_action and action_taken_this_turn : 
                self.display_atmospheric_details()
            
            if self.player_character.name == "Rodion Raskolnikov":
                obj_grapple = self.player_character.get_objective_by_id("grapple_with_crime")
                if obj_grapple and obj_grapple["completed"]:
                    current_stage = self.player_character.get_current_stage_for_objective("grapple_with_crime")
                    if current_stage and current_stage.get("is_ending_stage"):
                        self._print_color(f"\n--- The story of {self.player_character.name} has reached a conclusion ({current_stage['description']}) ---", Colors.CYAN + Colors.BOLD)
                        break 


