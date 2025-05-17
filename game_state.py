# game_state.py
import json
import os
import re
import random # For NPC-NPC interaction chance

from game_config import (Colors, API_CONFIG_FILE, GEMINI_MODEL_NAME,
                         CONCLUDING_PHRASES, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS,
                         TIME_UNITS_PER_PLAYER_ACTION, MAX_TIME_UNITS_PER_DAY, TIME_PERIODS,
                         TIME_UNITS_FOR_NPC_INTERACTION_CHANCE, NPC_INTERACTION_CHANCE) # Added new imports
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
        
        self.gemini_api = GeminiAPI()
        self.event_manager = EventManager(self) 
        self.game_config = __import__('game_config') 

        self.game_time = 0 
        self.current_day = 1
        self.time_since_last_npc_interaction = 0 # Counter for NPC-NPC interaction

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

    def advance_time(self, units=TIME_UNITS_PER_PLAYER_ACTION): # Allow custom time advancement
        self.game_time += units
        if (self.game_time // MAX_TIME_UNITS_PER_DAY) + 1 > self.current_day:
            self.current_day = (self.game_time // MAX_TIME_UNITS_PER_DAY) + 1
            self._print_color(f"\nA new day dawns. It is Day {self.current_day}.", Colors.CYAN + Colors.BOLD)
        
        current_period = self.get_current_time_period()
        self._print_color(f"(Time: Day {self.current_day}, {current_period}, Unit: {self.game_time % MAX_TIME_UNITS_PER_DAY})", Colors.MAGENTA)
        self.time_since_last_npc_interaction += units


    def load_all_characters(self):
        for name, data in CHARACTERS_DATA.items():
            if data["default_location"] not in data["accessible_locations"]:
                self._print_color(f"Warning: Default location {data['default_location']} for {name} not in accessible_locations. Adding it.", Colors.YELLOW)
                data["accessible_locations"].append(data["default_location"])

            self.all_character_objects[name] = Character(
                name, data["persona"], data["greeting"], data["default_location"], 
                data["accessible_locations"], data.get("objectives", [])
            )

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
                    
                    self._print_color(f"\nYou are playing as {Colors.GREEN}{self.player_character.name}{Colors.RESET}.", Colors.WHITE)
                    self._print_color(f"You start in: {Colors.CYAN}{self.current_location_name}{Colors.RESET}", Colors.WHITE)
                    break
                else:
                    self._print_color("Invalid choice. Please enter a number from the list.", Colors.RED)
            except ValueError:
                self._print_color("Invalid input. Please enter a number.", Colors.RED)
    
    def update_current_location_details(self):
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
        print(base_description + time_effect_desc)


        self.npcs_in_current_location = []
        for char_name, char_obj in self.all_character_objects.items():
            if not char_obj.is_player and char_obj.current_location == self.current_location_name: 
                if char_obj not in self.npcs_in_current_location:
                    self.npcs_in_current_location.append(char_obj)
        
        if self.current_location_name == "Raskolnikov's Garret" and self.player_character.name != "Rodion Raskolnikov":
            rask_npc_obj = self.all_character_objects.get("Rodion Raskolnikov")
            if rask_npc_obj and rask_npc_obj.current_location == "Raskolnikov's Garret" and rask_npc_obj not in self.npcs_in_current_location:
                 self.npcs_in_current_location.append(rask_npc_obj)


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
        active_objectives = [obj for obj in self.player_character.objectives if obj.get("active", False) and not obj["completed"]]
        completed_objectives = [obj for obj in self.player_character.objectives if obj["completed"]]

        if not active_objectives and not completed_objectives:
            print("You have no specific objectives at the moment.")
            return
        
        if active_objectives:
            self._print_color("Ongoing:", Colors.YELLOW)
            for obj in active_objectives:
                self._print_color(f"- {obj['description']}", Colors.WHITE)
        
        if completed_objectives:
            self._print_color("\nCompleted:", Colors.GREEN)
            for obj in completed_objectives:
                self._print_color(f"- {obj['description']}", Colors.WHITE)


    def run(self):
        self.gemini_api.configure(self._print_color, self._input_color) 
        self.load_all_characters()
        self.select_player_character()

        if not self.player_character or not self.current_location_name:
            self._print_color("Game initialization failed. Exiting.", Colors.RED)
            return
        
        self.update_current_location_details() 

        self._print_color("\n--- Game Start ---", Colors.CYAN + Colors.BOLD)
        self._print_color(f"Day {self.current_day}, {self.get_current_time_period()}", Colors.MAGENTA)
        print(f"{Colors.MAGENTA}Type 'quit' to exit the game.{Colors.RESET}")
        print(f"{Colors.MAGENTA}Type 'look' to examine your surroundings, see who is here, and find exits.{Colors.RESET}")
        print(f"{Colors.MAGENTA}Type 'talk to [name]' to speak with someone.{Colors.RESET}")
        print(f"{Colors.MAGENTA}Type 'move to [exit description]' or 'go to [location name]' to change locations.{Colors.RESET}")
        print(f"{Colors.MAGENTA}Type 'objectives' to see your current goals.{Colors.RESET}")
        print(f"{Colors.MAGENTA}Type 'think' or 'reflect' for your character's inner thoughts.{Colors.RESET}")
        print(f"{Colors.MAGENTA}Type 'wait' to pass some time.{Colors.RESET}")
        print(f"{Colors.MAGENTA}Type 'visualize [character name]' to see an ASCII art portrait.{Colors.RESET}")


        while True:
            current_location_data = LOCATIONS_DATA.get(self.current_location_name)
            if not current_location_data:
                 self._print_color(f"Critical Error: Current location '{self.current_location_name}' data not found. Exiting.", Colors.RED)
                 break

            action = self._input_color(f"\n[{Colors.CYAN}{self.current_location_name}{Colors.RESET}] What do you do? ", Colors.WHITE).strip().lower()
            action_taken_this_turn = True 
            time_to_advance = TIME_UNITS_PER_PLAYER_ACTION # Default time advancement

            if action == "quit":
                self._print_color("Exiting game. Goodbye.", Colors.MAGENTA)
                break
            elif action == "look":
                self.update_current_location_details() 
                if self.npcs_in_current_location:
                    self._print_color("\nPeople here:", Colors.YELLOW)
                    for npc in self.npcs_in_current_location:
                        print(f"- {Colors.YELLOW}{npc.name}{Colors.RESET} (Relationship: {self.get_relationship_text(npc.relationship_with_player)})")
                else:
                    print("\nYou see no one else of note here.")
                
                self._print_color("\nExits:", Colors.BLUE)
                has_accessible_exits = False
                if current_location_data["exits"]:
                    for exit_target_loc, exit_desc in current_location_data["exits"].items():
                        if exit_target_loc in self.player_character.accessible_locations:
                            print(f"- {Colors.BLUE}{exit_desc} (to {Colors.CYAN}{exit_target_loc}{Colors.BLUE}){Colors.RESET}")
                            has_accessible_exits = True
                if not has_accessible_exits:
                    print(f"{Colors.BLUE}There are no exits you can use from here.{Colors.RESET}")
                action_taken_this_turn = False # Looking doesn't usually pass significant time
            
            elif action == "objectives":
                self.display_objectives()
                action_taken_this_turn = False 

            elif action == "think" or action == "reflect":
                self._print_color("You pause to reflect...", Colors.MAGENTA)
                objectives_text = "\nYour current objectives:\n" + "\n".join([f"- {obj['description']}" for obj in self.player_character.objectives if obj.get("active", False) and not obj["completed"]])
                reflection = self.gemini_api.get_player_reflection(self.player_character, self.current_location_name, objectives_text)
                self._print_color(f"Inner thought: \"{reflection}\"", Colors.GREEN)
            
            elif action == "wait":
                self._print_color("You wait for a while, observing the flow of life around you.", Colors.MAGENTA)
                time_to_advance = TIME_UNITS_PER_PLAYER_ACTION * 3 
            
            elif action.startswith("visualize "):
                char_name_to_visualize = action[len("visualize "):].strip()
                target_char_obj = None
                if char_name_to_visualize.lower() == self.player_character.name.lower():
                    target_char_obj = self.player_character
                else:
                    for npc in self.all_character_objects.values(): # Check all known characters
                        if npc.name.lower().startswith(char_name_to_visualize.lower()):
                            target_char_obj = npc
                            break
                
                if target_char_obj:
                    self._print_color(f"Attempting to visualize {Colors.YELLOW}{target_char_obj.name}{Colors.RESET}...", Colors.MAGENTA)
                    ascii_art = self.gemini_api.get_character_ascii_art(target_char_obj.name, target_char_obj.persona)
                    self._print_color("\n" + ascii_art, Colors.WHITE) # Display ASCII art
                else:
                    self._print_color(f"Cannot find character '{char_name_to_visualize}' to visualize.", Colors.RED)
                action_taken_this_turn = False # Visualizing doesn't pass time


            elif action.startswith("talk to "):
                if not self.npcs_in_current_location:
                    print("There's no one here to talk to.")
                    action_taken_this_turn = False
                    continue

                target_name_input = action[len("talk to "):].strip()
                target_npc = None
                for npc_obj in self.npcs_in_current_location:
                    if npc_obj.name.lower().startswith(target_name_input.lower()): 
                        target_npc = npc_obj
                        break
                
                if target_npc:
                    self._print_color(f"\nYou approach {Colors.YELLOW}{target_npc.name}{Colors.RESET}.", Colors.WHITE)
                    
                    current_npc_history = target_npc.conversation_histories.get(self.player_character.name, [])
                    if not current_npc_history or not current_npc_history[-1].startswith(f"{target_npc.name}: {target_npc.greeting}"):
                        self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end="")
                        print(f"\"{target_npc.greeting}\"")
                        target_npc.add_to_history(self.player_character.name, target_npc.name, target_npc.greeting)
                    
                    while True:
                        player_dialogue = self._input_color(f"You ({Colors.GREEN}{self.player_character.name}{Colors.RESET}): ", Colors.GREEN).strip()
                        if player_dialogue.lower() == "leave" or player_dialogue.lower() == "goodbye":
                            self._print_color(f"You end the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.", Colors.WHITE)
                            target_npc.add_to_history(self.player_character.name, self.player_character.name, "(Leaves the conversation)")
                            break
                        if player_dialogue.lower() == "back":
                            self._print_color(f"You step back from the conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET}.", Colors.WHITE)
                            break 
                        if not player_dialogue:
                            print("You say nothing.")
                            continue
                        
                        self._print_color("Thinking...", Colors.MAGENTA)
                        ai_response = self.gemini_api.get_npc_dialogue(
                            target_npc, self.player_character, player_dialogue, 
                            self.current_location_name, 
                            self.get_relationship_text(target_npc.relationship_with_player),
                            target_npc.get_player_memory_summary()
                        )
                        target_npc.update_relationship(player_dialogue, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS) 

                        self._print_color(f"{target_npc.name}: ", Colors.YELLOW, end="")
                        print(f"\"{ai_response}\"")

                        if self.check_conversation_conclusion(ai_response):
                            self._print_color(f"\nThe conversation with {Colors.YELLOW}{target_npc.name}{Colors.RESET} seems to have concluded.", Colors.MAGENTA)
                            target_npc.add_to_history(self.player_character.name, target_npc.name, "(Conversation concludes)")
                            break 
                else:
                    self._print_color(f"You don't see anyone named '{target_name_input}' here to talk to.", Colors.RED)
                    action_taken_this_turn = False
            
            elif action.startswith("move to ") or action.startswith("go to "):
                prefix_len = len("move to ") if action.startswith("move to ") else len("go to ")
                target_exit_desc_input = action[prefix_len:].strip().lower()
                
                moved = False
                potential_target_loc_name = None

                if current_location_data["exits"]:
                    for exit_target_loc_name_key, exit_desc_text_val in current_location_data["exits"].items():
                        if exit_target_loc_name_key.lower().startswith(target_exit_desc_input) or \
                           exit_desc_text_val.lower().startswith(target_exit_desc_input):
                            potential_target_loc_name = exit_target_loc_name_key
                            break 
                
                if potential_target_loc_name:
                    if potential_target_loc_name in self.player_character.accessible_locations:
                        self.current_location_name = potential_target_loc_name
                        self.player_character.current_location = potential_target_loc_name 
                        self.update_current_location_details() 
                        moved = True
                    else:
                        self._print_color(f"You consider going to {Colors.CYAN}{potential_target_loc_name}{Colors.RESET}, but it doesn't feel right for you to go there now.", Colors.YELLOW)
                        action_taken_this_turn = False 
                
                if not moved and not potential_target_loc_name: 
                    self._print_color(f"You can't find a way to '{target_exit_desc_input}' from here.", Colors.RED)
                    action_taken_this_turn = False
                elif not moved and potential_target_loc_name: 
                    action_taken_this_turn = False


            else:
                self._print_color("Invalid action. Try 'look', 'talk to [name]', 'move to [exit]', 'objectives', 'think', 'wait', 'visualize [name]', or 'quit'.", Colors.RED)
                action_taken_this_turn = False

            if action_taken_this_turn:
                self.advance_time(time_to_advance) # Use potentially modified time_to_advance
                self.event_manager.check_and_trigger_events()
                
                # Refined NPC-NPC interaction trigger
                if self.time_since_last_npc_interaction >= TIME_UNITS_FOR_NPC_INTERACTION_CHANCE:
                    if len(self.npcs_in_current_location) >= 2 and random.random() < NPC_INTERACTION_CHANCE:
                        self.event_manager.attempt_npc_npc_interaction()
                        self.time_since_last_npc_interaction = 0 # Reset counter after attempt
                    else:
                        # If not enough NPCs or chance failed, still reset or partially reset counter
                        # to ensure it doesn't keep trying every single turn immediately after.
                        # For now, just reset. Could also decrement or set to a fraction.
                        self.time_since_last_npc_interaction = 0 


