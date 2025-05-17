# character_module.py
import random 

# CHARACTERS_DATA includes persona, greeting, locations, objectives, and now a basic schedule.
# Objectives are now more structured to allow for stages and branching.
# Each objective can have: id, description, completed (bool), active (bool),
# stages (list of dicts: {stage_id, description, is_current_stage, conditions_to_advance, consequences}),
# current_stage_id (str)
CHARACTERS_DATA = {
    "Rodion Raskolnikov": {
        "persona": "You are Rodion Raskolnikov from Dostoevsky's 'Crime and Punishment'. You are impoverished, proud, and highly intelligent. You are tormented by your philosophical theory about 'extraordinary' men and your recent actions. You are often aloof, suspicious, and prone to bouts of feverish intensity. Your speech should reflect your intellectualism, internal conflict, and occasional abruptness.",
        "greeting": "Hmph. What do you want?",
        "default_location": "Raskolnikov's Garret",
        "accessible_locations": [
            "Raskolnikov's Garret", "Stairwell (Outside Raskolnikov's Garret)", "Haymarket Square", "Tavern",
            "Sonya's Room", "Police Station (General Area)", "Porfiry's Office",
            "Pawnbroker's Apartment Building", "Pawnbroker's Apartment", "Voznesensky Bridge", "Pulcheria's Lodgings"
        ],
        "objectives": [
            {
                "id": "grapple_with_crime", 
                "description": "Come to terms with the murder of Alyona Ivanovna and Lizaveta.", 
                "completed": False, "active": True, "current_stage_id": "initial_turmoil",
                "stages": [
                    {"stage_id": "initial_turmoil", "description": "Reel from the act, battling fever and paranoia. Avoid immediate suspicion.", "is_current_stage": True,
                     "success_criteria": "Survive initial days without capture, manage fever.",
                     "next_stages": {"confession_path": "seek_sonya", "justification_path": "engage_porfiry_intellectually", "despair_path": "isolate_further"}},
                    {"stage_id": "seek_sonya", "description": "Drawn to Sonya's suffering and purity, consider confession as a path to redemption.", "is_current_stage": False},
                    {"stage_id": "engage_porfiry_intellectually", "description": "Test your theories and will against Porfiry Petrovich, attempting to outwit him.", "is_current_stage": False},
                    {"stage_id": "isolate_further", "description": "Succumb to nihilistic despair, pushing everyone away.", "is_current_stage": False},
                    {"stage_id": "confessed_to_sonya", "description": "Having confessed to Sonya, grapple with her reaction and the path she proposes.", "is_current_stage": False},
                    {"stage_id": "public_confession", "description": "Confess publicly at the Haymarket or police station.", "is_current_stage": False, "is_ending_stage": True},
                    {"stage_id": "siberia", "description": "Face the consequences in Siberia, seeking spiritual rebirth.", "is_current_stage": False, "is_ending_stage": True},
                    {"stage_id": "unrepentant_end", "description": "Remain unrepentant, your theory leading to a bleak end (capture or suicide).", "is_current_stage": False, "is_ending_stage": True},
                ]
            },
            {
                "id": "understand_theory", 
                "description": "Grapple with the validity and consequences of your 'extraordinary man' theory.", 
                "completed": False, "active": True, "current_stage_id": "initial_validation",
                "stages": [
                     {"stage_id": "initial_validation", "description": "Internally justify your actions based on your theory.", "is_current_stage": True},
                     {"stage_id": "challenged_by_reality", "description": "Confront the human cost and psychological toll, questioning the theory's basis.", "is_current_stage": False},
                     {"stage_id": "theory_shattered", "description": "Recognize the flaws and inhumanity of the theory.", "is_current_stage": False, "linked_to_objective_completion": "grapple_with_crime"},
                     {"stage_id": "theory_reinforced_darkly", "description": "Twist the theory further to rationalize ongoing defiance or despair.", "is_current_stage": False},
                ]
            },
            {
                "id": "help_family", 
                "description": "Alleviate your mother and sister's financial burdens and protect Dunya from Luzhin and Svidrigailov.", 
                "completed": False, "active": True, "current_stage_id": "learn_of_arrival",
                 "stages": [
                    {"stage_id": "learn_of_arrival", "description": "React to the news of your mother and sister's arrival and Dunya's engagement.", "is_current_stage": True},
                    {"stage_id": "confront_luzhin", "description": "Confront Pyotr Petrovich Luzhin over his intentions towards Dunya.", "is_current_stage": False},
                    {"stage_id": "warn_dunya_svidrigailov", "description": "Warn Dunya about the true nature of Arkady Svidrigailov.", "is_current_stage": False},
                    {"stage_id": "family_secure", "description": "Ensure Dunya is safe and your mother is somewhat at peace.", "is_current_stage": False, "is_ending_stage": True}, # Can be a positive outcome for this thread
                 ]
            }
        ],
        "inventory_items": [{"name": "mother's letter", "quantity": 1}], 
        "schedule": { 
            "Morning": "Raskolnikov's Garret",
            "Afternoon": "Haymarket Square",
            "Evening": "Raskolnikov's Garret",
            "Night": "Raskolnikov's Garret"
        }
    },
    "Sonya Marmeladova": {
        "persona": "You are Sonya Marmeladova from Dostoevsky's 'Crime and Punishment'. You are deeply religious, compassionate, and self-sacrificing, despite your difficult circumstances. You are shy but possess a profound inner strength and unwavering faith. Your speech is often gentle, earnest, and may include references to God or scripture.",
        "greeting": "Oh... hello. May God be with you.",
        "default_location": "Sonya's Room",
        "accessible_locations": [
            "Sonya's Room", "Haymarket Square", "Raskolnikov's Garret", "Pulcheria's Lodgings",
            "Police Station (General Area)", "Tavern"
        ],
        "objectives": [
            {"id": "support_family", "description": "Continue to support the Marmeladov children and Katerina Ivanovna.", "completed": False, "active": True},
            {
                "id": "guide_raskolnikov", 
                "description": "Offer spiritual guidance and hope to Rodion Raskolnikov, urging him towards confession.", 
                "completed": False, "active": True, "current_stage_id": "initial_encounter",
                "stages": [
                    {"stage_id": "initial_encounter", "description": "Recognize a shared suffering in Raskolnikov.", "is_current_stage": True},
                    {"stage_id": "lazarus_reading", "description": "Read the story of Lazarus to Raskolnikov, offering a path to spiritual rebirth.", "is_current_stage": False},
                    {"stage_id": "receive_confession", "description": "Hear Raskolnikov's confession and urge him to accept his suffering.", "is_current_stage": False},
                    {"stage_id": "follow_to_siberia", "description": "Decide to follow Raskolnikov to Siberia.", "is_current_stage": False, "is_ending_stage": True},
                ]
            }
        ],
        "inventory_items": [{"name": "Sonya's New Testament", "quantity": 1}],
        "schedule": {
            "Morning": "Sonya's Room",
            "Afternoon": "Haymarket Square", 
            "Evening": "Sonya's Room",
            "Night": "Sonya's Room"
        }
    },
    "Porfiry Petrovich": {
        "persona": "You are Porfiry Petrovich from Dostoevsky's 'Crime and Punishment'. You are an examining magistrate, intelligent, cunning, and psychologically astute. You enjoy engaging in intellectual cat-and-mouse games, often speaking in a roundabout, seemingly amiable, yet probing way. Your speech can be deceptively casual, peppered with subtle questions and observations designed to unnerve and expose.",
        "greeting": "Well, well, look who it is. Come in, come in. Care for a little chat... or perhaps you have something on your mind?",
        "default_location": "Porfiry's Office",
        "accessible_locations": [
            "Porfiry's Office", "Police Station (General Area)", "Haymarket Square", "Raskolnikov's Garret"
        ],
        "objectives": [
            {
                "id": "solve_murders", 
                "description": "Uncover the truth behind the murders of Alyona Ivanovna and Lizaveta, focusing on Raskolnikov.", 
                "completed": False, "active": True, "current_stage_id": "initial_suspicion",
                "stages": [
                    {"stage_id": "initial_suspicion", "description": "Observe Raskolnikov and gather preliminary impressions.", "is_current_stage": True},
                    {"stage_id": "psychological_probes", "description": "Engage Raskolnikov in conversations designed to test his guilt and theories.", "is_current_stage": False},
                    {"stage_id": "closing_the_net", "description": "Subtly reveal the strength of the evidence or understanding of Raskolnikov's mind.", "is_current_stage": False},
                    {"stage_id": "encourage_confession", "description": "Offer Raskolnikov a chance to confess for a potentially lighter sentence.", "is_current_stage": False},
                    {"stage_id": "case_solved", "description": "Raskolnikov confesses or is irrefutably proven guilty.", "is_current_stage": False, "is_ending_stage": True}
                ]
            },
            {"id": "understand_criminal_mind", "description": "Explore the psychology of the criminal, particularly Raskolnikov's 'extraordinary man' theory.", "completed": False, "active": True}
        ],
        "inventory_items": [],
        "schedule": { 
            "Morning": "Porfiry's Office",
            "Afternoon": "Porfiry's Office",
            "Evening": "Police Station (General Area)", 
            "Night": "Porfiry's Office" 
        }
    },
    # Other characters (Dunya, Svidrigailov, Razumikhin, Pulcheria) would also have updated objectives
    # For brevity, I'm focusing on the main ones for now.
    "Dunya Raskolnikova": {
        "persona": "You are Dunya Raskolnikova, Rodion's sister, from Dostoevsky's 'Crime and Punishment'. You are intelligent, strong-willed, virtuous, and deeply concerned for your brother. You are protective and prepared to make sacrifices, but not at the cost of your dignity. Your speech is articulate, composed, and reflects your strong moral compass.",
        "greeting": "Greetings. I hope you are well. Rodya has been so... unlike himself.",
        "default_location": "Pulcheria's Lodgings",
        "accessible_locations": [
            "Pulcheria's Lodgings", "Haymarket Square", "Raskolnikov's Garret", "Sonya's Room", "Tavern"
        ],
        "objectives": [
            {"id": "protect_rodion", "description": "Understand what is troubling Rodion and protect him from harm or folly.", "completed": False, "active": True},
            {"id": "resolve_luzhin", "description": "Deal with the unwelcome attentions and proposal of Pyotr Petrovich Luzhin.", "completed": False, "active": True},
            {"id": "assess_svidrigailov", "description": "Determine the true intentions of Arkady Svidrigailov and protect herself.", "completed": False, "active": True}
        ],
        "inventory_items": [],
        "schedule": {
            "Morning": "Pulcheria's Lodgings",
            "Afternoon": "Haymarket Square", 
            "Evening": "Pulcheria's Lodgings",
            "Night": "Pulcheria's Lodgings"
        }
    },
    "Arkady Svidrigailov": {
        "persona": "You are Arkady Svidrigailov from Dostoevsky's 'Crime and Punishment'. You are a sensualist, amoral, and enigmatic figure, haunted by his past and capable of both depravity and surprising acts of charity. You are often cynical, worldly, and your speech can be laced with double entendres or unsettling observations about the darker sides of human nature.",
        "greeting": "Ah, a new face. Or an old one? St. Petersburg is so full of... possibilities. And ghosts. Don't you find?",
        "default_location": "Tavern",
        "accessible_locations": [
            "Tavern", "Haymarket Square", "Sonya's Room", "Pulcheria's Lodgings", "Voznesensky Bridge",
            "Raskolnikov's Garret"
        ],
        "objectives": [
            {"id": "pursue_dunya", "description": "Attempt to win over Dunya Raskolnikova, employing various means.", "completed": False, "active": True},
            {"id": "escape_ennui", "description": "Find some amusement or meaning to escape your profound boredom and past ghosts, perhaps through Raskolnikov or Dunya.", "completed": False, "active": True},
            {"id": "final_reckoning", "description": "Confront the emptiness of his existence.", "completed": False, "active": False} # Can be triggered
        ],
        "inventory_items": [{"name": "worn coin", "quantity": 20}], 
        "schedule": {
            "Morning": "Tavern", 
            "Afternoon": "Haymarket Square",
            "Evening": "Tavern",
            "Night": "Voznesensky Bridge" 
        }
    },
    "Dmitri Razumikhin": {
        "persona": "You are Dmitri Razumikhin from Dostoevsky's 'Crime and Punishment'. You are Raskolnikov's loyal friend, energetic, talkative, somewhat poor but resourceful and generally good-natured. You are practical and often try to help Raskolnikov, though sometimes bewildered by his behavior. Your speech is enthusiastic, direct, and sometimes a bit boisterous.",
        "greeting": "Hello there! Good to see you! Rodya's been acting stranger than a three-legged dog, has he mentioned anything to you?",
        "default_location": "Tavern", 
        "accessible_locations": [
            "Tavern", "Haymarket Square", "Raskolnikov's Garret", "Stairwell (Outside Raskolnikov's Garret)",
            "Pulcheria's Lodgings", "Police Station (General Area)", "Sonya's Room"
        ],
        "objectives": [
            {"id": "help_raskolnikov", "description": "Figure out what's wrong with Raskolnikov and help him get back on his feet.", "completed": False, "active": True},
            {"id": "support_dunya_pulcheria", "description": "Offer assistance and protection to Dunya and Pulcheria Alexandrovna.", "completed": False, "active": True}
        ],
        "inventory_items": [{"name": "worn coin", "quantity": 5}],
        "schedule": {
            "Morning": "Raskolnikov's Garret", 
            "Afternoon": "Tavern",
            "Evening": "Pulcheria's Lodgings", 
            "Night": "Tavern"
        }
    },
    "Pulcheria Alexandrovna Raskolnikova": {
        "persona": "You are Pulcheria Alexandrovna Raskolnikova, Rodion's mother. You are loving, anxious, and deeply devoted to your children, often to the point of idealizing them. You've traveled to St. Petersburg with Dunya out of concern for Rodion. Your speech is warm, motherly, but often reveals your underlying worries and fragile health.",
        "greeting": "Rodya, my dear boy! Or... oh, excuse me. Hello. Have you seen my Rodya? I worry so.",
        "default_location": "Pulcheria's Lodgings",
        "accessible_locations": [
            "Pulcheria's Lodgings", "Raskolnikov's Garret", "Haymarket Square", "Sonya's Room"
        ],
        "objectives": [
            {"id": "ensure_rodyas_wellbeing", "description": "Understand why Rodya is so troubled and ensure he is safe and well.", "completed": False, "active": True},
            {"id": "see_dunya_settled", "description": "Hope for Dunya to find a secure and happy future.", "completed": False, "active": True}
        ],
        "inventory_items": [],
        "schedule": { 
            "Morning": "Pulcheria's Lodgings",
            "Afternoon": "Raskolnikov's Garret", 
            "Evening": "Pulcheria's Lodgings",
            "Night": "Pulcheria's Lodgings"
        }
    }
}


class Character:
    def __init__(self, name, persona, greeting, default_location, accessible_locations, 
                 objectives=None, inventory_items=None, schedule=None, is_player=False):
        self.name = name
        self.persona = persona
        self.greeting = greeting
        self.default_location = default_location
        self.current_location = default_location 
        self.accessible_locations = accessible_locations
        self.is_player = is_player
        self.conversation_histories = {} 
        self.memory_about_player = [] 
        self.relationship_with_player = 0 
        # Deepcopy objectives to prevent shared state issues if loaded from CHARACTERS_DATA multiple times
        self.objectives = [obj.copy() for obj in objectives] if objectives else []
        for obj in self.objectives: # Ensure stages are also copied deeply if they exist
            if "stages" in obj:
                obj["stages"] = [stage.copy() for stage in obj["stages"]]

        self.inventory = [item.copy() for item in inventory_items] if inventory_items else []
        self.schedule = schedule if schedule else {} 
        self.apparent_state = "normal" # e.g., "normal", "agitated", "feverish" - can be updated by events/actions

    def to_dict(self):
        return {
            "name": self.name,
            "current_location": self.current_location,
            "is_player": self.is_player,
            "conversation_histories": self.conversation_histories,
            "memory_about_player": self.memory_about_player,
            "relationship_with_player": self.relationship_with_player,
            "objectives": self.objectives, # Assumes objectives are serializable (dicts, lists, basic types)
            "inventory": self.inventory,
            "apparent_state": self.apparent_state,
            # Persona, greeting, default_location, accessible_locations, schedule are static from CHARACTERS_DATA
        }

    @classmethod
    def from_dict(cls, data, static_char_data):
        # Use static_char_data for persona, greeting, etc., but objectives/inventory from saved data
        char = cls(
            name=data["name"],
            persona=static_char_data["persona"],
            greeting=static_char_data["greeting"],
            default_location=static_char_data["default_location"],
            accessible_locations=static_char_data["accessible_locations"],
            # Load objectives from saved data, falling back to static if not present in save (e.g. new objective added to game)
            objectives=data.get("objectives", [obj.copy() for obj in static_char_data.get("objectives", [])]),
            inventory_items=data.get("inventory", [item.copy() for item in static_char_data.get("inventory_items", [])]),
            schedule=static_char_data.get("schedule", {}),
            is_player=data["is_player"]
        )
        char.current_location = data["current_location"]
        char.conversation_histories = data.get("conversation_histories", {})
        char.memory_about_player = data.get("memory_about_player", [])
        char.relationship_with_player = data.get("relationship_with_player", 0)
        char.apparent_state = data.get("apparent_state", "normal")
        
        # Ensure objectives and their stages are well-formed after loading
        loaded_objectives = data.get("objectives", [])
        static_objectives_map = {obj['id']: obj for obj in static_char_data.get("objectives", [])}
        
        final_objectives = []
        for l_obj in loaded_objectives:
            s_obj = static_objectives_map.get(l_obj['id'])
            if s_obj:
                # Merge: take completion status from loaded, structure/text from static (in case of updates)
                merged_obj = s_obj.copy() # Start with static structure
                merged_obj.update({ # Overlay saved dynamic data
                    "completed": l_obj.get("completed", s_obj.get("completed", False)),
                    "active": l_obj.get("active", s_obj.get("active", True)),
                    "current_stage_id": l_obj.get("current_stage_id", s_obj.get("current_stage_id"))
                })
                if "stages" in merged_obj and "stages" in l_obj: # Merge stages if they exist
                     # This part can get complex; for now, assume loaded stages are what we want if they exist for that objective
                    merged_obj["stages"] = [stage.copy() for stage in l_obj["stages"]]
                final_objectives.append(merged_obj)
            else: # Objective from save not in static data (e.g. old objective removed from game)
                final_objectives.append(l_obj.copy()) # Keep it as is
        char.objectives = final_objectives
        return char

    def add_to_inventory(self, item_name, quantity=1):
        from game_config import DEFAULT_ITEMS 
        if item_name not in DEFAULT_ITEMS:
            print(f"Debug: Attempted to add unknown item '{item_name}'") 
            return False

        for item in self.inventory:
            if item["name"] == item_name:
                item["quantity"] = item.get("quantity", 1) + quantity
                return True
        new_item_entry = {"name": item_name}
        # Only add quantity key if item is meant to be stackable (has value or explicit quantity > 1)
        # Or if the base item definition implies stackability (e.g. "value" or default quantity)
        if DEFAULT_ITEMS[item_name].get("value") is not None or quantity > 1 or DEFAULT_ITEMS[item_name].get("quantity", 1) > 1:
             new_item_entry["quantity"] = quantity
        self.inventory.append(new_item_entry)
        return True

    def remove_from_inventory(self, item_name, quantity=1):
        for i, item in enumerate(self.inventory):
            if item["name"] == item_name:
                current_quantity = item.get("quantity", 1)
                if current_quantity > quantity:
                    item["quantity"] -= quantity
                    return True
                elif current_quantity == quantity:
                    self.inventory.pop(i)
                    return True
                else: 
                    return False 
        return False 

    def has_item(self, item_name, quantity=1):
        for item in self.inventory:
            if item["name"] == item_name:
                return item.get("quantity", 1) >= quantity
        return False
    
    def get_notable_carried_items_summary(self):
        """Returns a brief summary of notable items the character is carrying."""
        from game_config import DEFAULT_ITEMS
        notable_items = []
        for item_data in self.inventory:
            item_name = item_data["name"]
            item_props = DEFAULT_ITEMS.get(item_name, {})
            if item_props.get("is_notable", False):
                notable_items.append(item_name)
            # Example for stackable items like coins becoming notable if many
            elif item_name == "worn coin" and item_data.get("quantity", 0) >= item_props.get("notable_threshold", 1000):
                 notable_items.append(f"a significant sum of money ({item_data.get('quantity',0)} coins)")


        if not notable_items:
            return "is not carrying anything particularly noteworthy."
        if len(notable_items) == 1:
            return f"is carrying {notable_items[0]}."
        else:
            return f"is carrying {', '.join(notable_items[:-1])} and {notable_items[-1]}."


    def get_inventory_description(self):
        if not self.inventory:
            return "You are carrying nothing."
        
        descriptions = []
        for item_data in self.inventory:
            item_name = item_data["name"]
            quantity = item_data.get("quantity", 1)
            if quantity > 1: # Only show quantity if it's more than 1 and item is stackable
                descriptions.append(f"{item_name} (x{quantity})")
            else:
                descriptions.append(item_name)
        return "You are carrying: " + ", ".join(descriptions) + "."


    def add_to_history(self, other_char_name, speaker_name, text):
        if other_char_name not in self.conversation_histories:
            self.conversation_histories[other_char_name] = []
        # Limit history length per conversation pair
        if len(self.conversation_histories[other_char_name]) > 10:
            self.conversation_histories[other_char_name].pop(0)
        self.conversation_histories[other_char_name].append(f"{speaker_name}: {text}")

    def get_formatted_history(self, other_char_name, limit=6):
        history = self.conversation_histories.get(other_char_name, [])
        return "\n".join(history[-limit:])
    
    def add_player_memory(self, memory_fact):
        if memory_fact not in self.memory_about_player:
            self.memory_about_player.append(memory_fact)
            if len(self.memory_about_player) > 15: # Increased memory size
                self.memory_about_player.pop(0)

    def get_player_memory_summary(self):
        if not self.memory_about_player:
            return "You don't recall any specific details about them yet."
        return "Key things you recall about them: " + "; ".join(self.memory_about_player)

    def update_relationship(self, player_dialogue, positive_keywords, negative_keywords):
        change = 0
        player_dialogue_lower = player_dialogue.lower()
        for keyword in positive_keywords:
            if keyword in player_dialogue_lower:
                change += 1
        for keyword in negative_keywords:
            if keyword in player_dialogue_lower:
                change -= 1
        
        self.relationship_with_player += change
        self.relationship_with_player = max(-10, min(10, self.relationship_with_player))

        if change > 0:
            self.add_player_memory(f"They said something positive ('{player_dialogue[:30]}...').")
        elif change < 0:
            self.add_player_memory(f"They said something negative ('{player_dialogue[:30]}...').")

    def get_objective_by_id(self, objective_id):
        for obj in self.objectives:
            if obj["id"] == objective_id:
                return obj
        return None
    
    def get_current_stage_for_objective(self, objective_id):
        obj = self.get_objective_by_id(objective_id)
        if obj and "current_stage_id" in obj and "stages" in obj:
            for stage in obj["stages"]:
                if stage["stage_id"] == obj["current_stage_id"]:
                    return stage
        return None

    def advance_objective_stage(self, objective_id, next_stage_id):
        obj = self.get_objective_by_id(objective_id)
        if obj and "stages" in obj:
            current_stage_found = False
            next_stage_exists = any(s["stage_id"] == next_stage_id for s in obj["stages"])

            if not next_stage_exists:
                print(f"Debug: Next stage '{next_stage_id}' not found for objective '{objective_id}'.")
                return False

            for stage in obj["stages"]:
                if stage["stage_id"] == obj["current_stage_id"]:
                    stage["is_current_stage"] = False
                    current_stage_found = True
                if stage["stage_id"] == next_stage_id:
                    stage["is_current_stage"] = True
            
            if current_stage_found:
                obj["current_stage_id"] = next_stage_id
                self.add_player_memory(f"Progressed in objective '{obj['description']}' to stage: '{next_stage_id}'.")
                # Check if this new stage completes the objective
                new_current_stage = self.get_current_stage_for_objective(objective_id)
                if new_current_stage and new_current_stage.get("is_ending_stage", False):
                    self.complete_objective(objective_id, by_stage=True)
                return True
        return False


    def complete_objective(self, objective_id, by_stage=False):
        obj = self.get_objective_by_id(objective_id)
        if obj and not obj["completed"]:
            obj["completed"] = True
            obj["active"] = False # Usually completed objectives are no longer active
            if not by_stage: # Avoid double memory if completed via stage progression
                self.add_player_memory(f"Objective '{obj['description']}' was completed.")
            else:
                 self.add_player_memory(f"Objective '{obj['description']}' concluded with stage '{obj.get('current_stage_id', 'final')}''.")
            return True
        return False
    
    def activate_objective(self, objective_id):
        obj = self.get_objective_by_id(objective_id)
        if obj:
            obj["active"] = True
            # Potentially set a starting stage if not already set
            if "stages" in obj and "current_stage_id" not in obj and obj["stages"]:
                obj["current_stage_id"] = obj["stages"][0]["stage_id"]
                obj["stages"][0]["is_current_stage"] = True
            return True
        return False

