# event_manager.py
import random
from game_config import Colors

class EventManager:
    def __init__(self, game_ref):
        self.game = game_ref # Reference to the main Game object to access state
        self.triggered_events = set() # Keep track of events that have already happened

        self.story_events = [
            {
                "id": "marmeladov_tavern_encounter",
                "name": "Encounter with Marmeladov",
                "trigger": self.trigger_marmeladov_encounter,
                "action": self.action_marmeladov_encounter,
                "one_time": True
            },
            {
                "id": "raskolnikov_receives_letter",
                "name": "Letter from Mother",
                "trigger": self.trigger_letter_from_mother,
                "action": self.action_letter_from_mother,
                "one_time": True
            }
            # Add more events here
        ]

    def _print_event(self, text):
        self.game._print_color(f"\n{Colors.BOLD}{Colors.MAGENTA}--- Event ---{Colors.RESET}", Colors.MAGENTA)
        self.game._print_color(text, Colors.MAGENTA)
        self.game._print_color(f"{Colors.BOLD}{Colors.MAGENTA}-------------{Colors.RESET}\n", Colors.MAGENTA)


    # --- Event Triggers ---
    def trigger_marmeladov_encounter(self):
        # Assuming Marmeladov is not a full NPC yet, this is a scripted encounter.
        # Could be enhanced if Marmeladov becomes a full NPC.
        return (self.game.player_character.name == "Rodion Raskolnikov" and
                self.game.current_location_name == "Tavern" and
                self.game.game_time < 50 and # Early in the game
                "marmeladov_tavern_encounter" not in self.triggered_events)

    def trigger_letter_from_mother(self):
        return (self.game.player_character.name == "Rodion Raskolnikov" and
                self.game.current_location_name == "Raskolnikov's Garret" and # Or anywhere he might receive mail
                self.game.game_time > 10 and self.game.game_time < 60 and # After a bit of time
                "raskolnikov_receives_letter" not in self.triggered_events)

    # --- Event Actions ---
    def action_marmeladov_encounter(self):
        self._print_event(
            "As you sit nursing a cheap drink, a disheveled man with flushed cheeks and rambling speech stumbles towards your table. "
            "It is Semyon Zakharovich Marmeladov. He begins a lengthy, sorrowful monologue about his misfortunes, his daughter Sonya, "
            "and his own wretchedness. You listen, or perhaps only half-listen, to his tragic tale."
        )
        # This could potentially affect Raskolnikov's mood or objectives, or lead to meeting Sonya later.
        # For now, it's a narrative beat.
        self.game.player_character.add_player_memory("Listened to Marmeladov's tragic story in the tavern.")
        if self.game.player_character.get_objective_by_id("understand_theory"): # Slight nudge
             self.game.player_character.add_player_memory("Marmeladov's suffering gives pause to your theories.")


    def action_letter_from_mother(self):
        self._print_event(
            "A letter arrives for you, bearing the familiar handwriting of your mother, Pulcheria Alexandrovna. "
            "It is filled with news from home, expressions of her deep love and concern for you, and details about Dunya's "
            "unfortunate situation with Mr. Svidrigailov and her subsequent engagement to Mr. Luzhin. "
            "Your mother expresses her hopes that Luzhin might be able to help you in your career. "
            "The letter speaks of their imminent arrival in St. Petersburg."
        )
        self.game.player_character.add_player_memory("Received a troubling letter from mother about Dunya and Luzhin.")
        # This could activate or update objectives related to family.
        obj_help_family = self.game.player_character.get_objective_by_id("help_family")
        if obj_help_family and not obj_help_family["active"]:
            self.game.player_character.activate_objective("help_family")
        self.game._print_color("This news weighs heavily on your mind.", Colors.YELLOW)


    def check_and_trigger_events(self):
        for event in self.story_events:
            if event["id"] not in self.triggered_events and event["trigger"]():
                event["action"]()
                if event.get("one_time", True):
                    self.triggered_events.add(event["id"])
                return True # Trigger one event per turn for simplicity
        return False

    def attempt_npc_npc_interaction(self):
        if len(self.game.npcs_in_current_location) >= 2:
            # Only attempt if enough time has passed since last attempt or game start
            if self.game.game_time % self.game.game_config.TIME_UNITS_FOR_NPC_INTERACTION_CHANCE == 0:
                if random.random() < self.game.game_config.NPC_INTERACTION_CHANCE:
                    npc1, npc2 = random.sample(self.game.npcs_in_current_location, 2)
                    self.game._print_color(f"\n{Colors.MAGENTA}Nearby, you overhear a brief exchange...{Colors.RESET}", Colors.MAGENTA)
                    
                    interaction_text = self.game.gemini_api.get_npc_to_npc_interaction(
                        npc1, npc2, self.game.current_location_name, self.game.get_current_time_period()
                    )
                    if interaction_text:
                        # Simple display, assuming format "NPC1: text \n NPC2: text"
                        lines = interaction_text.split('\n')
                        for line in lines:
                            if ":" in line:
                                speaker, dialogue = line.split(":", 1)
                                self.game._print_color(f"{speaker.strip()}:", Colors.YELLOW, end="")
                                print(f" \"{dialogue.strip()}\"")
                            else:
                                print(f"{Colors.YELLOW}{line}{Colors.RESET}") # Fallback for other formats
                        # Add to their respective conversation histories (optional, could get noisy)
                        # npc1.add_to_history(npc2.name, npc1.name, "Overheard talking to " + npc2.name)
                        # npc2.add_to_history(npc1.name, npc2.name, "Overheard talking to " + npc1.name)
                    else:
                        self.game._print_color(f"{Colors.MAGENTA}...but it trails off into indistinct murmurs.{Colors.RESET}", Colors.MAGENTA)

