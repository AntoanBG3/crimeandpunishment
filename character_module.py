# character_module.py

# CHARACTERS_DATA remains largely the same but is now in this file.
# Objectives are part of this data.
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
            {"id": "escape_suspicion", "description": "Avoid the suspicion of Porfiry Petrovich regarding the murders.", "completed": False, "active": True},
            {"id": "understand_theory", "description": "Grapple with the validity and consequences of your 'extraordinary man' theory.", "completed": False, "active": True},
            {"id": "help_family", "description": "Find a way to alleviate your mother and sister's financial burdens without sacrificing Dunya.", "completed": False, "active": True}
        ]
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
            {"id": "guide_raskolnikov", "description": "Offer spiritual guidance and hope to Rodion Raskolnikov.", "completed": False, "active": True}
        ]
    },
    "Porfiry Petrovich": {
        "persona": "You are Porfiry Petrovich from Dostoevsky's 'Crime and Punishment'. You are an examining magistrate, intelligent, cunning, and psychologically astute. You enjoy engaging in intellectual cat-and-mouse games, often speaking in a roundabout, seemingly amiable, yet probing way. Your speech can be deceptively casual, peppered with subtle questions and observations.",
        "greeting": "Well, well, look who it is. Care for a little chat?",
        "default_location": "Porfiry's Office",
        "accessible_locations": [
            "Porfiry's Office", "Police Station (General Area)", "Haymarket Square", "Raskolnikov's Garret"
        ],
        "objectives": [
            {"id": "solve_murders", "description": "Uncover the truth behind the murders of Alyona Ivanovna and Lizaveta.", "completed": False, "active": True},
            {"id": "understand_criminal_mind", "description": "Explore the psychology of the criminal, particularly Raskolnikov if he is a suspect.", "completed": False, "active": True}
        ]
    },
    "Dunya Raskolnikova": {
        "persona": "You are Dunya Raskolnikova, Rodion's sister, from Dostoevsky's 'Crime and Punishment'. You are intelligent, strong-willed, virtuous, and deeply concerned for your brother. You are protective and prepared to make sacrifices, but not at the cost of your dignity. Your speech is articulate, composed, and reflects your strong moral compass.",
        "greeting": "Greetings. I hope you are well.",
        "default_location": "Pulcheria's Lodgings",
        "accessible_locations": [
            "Pulcheria's Lodgings", "Haymarket Square", "Raskolnikov's Garret", "Sonya's Room", "Tavern"
        ],
        "objectives": [
            {"id": "protect_rodion", "description": "Understand what is troubling Rodion and protect him from harm or folly.", "completed": False, "active": True},
            {"id": "resolve_luzhin", "description": "Deal with the unwelcome attentions and proposal of Pyotr Petrovich Luzhin.", "completed": False, "active": True},
            {"id": "assess_svidrigailov", "description": "Determine the true intentions of Arkady Svidrigailov.", "completed": False, "active": True}
        ]
    },
    "Arkady Svidrigailov": {
        "persona": "You are Arkady Svidrigailov from Dostoevsky's 'Crime and Punishment'. You are a sensualist, amoral, and enigmatic figure, haunted by his past and capable of both depravity and surprising acts of charity. You are often cynical, worldly, and your speech can be laced with double entendres or unsettling observations.",
        "greeting": "Ah, a new face. Or an old one? St. Petersburg is so full of... possibilities.",
        "default_location": "Tavern",
        "accessible_locations": [
            "Tavern", "Haymarket Square", "Sonya's Room", "Pulcheria's Lodgings", "Voznesensky Bridge",
            "Raskolnikov's Garret"
        ],
        "objectives": [
            {"id": "pursue_dunya", "description": "Attempt to win over Dunya Raskolnikova, by any means necessary.", "completed": False, "active": True},
            {"id": "escape_ennui", "description": "Find some amusement or meaning to escape your profound boredom and past ghosts.", "completed": False, "active": True}
        ]
    },
    "Dmitri Razumikhin": {
        "persona": "You are Dmitri Razumikhin from Dostoevsky's 'Crime and Punishment'. You are Raskolnikov's loyal friend, energetic, talkative, somewhat poor but resourceful and generally good-natured. You are practical and often try to help Raskolnikov. Your speech is enthusiastic, direct, and sometimes a bit boisterous.",
        "greeting": "Hello there! Good to see you! Care for a drink, or perhaps some work?",
        "default_location": "Tavern",
        "accessible_locations": [
            "Tavern", "Haymarket Square", "Raskolnikov's Garret", "Stairwell (Outside Raskolnikov's Garret)",
            "Pulcheria's Lodgings", "Police Station (General Area)", "Sonya's Room"
        ],
        "objectives": [
            {"id": "help_raskolnikov", "description": "Figure out what's wrong with Raskolnikov and help him get back on his feet.", "completed": False, "active": True},
            {"id": "support_dunya_pulcheria", "description": "Offer assistance and protection to Dunya and Pulcheria Alexandrovna.", "completed": False, "active": True}
        ]
    },
    "Pulcheria Alexandrovna Raskolnikova": {
        "persona": "You are Pulcheria Alexandrovna Raskolnikova, Rodion's mother. You are loving, anxious, and deeply devoted to your children, often to the point of idealizing them. You've traveled to St. Petersburg with Dunya out of concern for Rodion. Your speech is warm, motherly, but often reveals your underlying worries.",
        "greeting": "Rodya, my dear boy! Or... oh, excuse me. Hello.",
        "default_location": "Pulcheria's Lodgings",
        "accessible_locations": [
            "Pulcheria's Lodgings", "Raskolnikov's Garret", "Haymarket Square", "Sonya's Room"
        ],
        "objectives": [
            {"id": "ensure_rodyas_wellbeing", "description": "Understand why Rodya is so troubled and ensure he is safe and well.", "completed": False, "active": True},
            {"id": "see_dunya_settled", "description": "Hope for Dunya to find a secure and happy future.", "completed": False, "active": True}
        ]
    }
}


class Character:
    def __init__(self, name, persona, greeting, default_location, accessible_locations, objectives=None, is_player=False):
        self.name = name
        self.persona = persona
        self.greeting = greeting
        self.default_location = default_location
        self.current_location = default_location # NPCs can also move, potentially
        self.accessible_locations = accessible_locations
        self.is_player = is_player
        self.conversation_histories = {} 
        self.memory_about_player = [] 
        self.relationship_with_player = 0 
        self.objectives = [obj.copy() for obj in objectives] if objectives else [] # Ensure objectives are copied

    def add_to_history(self, other_char_name, speaker_name, text):
        if other_char_name not in self.conversation_histories:
            self.conversation_histories[other_char_name] = []
        self.conversation_histories[other_char_name].append(f"{speaker_name}: {text}")

    def get_formatted_history(self, other_char_name, limit=6):
        history = self.conversation_histories.get(other_char_name, [])
        return "\n".join(history[-limit:])
    
    def add_player_memory(self, memory_fact):
        if memory_fact not in self.memory_about_player:
            self.memory_about_player.append(memory_fact)
            if len(self.memory_about_player) > 10: # Increased memory size
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

    def complete_objective(self, objective_id):
        obj = self.get_objective_by_id(objective_id)
        if obj:
            obj["completed"] = True
            # Potentially add a memory about completing it
            self.add_player_memory(f"Objective '{obj['description']}' was addressed or completed.")
            return True
        return False
    
    def activate_objective(self, objective_id):
        obj = self.get_objective_by_id(objective_id)
        if obj:
            obj["active"] = True
            return True
        return False

