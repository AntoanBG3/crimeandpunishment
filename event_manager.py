# event_manager.py
import random
from game_config import Colors, DEFAULT_ITEMS # For adding generated items

class EventManager:
    def __init__(self, game_ref):
        self.game = game_ref
        self.triggered_events = set()
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
            },
            {
                "id": "katerina_ivanovna_public_lament",
                "name": "Katerina Ivanovna's Public Lament",
                "trigger": self.trigger_katerina_public_lament,
                "action": self.action_katerina_public_lament,
                "one_time": False # Can happen periodically
            },
            { # New event for finding an anonymous note
                "id": "find_anonymous_warning_note",
                "name": "Find an Anonymous Warning Note",
                "trigger": self.trigger_find_anonymous_note,
                "action": self.action_find_anonymous_note,
                "one_time": True # Or could be multiple different notes
            }
        ]

    def _print_event(self, text):
        self.game._print_color(f"\n{Colors.BOLD}{Colors.MAGENTA}--- Event ---{Colors.RESET}", Colors.MAGENTA)
        self.game._print_color(text, Colors.MAGENTA)
        self.game._print_color(f"{Colors.BOLD}{Colors.MAGENTA}-------------{Colors.RESET}\n", Colors.MAGENTA)

    # --- Event Triggers ---
    def trigger_marmeladov_encounter(self):
        return (self.game.player_character and self.game.player_character.name == "Rodion Raskolnikov" and
                self.game.current_location_name == "Tavern" and
                self.game.game_time > 20 and self.game.game_time < 70 and # Specific time window
                "marmeladov_tavern_encounter" not in self.triggered_events)

    def trigger_letter_from_mother(self):
        return (self.game.player_character and self.game.player_character.name == "Rodion Raskolnikov" and
                self.game.current_location_name == "Raskolnikov's Garret" and
                self.game.game_time > 10 and self.game.game_time < 60 and
                "raskolnikov_receives_letter" not in self.triggered_events)

    def trigger_katerina_public_lament(self):
        katerina = self.game.all_character_objects.get("Katerina Ivanovna Marmeladova")
        return (katerina and katerina.current_location == "Haymarket Square" and
                self.game.current_location_name == "Haymarket Square" and
                self.game.get_current_time_period() in ["Afternoon", "Evening"] and
                random.random() < 0.10 and # Reduced chance
                "katerina_ivanovna_public_lament_recent" not in self.triggered_events)
    
    def trigger_find_anonymous_note(self):
        # Trigger if Raskolnikov's notoriety is rising and he's in a less secure place
        return (self.game.player_character and self.game.player_character.name == "Rodion Raskolnikov" and
                self.game.player_notoriety_level >= 1.5 and
                self.game.current_location_name in ["Raskolnikov's Garret", "Stairwell (Outside Raskolnikov's Garret)"] and
                random.random() < 0.25 and # Not too common
                "find_anonymous_warning_note" not in self.triggered_events)


    # --- Event Actions ---
    def action_marmeladov_encounter(self):
        event_desc = ("As you sit nursing a cheap drink, a disheveled man with flushed cheeks and rambling speech stumbles towards your table. "
            "It is Semyon Zakharovich Marmeladov. He begins a lengthy, sorrowful monologue about his misfortunes, his daughter Sonya, "
            "and his own wretchedness. You listen, or perhaps only half-listen, to his tragic tale.")
        self._print_event(event_desc)
        if self.game.player_character:
            self.game.player_character.add_player_memory("Listened to Marmeladov's tragic story in the tavern.")
            if self.game.player_character.get_objective_by_id("understand_theory"):
                 self.game.player_character.add_player_memory("Marmeladov's suffering gives pause to your theories.")
        self.game.last_significant_event_summary = "encountered Marmeladov in the tavern."
        self.game.key_events_occurred.append("Encountered Marmeladov.")
        # This encounter might add to "known_facts_about_crime" if Marmeladov mentions Sonya's situation vaguely.
        if "Sonya" not in " ".join(self.game.known_facts_about_crime):
            self.game.known_facts_about_crime.append("Heard of Sonya Marmeladova's difficult circumstances.")


    def action_letter_from_mother(self):
        event_desc = ("A letter arrives for you, bearing the familiar handwriting of your mother, Pulcheria Alexandrovna. "
            "It is filled with news from home, expressions of her deep love and concern for you, and details about Dunya's "
            "unfortunate situation with Mr. Svidrigailov and her subsequent engagement to Mr. Luzhin. "
            "Your mother expresses her hopes that Luzhin might be able to help you in your career. "
            "The letter speaks of their imminent arrival in St. Petersburg.")
        self._print_event(event_desc)
        if self.game.player_character:
            self.game.player_character.add_player_memory("Received a troubling letter from mother about Dunya and Luzhin.")
            obj_help_family = self.game.player_character.get_objective_by_id("help_family")
            if obj_help_family and not obj_help_family.get("active", True):
                self.game.player_character.activate_objective("help_family")
            if not self.game.player_character.has_item("mother's letter"):
                self.game.player_character.add_to_inventory("mother's letter")
                self._print_color("The letter is now in your possession.", Colors.GREEN)
            self.game._print_color("This news weighs heavily on your mind.", Colors.YELLOW)
        self.game.last_significant_event_summary = "received a letter from his mother about Dunya."
        self.game.key_events_occurred.append("Received letter from mother regarding Dunya's situation.")

    def action_katerina_public_lament(self):
        event_desc = ("A commotion draws your attention. Katerina Ivanovna Marmeladova is in the square, flushed and feverish, "
            "her voice rising in a shrill lament. She clutches her children, decrying her fate, the injustice of her poverty, "
            "and the memory of her supposedly noble birth. A small, unsympathetic crowd gathers to watch the spectacle.")
        self._print_event(event_desc)
        katerina = self.game.all_character_objects.get("Katerina Ivanovna Marmeladova")
        if katerina: katerina.apparent_state = "highly agitated and feverish"
        if self.game.player_character:
            self.game.player_character.add_player_memory("Witnessed Katerina Ivanovna's distressing public scene in Haymarket.")
        self.game.last_significant_event_summary = "witnessed Katerina Ivanovna's public outburst."
        self.game.key_events_occurred.append("Katerina Ivanovna caused a public scene.")
        self.triggered_events.add("katerina_ivanovna_public_lament_recent")

    def action_find_anonymous_note(self):
        note_subject = "a warning about being watched or known"
        note_tone = "ominous, slightly uneducated, and hurried"
        note_key_info = "Hints that Raskolnikov's recent unusual behavior or presence near certain places has been noticed. Does not directly name the crime."
        
        note_text = self.game.gemini_api.get_generated_text_document(
            document_type="Anonymous Warning Note",
            author_persona_hint="someone observant from the shadows, perhaps a minor official or a street dweller",
            recipient_persona_hint="Rodion Raskolnikov",
            subject_matter=note_subject,
            desired_tone=note_tone,
            key_info_to_include=note_key_info,
            length_sentences=2
        )
        if note_text and not note_text.startswith("(OOC:"):
            event_desc = f"Tucked into your doorframe (or perhaps slipped under your door), you find a hastily folded piece of paper. It's an anonymous note."
            self._print_event(event_desc)
            
            # Create the "Anonymous Note" item instance with this specific content
            # Option 1: Add to location (player must then take it)
            note_item_instance = {"name": "Anonymous Note", "quantity": 1, "generated_content": note_text}
            # Ensure the base "Anonymous Note" is in DEFAULT_ITEMS with readable=True
            if "Anonymous Note" in DEFAULT_ITEMS:
                self.game.dynamic_location_items.setdefault(self.game.current_location_name, []).append(note_item_instance)
                self._print_color(f"An {Colors.GREEN}Anonymous Note{Colors.RESET} appears on the floor.", Colors.YELLOW)
                self.game.player_character.add_journal_entry("Note Found", f"Found an anonymous note: {note_text[:30]}...", self.game._get_current_game_time_period_str())

            else: # Fallback if item not defined well
                 self._print_color(f"You find a strange note: \"{note_text}\"", Colors.YELLOW)

            if self.game.player_character:
                self.game.player_character.add_player_memory("Found an ominous anonymous note.")
                self.game.player_character.apparent_state = "paranoid"
            self.game.last_significant_event_summary = "found an anonymous warning note."
            self.game.key_events_occurred.append("Found an anonymous warning note.")
            self.game.player_notoriety_level = min(self.game.player_notoriety_level + 0.5, 3) # Finding a note means someone *is* watching
        else:
            self._print_event("You thought you saw something, but it was just a trick of the light.")


    def check_and_trigger_events(self):
        if self.game.game_time % 100 == 5: # Cooldown reset periodically
            events_to_remove = {ev for ev in self.triggered_events if ev.endswith("_recent")}
            for ev_rem in events_to_remove: self.triggered_events.remove(ev_rem)

        for event in self.story_events:
            event_id = event["id"]
            is_one_time = event.get("one_time", True)
            if is_one_time and event_id in self.triggered_events: continue
            if not is_one_time and f"{event_id}_recent" in self.triggered_events: continue
            trigger_result = False
            try:
                if callable(event["trigger"]): trigger_result = event["trigger"]()
            except Exception as e:
                self.game._print_color(f"Error in event trigger for '{event.get('id', 'unknown event')}': {e}", Colors.RED)
            if trigger_result:
                try:
                    if callable(event["action"]): event["action"]()
                    if is_one_time: self.triggered_events.add(event_id)
                    # For repeatable, action should add "_recent" flag if needed
                    return True
                except Exception as e:
                     self.game._print_color(f"Error in event action for '{event.get('id', 'unknown event')}': {e}", Colors.RED)
                     if is_one_time: self.triggered_events.add(event_id);
                     return False
        return False

    def attempt_npc_npc_interaction(self):
        # ... (as before)
        if len(self.game.npcs_in_current_location) >= 2:
            try: npc1, npc2 = random.sample(self.game.npcs_in_current_location, 2)
            except ValueError: return False

            self.game._print_color(f"\n{Colors.MAGENTA}Nearby, you overhear a brief exchange...{Colors.RESET}", Colors.MAGENTA)
            interaction_text = self.game.gemini_api.get_npc_to_npc_interaction(npc1, npc2, self.game.current_location_name, self.game.get_current_time_period())
            if interaction_text and not interaction_text.startswith("(OOC:"):
                lines = interaction_text.split('\n')
                for line in lines:
                    if ":" in line:
                        speaker, dialogue = line.split(":", 1)
                        self.game._print_color(f"{speaker.strip()}:", Colors.YELLOW, end=""); print(f" \"{dialogue.strip()}\"")
                    else: self.game._print_color(f"{Colors.DIM}{line}{Colors.RESET}", Colors.DIM)
                return True
            else:
                # self.game._print_color(f"{Colors.MAGENTA}...but it trails off into indistinct murmurs.{Colors.RESET}", Colors.MAGENTA)
                pass # AI might sometimes return OOC or empty, don't always print murmurs for that
                return False
        return False