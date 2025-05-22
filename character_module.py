# character_module.py
import random
import copy

CHARACTERS_DATA = {
    "Rodion Raskolnikov": {
        "persona": "You are Rodion Raskolnikov from Dostoevsky's 'Crime and Punishment'. You are impoverished, proud, and highly intelligent. You are tormented by your philosophical theory about 'extraordinary' men and your recent actions. You are often aloof, suspicious, and prone to bouts of feverish intensity. Your speech should reflect your intellectualism, internal conflict, and occasional abruptness.",
        "greeting": "Hmph. What do you want?",
        "default_location": "Raskolnikov's Garret",
        "accessible_locations": [
            "Raskolnikov's Garret", "Stairwell (Outside Raskolnikov's Garret)", "Haymarket Square", "Tavern",
            "Sonya's Room", "Police Station (General Area)", "Porfiry's Office",
            "Pawnbroker's Apartment Building", "Pawnbroker's Apartment", "Voznesensky Bridge", "Pulcheria's Lodgings",
            "Katerina Ivanovna's Apartment"
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
                    {"stage_id": "received_cross_from_sonya", "description": "Sonya has given you her cypress cross, a symbol of shared suffering and potential redemption.", "is_current_stage": False},
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
                     {"stage_id": "theory_shattered", "description": "Recognize the flaws and inhumanity of the theory.", "is_current_stage": False, "linked_to_objective_completion": {"id": "grapple_with_crime", "stage_to_advance_to": "seek_sonya"}},
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
                    {"stage_id": "family_secure", "description": "Ensure Dunya is safe and your mother is somewhat at peace.", "is_current_stage": False, "is_ending_stage": True},
                 ]
            },
            {
                "id": "ponder_redemption",
                "description": "Reflect on the meaning of Sonya's cross and the possibility of redemption.",
                "completed": False, "active": False, "current_stage_id": "initial_reflection",
                "stages": [
                    {"stage_id": "initial_reflection", "description": "The weight of the cross prompts unsettling thoughts of guilt and sacrifice.", "is_current_stage": True},
                    {"stage_id": "glimmer_of_hope", "description": "A fleeting sense that suffering might lead to something beyond despair.", "is_current_stage": False},
                    {"stage_id": "path_to_confession_clearer", "description": "The cross becomes a concrete symbol of the path Sonya represents.", "is_current_stage": False}
                ]
            }
        ],
        "inventory_items": [{"name": "mother's letter", "quantity": 1}, {"name": "worn coin", "quantity": 5}],
        "schedule": {
            "Morning": "Raskolnikov's Garret",
            "Afternoon": "Haymarket Square",
            "Evening": "Raskolnikov's Garret",
            "Night": "Raskolnikov's Garret"
        },
        "skills": {
            "Academia": 2,
            "Observation": 1, # Base Raskolnikov Observation
            "Persuasion": 1, # Added Persuasion for Raskolnikov
            "Streetwise": 0
        }
    },
    "Sonya Marmeladova": {
        "persona": "You are Sonya Marmeladova from Dostoevsky's 'Crime and Punishment'. You are deeply religious, compassionate, and self-sacrificing, despite your difficult circumstances. You are shy but possess a profound inner strength and unwavering faith. Your speech is often gentle, earnest, and may include references to God or scripture.",
        "greeting": "Oh... hello. May God be with you.",
        "default_location": "Sonya's Room",
        "accessible_locations": [
            "Sonya's Room", "Haymarket Square", "Raskolnikov's Garret", "Pulcheria's Lodgings",
            "Police Station (General Area)", "Tavern", "Katerina Ivanovna's Apartment"
        ],
        "objectives": [ # Objectives for Sonya
            {
                "id": "support_family", "description": "Continue to support the Marmeladov children and Katerina Ivanovna.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Provide for the family amidst hardship."}]
            },
            {
                "id": "guide_raskolnikov", "description": "Offer spiritual guidance and hope to Rodion Raskolnikov, urging him towards confession.",
                "completed": False, "active": True, "current_stage_id": "initial_encounter",
                "stages": [
                    {"stage_id": "initial_encounter", "description": "Recognize a shared suffering in Raskolnikov."},
                    {"stage_id": "lazarus_reading", "description": "Read the story of Lazarus to Raskolnikov, offering a path to spiritual rebirth."},
                    {"stage_id": "offer_cross", "description": "Offer Raskolnikov her cypress cross as a symbol of shared suffering and redemption."},
                    {"stage_id": "receive_confession", "description": "Hear Raskolnikov's confession and urge him to accept his suffering."},
                    {"stage_id": "follow_to_siberia", "description": "Decide to follow Raskolnikov to Siberia.", "is_ending_stage": True}
                ]
            }
        ],
        "inventory_items": [
            {"name": "Sonya's New Testament", "quantity": 1},
            {"name": "Sonya's Cypress Cross", "quantity": 1}
        ],
        "npc_relationships": {
            "Katerina Ivanovna Marmeladova": -1,
            "Rodion Raskolnikov": 0 
        },
        "skills": {
            "Observation": 2, # Sonya is observant
            "Persuasion": 0, 
            "Streetwise": 1, 
            "Academia": 0
        },
        "schedule": {
            "Morning": "Sonya's Room",
            "Afternoon": "Katerina Ivanovna's Apartment", 
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
                "id": "solve_murders", "description": "Uncover the truth behind the murders of Alyona Ivanovna and Lizaveta, focusing on Raskolnikov.",
                "completed": False, "active": True, "current_stage_id": "initial_suspicion",
                "stages": [
                    {"stage_id": "initial_suspicion", "description": "Observe Raskolnikov and gather preliminary impressions."},
                    {"stage_id": "psychological_probes", "description": "Engage Raskolnikov in conversations designed to test his guilt and theories."},
                    {"stage_id": "closing_the_net", "description": "Subtly reveal the strength of the evidence or understanding of Raskolnikov's mind."},
                    {"stage_id": "encourage_confession", "description": "Offer Raskolnikov a chance to confess for a potentially lighter sentence."},
                    {"stage_id": "case_solved", "description": "Raskolnikov confesses or is irrefutably proven guilty.", "is_ending_stage": True}
                ]
            },
            {
                "id": "understand_criminal_mind", "description": "Explore the psychology of the criminal, particularly Raskolnikov's 'extraordinary man' theory.",
                "completed": False, "active": True, "current_stage_id": "default",
                 "stages" : [{"stage_id": "default", "description": "Observe and analyze criminal behavior."}]
            }
        ],
        "inventory_items": [], 
        "npc_relationships": {
            "Rodion Raskolnikov": 0,
            "Dmitri Razumikhin": 0 
        },
        "skills": {
            "Observation": 3, # Porfiry is highly observant
            "Persuasion": 2,  # Updated Porfiry's Persuasion
            "Academia": 1,    
            "Streetwise": 0
        },
        "schedule": { 
            "Morning": "Porfiry's Office",
            "Afternoon": "Porfiry's Office",
            "Evening": "Police Station (General Area)", 
            "Night": "Porfiry's Office" 
        }
    },
    "Dunya Raskolnikova": {
        "persona": "You are Dunya Raskolnikova, Rodion's sister, from Dostoevsky's 'Crime and Punishment'. You are intelligent, strong-willed, virtuous, and deeply concerned for your brother. You are protective and prepared to make sacrifices, but not at the cost of your dignity. Your speech is articulate, composed, and reflects your strong moral compass.",
        "greeting": "Greetings. I hope you are well. Rodya has been so... unlike himself.",
        "default_location": "Pulcheria's Lodgings",
        "accessible_locations": [
            "Pulcheria's Lodgings", "Haymarket Square", "Raskolnikov's Garret", "Sonya's Room", "Tavern",
            "Katerina Ivanovna's Apartment"
        ],
        "objectives": [ 
            {
                "id": "protect_rodion", "description": "Understand what is troubling Rodion and protect him from harm or folly.",
                "completed": False, "active": True, "current_stage_id": "default",
                 "stages" : [{"stage_id": "default", "description": "Seek to understand and aid Rodion."}]
            },
            {
                "id": "resolve_luzhin", "description": "Deal with the unwelcome attentions and proposal of Pyotr Petrovich Luzhin.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Address the situation with Luzhin."}]
            },
            {
                "id": "assess_svidrigailov", "description": "Determine the true intentions of Arkady Svidrigailov and protect herself.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Be wary of Svidrigailov."}]
            }
        ],
        "inventory_items": [],
        "skills": { # Added skills for Dunya
            "Observation": 2,
            "Persuasion": 1
        },
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
            "Raskolnikov's Garret", "Katerina Ivanovna's Apartment"
        ],
        "objectives": [ 
            {
                "id": "pursue_dunya", "description": "Attempt to win over Dunya Raskolnikova, employing various means.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Consider your approach towards Dunya."}]
            },
            {
                "id": "escape_ennui", "description": "Find some amusement or meaning to escape your profound boredom and past ghosts, perhaps through Raskolnikov or Dunya.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Seek distraction from your ennui."}]

            },
            {
                "id": "final_reckoning", "description": "Confront the emptiness of his existence.",
                "completed": False, "active": False, "current_stage_id": "default", 
                "stages" : [{"stage_id": "default", "description": "The end approaches."}]
            }
        ],
        "inventory_items": [{"name": "worn coin", "quantity": 100}],
        "skills": { # Added skills for Svidrigailov
            "Observation": 2,
            "Persuasion": 2
        },
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
            "Pulcheria's Lodgings", "Police Station (General Area)", "Sonya's Room", "Katerina Ivanovna's Apartment"
        ],
        "objectives": [ 
            {
                "id": "help_raskolnikov", "description": "Figure out what's wrong with Raskolnikov and help him get back on his feet.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Worry about Rodya and try to assist him."}]
            },
            {
                "id": "support_dunya_pulcheria", "description": "Offer assistance and protection to Dunya and Pulcheria Alexandrovna.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Look out for Rodya's family."}]
            }
        ],
        "inventory_items": [{"name": "worn coin", "quantity": 15}],
        "npc_relationships": {
            "Rodion Raskolnikov": 5,
            "Dunya Raskolnikova": 2,
            "Porfiry Petrovich": -1
        },
        "skills": { # Added skills for Razumikhin
            "Observation": 1,
            "Persuasion": 0
        },
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
            "Pulcheria's Lodgings", "Raskolnikov's Garret", "Haymarket Square", "Sonya's Room",
            "Katerina Ivanovna's Apartment"
        ],
        "objectives": [ 
            {
                "id": "ensure_rodyas_wellbeing", "description": "Understand why Rodya is so troubled and ensure he is safe and well.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Be deeply concerned for Rodion's state."}]
            },
            {
                "id": "see_dunya_settled", "description": "Hope for Dunya to find a secure and happy future.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Wish for Dunya's happiness and security."}]
            }
        ],
        "inventory_items": [],
        "schedule": {
            "Morning": "Pulcheria's Lodgings",
            "Afternoon": "Raskolnikov's Garret", 
            "Evening": "Pulcheria's Lodgings",
            "Night": "Pulcheria's Lodgings"
        }
    },
    "Katerina Ivanovna Marmeladova": {
        "persona": "You are Katerina Ivanovna Marmeladova, a proud, consumptive, and increasingly desperate woman, widow of Semyon Marmeladov and stepmother to Sonya. You cling to the remnants of a supposed aristocratic past, often erupting in histrionic fits of coughing, anger, and lamentation. Your speech is erratic, veering between haughty pronouncements, bitter complaints about poverty and injustice, and tender, sorrowful words for your children.",
        "greeting": "Who are you to disturb a respectable, albeit unfortunate, family? Can't you see we are suffering? Oh, the indignity! The children are starving!",
        "default_location": "Katerina Ivanovna's Apartment",
        "accessible_locations": [
            "Katerina Ivanovna's Apartment", "Haymarket Square", "Sonya's Room", "Tavern"
        ],
        "objectives": [ 
            {
                "id": "lament_fate", "description": "Express outrage and despair at her family's poverty and the injustices of the world.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Voice her grievances loudly and often."}]
            },
            {
                "id": "care_for_children", "description": "Attempt to care for her young children (Polenka, Kolya, Lida) amidst growing illness and poverty.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Struggle to provide for her children."}]
            },
            {
                "id": "memorial_dinner_for_marmeladov", "description": "Obsessively plan a grand (and financially ruinous) memorial dinner for Marmeladov.",
                "completed": False, "active": False, "current_stage_id": "planning",
                "stages": [
                    {"stage_id": "planning", "description": "Frantically try to arrange a memorial dinner beyond her means."},
                    {"stage_id": "dinner_chaos", "description": "The memorial dinner descends into chaos and further humiliation.", "is_ending_stage": True}
                ]
            }
        ],
        "inventory_items": [{"name": "tattered handkerchief", "quantity": 1}],
        "schedule": { 
            "Morning": "Katerina Ivanovna's Apartment",
            "Afternoon": "Katerina Ivanovna's Apartment", 
            "Evening": "Katerina Ivanovna's Apartment",
            "Night": "Katerina Ivanovna's Apartment"
        },
        "apparent_state": "feverish and agitated" 
    },
    "Police Clerk Ilya": {
        "persona": "You are Ilya, a junior police clerk. You are overworked, somewhat officious, and keen to follow procedure. You mostly deal with paperwork and minor complaints, often sighing about the chaos of the station. You address people formally.",
        "greeting": "Yes? State your business, please. Quickly, I have much to attend to.",
        "default_location": "Police Station (General Area)",
        "accessible_locations": ["Police Station (General Area)", "Porfiry's Office"], 
        "objectives": [
            {
                "id": "maintain_order", "description": "Try to keep the station's administrative tasks in order.",
                "completed": False, "active": True, "current_stage_id": "default",
                 "stages" : [{"stage_id": "default", "description": "Process paperwork and direct petitioners."}]
            }
        ],
        "inventory_items": [],
        "schedule": {
            "Morning": "Police Station (General Area)",
            "Afternoon": "Police Station (General Area)",
            "Evening": "Police Station (General Area)",
            "Night": "Police Station (General Area)" 
        },
        "apparent_state": "harried"
    },
    "Officer Volkov": {
        "persona": "You are Officer Volkov, a seasoned but weary police officer. You've seen much in your time on the St. Petersburg streets and are generally cynical and taciturn. You might offer a gruff comment or a suspicious glance. You don't waste words.",
        "greeting": "Hmph. What is it now?",
        "default_location": "Police Station (General Area)",
        "accessible_locations": ["Police Station (General Area)", "Haymarket Square"], 
        "objectives": [
            {
                "id": "keep_peace", "description": "Maintain a semblance of order on the streets and in the station.",
                "completed": False, "active": True, "current_stage_id": "default",
                "stages" : [{"stage_id": "default", "description": "Observe and intervene if necessary."}]
            }
        ],
        "inventory_items": [],
        "schedule": {
            "Morning": "Police Station (General Area)",
            "Afternoon": "Haymarket Square", 
            "Evening": "Police Station (General Area)",
            "Night": "Haymarket Square" 
        },
        "apparent_state": "watchful"
    }
}


class Character:
    def __init__(self, name, persona, greeting, default_location, accessible_locations,
                 objectives=None, inventory_items=None, schedule=None, npc_relationships=None, skills_data=None, is_player=False):
        self.name = name
        self.persona = persona
        self.greeting = greeting
        self.default_location = default_location
        self.current_location = default_location
        self.accessible_locations = accessible_locations if accessible_locations is not None else [default_location]
        self.is_player = is_player
        self.conversation_histories = {}
        self.memory_about_player = []  # List of dictionaries
        self.journal_entries = [] 
        self.relationship_with_player = 0
        self.npc_relationships = copy.deepcopy(npc_relationships) if npc_relationships is not None else {}
        self.skills = copy.deepcopy(skills_data) if skills_data is not None else {}
        
        self.objectives = []
        if objectives:
            for obj_template in objectives:
                obj = copy.deepcopy(obj_template)
                obj["completed"] = obj.get("completed", False)
                obj["active"] = obj.get("active", True) 
                if "stages" not in obj or not obj["stages"]:
                    obj["stages"] = [{"stage_id": "default", "description": "Initial state of objective.", "is_current_stage": True}]
                
                current_stage_id_present = "current_stage_id" in obj
                current_stage_is_valid = False
                if current_stage_id_present:
                    for stage in obj["stages"]:
                        if stage.get("stage_id") == obj["current_stage_id"]:
                            stage["is_current_stage"] = True
                            current_stage_is_valid = True
                        else:
                            stage["is_current_stage"] = False
                
                if not current_stage_id_present or not current_stage_is_valid:
                    if obj["stages"]: 
                        obj["current_stage_id"] = obj["stages"][0].get("stage_id")
                        obj["stages"][0]["is_current_stage"] = True
                    else: 
                        obj["current_stage_id"] = "default"

                self.objectives.append(obj)


        self.inventory = [copy.deepcopy(item) for item in inventory_items] if inventory_items else []
        self.schedule = schedule if schedule else {}
        self.apparent_state = CHARACTERS_DATA.get(name, {}).get("apparent_state", "normal")


    def add_journal_entry(self, entry_type, text_content, game_day_time_period_str):
        MAX_JOURNAL_ENTRIES = 20 
        if len(self.journal_entries) >= MAX_JOURNAL_ENTRIES:
            self.journal_entries.pop(0) 
        
        entry = f"({game_day_time_period_str}) [{entry_type.upper()}]: {text_content}"
        self.journal_entries.append(entry)

    def get_journal_summary(self, count=5):
        if not self.journal_entries:
            return "Journal is empty."
        return "\nRecent Journal Entries:\n" + "\n".join(self.journal_entries[-count:])


    def to_dict(self):
        return {
            "name": self.name,
            "current_location": self.current_location,
            "is_player": self.is_player,
            "conversation_histories": self.conversation_histories,
            "memory_about_player": self.memory_about_player,
            "journal_entries": self.journal_entries, 
            "relationship_with_player": self.relationship_with_player,
            "npc_relationships": self.npc_relationships,
            "skills": self.skills,
            "objectives": self.objectives,
            "inventory": self.inventory,
            "apparent_state": self.apparent_state,
        }

    @classmethod
    def from_dict(cls, data, static_char_data):
        static_char_data_safe = static_char_data if static_char_data is not None else {}
        
        char = cls(
            name=data["name"], 
            persona=static_char_data_safe.get("persona", "A mysterious figure."),
            greeting=static_char_data_safe.get("greeting", "Hello."),
            default_location=static_char_data_safe.get("default_location", "Unknown Location"),
            accessible_locations=static_char_data_safe.get("accessible_locations", []),
            objectives=[], 
            inventory_items=data.get("inventory", []), 
            schedule=static_char_data_safe.get("schedule", {}),
            npc_relationships=static_char_data_safe.get("npc_relationships", {}), 
            skills_data=static_char_data_safe.get("skills", {}),
            is_player=data.get("is_player", False) 
        )
        
        char.current_location = data.get("current_location", char.default_location)
        char.conversation_histories = data.get("conversation_histories", {})
        char.memory_about_player = data.get("memory_about_player", []) # Ensures backward compatibility
        char.journal_entries = data.get("journal_entries", []) 
        char.relationship_with_player = data.get("relationship_with_player", 0)
        char.apparent_state = data.get("apparent_state", static_char_data_safe.get("apparent_state", "normal"))

        saved_npc_relationships = data.get("npc_relationships")
        if saved_npc_relationships is not None:
            char.npc_relationships = saved_npc_relationships
        
        saved_skills = data.get("skills")
        if saved_skills is not None:
            char.skills = saved_skills

        loaded_objectives_map = {obj['id']: obj for obj in data.get("objectives", []) if 'id' in obj}
        static_objectives_template = static_char_data_safe.get("objectives", [])
        
        final_objectives_list = []
        if static_objectives_template:
            for static_obj_template_item in static_objectives_template:
                obj_id = static_obj_template_item.get("id")
                if not obj_id: continue

                final_obj = copy.deepcopy(static_obj_template_item) 

                if obj_id in loaded_objectives_map: 
                    loaded_obj_data = loaded_objectives_map[obj_id]
                    final_obj["completed"] = loaded_obj_data.get("completed", final_obj.get("completed", False))
                    final_obj["active"] = loaded_obj_data.get("active", final_obj.get("active", True))
                    final_obj["current_stage_id"] = loaded_obj_data.get("current_stage_id", final_obj.get("current_stage_id"))

                if "stages" in final_obj and final_obj["stages"]:
                    current_stage_id_found_in_stages = False
                    for stage_in_final_obj in final_obj["stages"]:
                        is_current = (stage_in_final_obj.get("stage_id") == final_obj.get("current_stage_id"))
                        stage_in_final_obj["is_current_stage"] = is_current
                        if is_current:
                            current_stage_id_found_in_stages = True
                    if not current_stage_id_found_in_stages and final_obj["stages"]: 
                        final_obj["current_stage_id"] = final_obj["stages"][0].get("stage_id")
                        final_obj["stages"][0]["is_current_stage"] = True
                elif "stages" not in final_obj or not final_obj.get("stages"): 
                     final_obj["stages"] = [{"stage_id": "default", "description": "Objective state.", "is_current_stage": True}]
                     final_obj["current_stage_id"] = "default"

                final_objectives_list.append(final_obj)
        
        for loaded_id, loaded_obj_val in loaded_objectives_map.items():
            if not any(fo.get('id') == loaded_id for fo in final_objectives_list):
                loaded_obj_val["stages"] = loaded_obj_val.get("stages", [{"stage_id": "default", "description": "Legacy objective state.", "is_current_stage": True}])
                if "current_stage_id" not in loaded_obj_val and loaded_obj_val.get("stages"):
                    loaded_obj_val["current_stage_id"] = loaded_obj_val["stages"][0].get("stage_id")
                if loaded_obj_val.get("stages"): 
                    for stage in loaded_obj_val["stages"]:
                        stage["is_current_stage"] = (stage.get("stage_id") == loaded_obj_val.get("current_stage_id"))
                loaded_obj_val["active"] = loaded_obj_val.get("active", True)
                loaded_obj_val["completed"] = loaded_obj_val.get("completed", False)
                final_objectives_list.append(loaded_obj_val)
        
        char.objectives = final_objectives_list
        return char

    def add_to_inventory(self, item_name, quantity=1):
        from game_config import DEFAULT_ITEMS 
        if item_name not in DEFAULT_ITEMS:
            return False

        item_props = DEFAULT_ITEMS[item_name]
        is_stackable = item_props.get("stackable", False) or item_props.get("value") is not None

        for item in self.inventory:
            if item["name"] == item_name:
                if is_stackable:
                    item["quantity"] = item.get("quantity", 1) + quantity
                    return True
                else: 
                    return False 

        new_item_entry = {"name": item_name}
        if is_stackable:
            new_item_entry["quantity"] = quantity
        elif quantity > 1: 
            pass 

        self.inventory.append(new_item_entry) 
        return True


    def remove_from_inventory(self, item_name, quantity=1):
        from game_config import DEFAULT_ITEMS
        item_props = DEFAULT_ITEMS.get(item_name, {})
        is_stackable = item_props.get("stackable", False) or item_props.get("value") is not None

        for i, item in enumerate(self.inventory):
            if item["name"] == item_name:
                if is_stackable:
                    current_quantity = item.get("quantity", 1)
                    if current_quantity > quantity:
                        item["quantity"] -= quantity
                        return True
                    elif current_quantity == quantity:
                        self.inventory.pop(i)
                        return True
                    else: 
                        return False
                else: 
                    if quantity == 1: 
                        self.inventory.pop(i)
                        return True
                    else: 
                        return False
        return False 

    def has_item(self, item_name, quantity=1):
        from game_config import DEFAULT_ITEMS
        item_props = DEFAULT_ITEMS.get(item_name, {})
        is_stackable = item_props.get("stackable", False) or item_props.get("value") is not None

        for item in self.inventory:
            if item["name"] == item_name:
                if is_stackable:
                    return item.get("quantity", 1) >= quantity
                else: 
                    return quantity == 1 
        return False

    def get_notable_carried_items_summary(self):
        from game_config import DEFAULT_ITEMS
        if not self.inventory:
            return "is not carrying anything of note."
        notable_items_list = []
        for item_data in self.inventory:
            item_name = item_data["name"]
            item_props = DEFAULT_ITEMS.get(item_name, {})
            qty = item_data.get("quantity", 1) if item_props.get("stackable") or item_props.get("value") is not None else 1

            if item_props.get("is_notable", False):
                item_str = item_name
                if (item_props.get("stackable") or item_props.get("value") is not None) and qty > 1:
                    item_str += f" (x{qty})"
                notable_items_list.append(item_str)
            elif item_name == "worn coin" and qty >= item_props.get("notable_threshold", 20): 
                 notable_items_list.append(f"a sum of money ({qty} coins)")
        if not notable_items_list:
            return "is not carrying anything particularly noteworthy."
        if len(notable_items_list) == 1:
            return f"is carrying {notable_items_list[0]}."
        elif len(notable_items_list) == 2:
            return f"is carrying {notable_items_list[0]} and {notable_items_list[1]}."
        else: 
            return f"is carrying {', '.join(notable_items_list[:-1])}, and {notable_items_list[-1]}."

    def get_inventory_description(self):
        if not self.inventory:
            return "You are carrying nothing."
        descriptions = []
        from game_config import DEFAULT_ITEMS
        for item_data in self.inventory:
            item_name = item_data["name"]
            item_props = DEFAULT_ITEMS.get(item_name, {})
            is_stackable = item_props.get("stackable", False) or item_props.get("value") is not None
            quantity = item_data.get("quantity", 1) if is_stackable else 1

            if is_stackable and quantity > 1 :
                descriptions.append(f"{item_name} (x{quantity})")
            else:
                descriptions.append(item_name)
        return "You are carrying: " + ", ".join(descriptions) + "."

    def add_to_history(self, other_char_name, speaker_name, text):
        if other_char_name not in self.conversation_histories:
            self.conversation_histories[other_char_name] = []
        max_history = 10 
        self.conversation_histories[other_char_name].append(f"{speaker_name}: {text}")
        if len(self.conversation_histories[other_char_name]) > max_history:
            self.conversation_histories[other_char_name].pop(0) 

    def get_formatted_history(self, other_char_name, limit=6):
        history = self.conversation_histories.get(other_char_name, [])
        return "\n".join(history[-limit:])

    def add_player_memory(self, memory_type: str, turn: int, content: dict, sentiment_impact: int = 0):
        """
        Adds a structured memory about the player.
        memory_type: e.g., "received_item", "dialogue_exchange", "player_action_observed"
        turn: The game turn number.
        content: Dictionary with details specific to the type.
        sentiment_impact: Optional integer indicating sentiment impact.
        """
        # Basic validation to ensure content is a dictionary
        if not isinstance(content, dict):
            print(f"Error: Memory content for type '{memory_type}' must be a dictionary. Received: {content}")
            # Potentially add a default error memory or skip adding this memory
            return

        memory_entry = {
            "type": memory_type,
            "turn": turn,
            "content": content,
            "sentiment_impact": sentiment_impact
        }
        
        # Avoid duplicate exact memories if necessary, though turn makes most unique
        # For now, allow all memories to be added.
        self.memory_about_player.append(memory_entry)
        
        MAX_MEMORIES = 30  # Increased slightly
        if len(self.memory_about_player) > MAX_MEMORIES:
            self.memory_about_player.pop(0)

    def get_player_memory_summary(self, current_turn: int, count: int = 7):
        if not self.memory_about_player:
            return "You don't recall any specific interactions or observations about them yet."

        # Sort memories by turn, most recent first, then by sentiment impact
        # Lambda takes a memory dict and returns a tuple for sorting.
        # Sort primarily by recency (descending), then by absolute sentiment impact (descending)
        sorted_memories = sorted(
            self.memory_about_player,
            key=lambda m: (m.get("turn", 0), abs(m.get("sentiment_impact", 0))),
            reverse=True
        )

        summary_parts = []
        for mem in sorted_memories[:count]:
            turn_ago = current_turn - mem.get("turn", current_turn)
            recency_prefix = ""
            if turn_ago == 0:
                recency_prefix = "Just now, "
            elif turn_ago == 1:
                recency_prefix = "A moment ago, "
            elif turn_ago < 5:
                recency_prefix = "Recently, "
            else:
                recency_prefix = "Some time ago, "

            content_str = "details unclear"
            mem_type = mem.get("type")
            content = mem.get("content", {})

            if mem_type == "received_item":
                item_name = content.get("item_name", "an item")
                qty = content.get("quantity", 1)
                content_str = f"player gave me {item_name}{f' (x{qty})' if qty > 1 else ''}"
            elif mem_type == "gave_item_to_player":
                item_name = content.get("item_name", "an item")
                qty = content.get("quantity", 1)
                content_str = f"I gave {item_name}{f' (x{qty})' if qty > 1 else ''} to the player"
            elif mem_type == "dialogue_exchange":
                player_stmt = content.get("player_statement", "something")
                topic = content.get("topic_hint", "")
                sentiment = mem.get("sentiment_impact", 0)
                if topic:
                    content_str = f"we talked about {topic}"
                    if player_stmt and player_stmt != "...":
                         content_str += f", and they said '{player_stmt[:50]}...'"
                else:
                    content_str = f"player said '{player_stmt[:50]}...'"
                if sentiment > 0:
                    content_str += " (it was a positive exchange)"
                elif sentiment < 0:
                    content_str += " (it was a negative exchange)"
            elif mem_type == "player_action_observed":
                action = content.get("action", "did something")
                location = content.get("location")
                target = content.get("target_item")
                if target:
                    action_desc = f"player {action} {target}"
                else:
                    action_desc = f"player {action}"
                if location:
                    content_str = f"{action_desc} in {location}"
                else:
                    content_str = action_desc
            elif mem_type == "relationship_change": # For direct relationship updates
                direction = "positively" if content.get("change", 0) > 0 else "negatively"
                reason = content.get("reason", "something they did or said")
                content_str = f"my view of them changed {direction} because of {reason}"
            else: # Fallback for old string memories or unknown types
                if isinstance(mem, str): # Handle old format
                    content_str = mem 
                elif isinstance(content, dict) and "summary" in content: # If new type has a summary
                    content_str = content["summary"]
                elif isinstance(content, str): # If content is just a string
                    content_str = content
            
            summary_parts.append(recency_prefix + content_str)

        if not summary_parts:
            return "You have some fleeting recollections, but nothing stands out clearly."
        
        return "Key things you recall about them: " + "; ".join(summary_parts) + "."

    def update_relationship(self, player_dialogue: str, positive_keywords: list[str], negative_keywords: list[str], game_turn: int):
        change = 0
        player_dialogue_lower = player_dialogue.lower()
        for keyword in positive_keywords:
            if keyword in player_dialogue_lower:
                change += 1
        for keyword in negative_keywords:
            if keyword in player_dialogue_lower:
                change -= 1
        
        if change != 0: 
            self.relationship_with_player += change
            self.relationship_with_player = max(-10, min(10, self.relationship_with_player))
            # Add a memory for the relationship change
            if change != 0:
                self.add_player_memory(
                    memory_type="relationship_change",
                    turn=game_turn,
                    content={
                        "reason": f"their statement ('{player_dialogue[:30]}...')",
                        "change": change
                    },
                    sentiment_impact=change
                )

    def get_objective_by_id(self, objective_id):
        if not objective_id: return None
        for obj in self.objectives:
            if obj.get("id") == objective_id:
                return obj
        return None

    def get_current_stage_for_objective(self, objective_id):
        obj = self.get_objective_by_id(objective_id)
        if obj and obj.get("current_stage_id") and obj.get("stages"):
            for stage in obj["stages"]:
                if stage.get("stage_id") == obj["current_stage_id"]:
                    return stage
        return None

    def advance_objective_stage(self, objective_id, next_stage_id):
        obj = self.get_objective_by_id(objective_id)
        if obj and obj.get("stages"):
            current_stage_found_in_obj = False
            next_stage_obj_from_template = None 
            
            for s_val_in_obj_stages in obj["stages"]:
                if s_val_in_obj_stages.get("stage_id") == next_stage_id:
                    next_stage_obj_from_template = s_val_in_obj_stages
                    break
            
            if not next_stage_obj_from_template:
                return False

            for stage_in_obj in obj["stages"]: 
                stage_in_obj["is_current_stage"] = (stage_in_obj.get("stage_id") == next_stage_id)
                if stage_in_obj["is_current_stage"]: 
                    current_stage_found_in_obj = True 

            if current_stage_found_in_obj: 
                obj["current_stage_id"] = next_stage_id
                new_stage_desc = next_stage_obj_from_template.get('description', 'unnamed stage')
                
                if self.is_player:
                    # Player memories are simple strings for now, not using the new dict structure.
                    # This could be enhanced later if player also needs structured memory.
                    self.memory_about_player.append(f"Made progress on '{obj.get('description','Unnamed Objective')}': now at '{new_stage_desc}'.")
                
                if next_stage_obj_from_template.get("is_ending_stage", False):
                    self.complete_objective(objective_id, by_stage=True)
                return True
        return False

    def complete_objective(self, objective_id, by_stage=False):
        obj = self.get_objective_by_id(objective_id)
        if obj and not obj.get("completed", False):
            obj["completed"] = True
            obj["active"] = False  
            obj_desc = obj.get('description', 'Unnamed Objective')
            if self.is_player:
                current_stage_for_memory = self.get_current_stage_for_objective(objective_id)
                stage_desc_for_memory = current_stage_for_memory.get('description', 'final stage') if current_stage_for_memory else 'final stage'
                
                if not by_stage:
                    # Player memories are simple strings
                    self.memory_about_player.append(f"Objective '{obj_desc}' was completed.")
                else:
                    # Player memories are simple strings
                    self.memory_about_player.append(f"Objective '{obj_desc}' concluded with stage '{stage_desc_for_memory}'.")
                print(f"[DEBUG] Player {self.name} completed objective: {obj_desc} (Stage: {stage_desc_for_memory if by_stage else 'N/A'})")

            link_info = None
            current_stage = self.get_current_stage_for_objective(objective_id)
            if current_stage and "linked_to_objective_completion" in current_stage:
                link_info = current_stage["linked_to_objective_completion"]
            elif "linked_to_objective_completion" in obj:
                link_info = obj["linked_to_objective_completion"]

            if link_info:
                target_objective_id = None
                specific_next_stage_id = None

                if isinstance(link_info, str): 
                    target_objective_id = link_info
                elif isinstance(link_info, dict): 
                    target_objective_id = link_info.get("id")
                    specific_next_stage_id = link_info.get("stage_to_advance_to")

                if target_objective_id:
                    target_objective = self.get_objective_by_id(target_objective_id)
                    if target_objective:
                        target_obj_desc = target_objective.get('description', 'Unnamed Linked Objective')
                        if not target_objective.get("active", False) and not target_objective.get("completed", False) :
                            print(f"[DEBUG] Linking: Activating objective '{target_obj_desc}' due to completion of '{obj_desc}'.")
                            self.activate_objective(target_objective_id) 
                            if specific_next_stage_id and target_objective.get("current_stage_id") != specific_next_stage_id :
                                print(f"[DEBUG] Linking: Advancing newly activated objective '{target_obj_desc}' to specific stage '{specific_next_stage_id}'.")
                                self.advance_objective_stage(target_objective_id, specific_next_stage_id)
                            if self.is_player: # Player memories are simple strings
                                self.memory_about_player.append(f"Completing '{obj_desc}' has opened up new paths regarding '{target_obj_desc}'.")
                        
                        elif target_objective.get("active", False) and not target_objective.get("completed", False):
                            if specific_next_stage_id:
                                print(f"[DEBUG] Linking: Advancing active objective '{target_obj_desc}' to specific stage '{specific_next_stage_id}' due to '{obj_desc}'.")
                                if self.advance_objective_stage(target_objective_id, specific_next_stage_id):
                                     if self.is_player: # Player memories are simple strings
                                        self.memory_about_player.append(f"Progress on '{obj_desc}' has further developed your understanding of '{target_obj_desc}'.")
                                else: print(f"[DEBUG] Linking: Failed to advance '{target_obj_desc}' to stage '{specific_next_stage_id}'.")
                            else:
                                current_target_stage = self.get_current_stage_for_objective(target_objective_id)
                                if current_target_stage and current_target_stage.get("next_stages"):
                                    potential_next_ids = current_target_stage["next_stages"]
                                    if isinstance(potential_next_ids, dict) and potential_next_ids:
                                        auto_next_stage_id = next(iter(potential_next_ids.values()))
                                        print(f"[DEBUG] Linking: Attempting generic advance for active objective '{target_obj_desc}' to its next stage '{auto_next_stage_id}' due to '{obj_desc}'.")
                                        if self.advance_objective_stage(target_objective_id, auto_next_stage_id):
                                            if self.is_player: # Player memories are simple strings
                                                self.memory_about_player.append(f"Progress on '{obj_desc}' has influenced your approach to '{target_obj_desc}'.")
                                    elif isinstance(potential_next_ids, list) and potential_next_ids:
                                         auto_next_stage_id = potential_next_ids[0]
                                         print(f"[DEBUG] Linking: Attempting generic advance for active objective '{target_obj_desc}' to its next stage '{auto_next_stage_id}' due to '{obj_desc}'.")
                                         if self.advance_objective_stage(target_objective_id, auto_next_stage_id):
                                            if self.is_player: # Player memories are simple strings
                                                self.memory_about_player.append(f"Progress on '{obj_desc}' has influenced your approach to '{target_obj_desc}'.")
                                    else:
                                        print(f"[DEBUG] Linking: Objective '{target_obj_desc}' is active, but current stage has no defined 'next_stages' for generic advance.")
                                else:
                                    print(f"[DEBUG] Linking: Objective '{target_obj_desc}' is active, but current stage or its 'next_stages' are not clearly defined for generic advance.")
            return True
        return False

    def activate_objective(self, objective_id, set_stage_id=None):
        obj = self.get_objective_by_id(objective_id)
        if obj:
            obj["active"] = True
            obj["completed"] = False  

            initial_stage_id_to_set = None
            if set_stage_id: 
                if any(s.get("stage_id") == set_stage_id for s in obj.get("stages", [])):
                    initial_stage_id_to_set = set_stage_id
                else:
                    print(f"[DEBUG] Warning: Requested stage_id '{set_stage_id}' for activating objective '{objective_id}' not found. Defaulting to first stage.")

            if not initial_stage_id_to_set: 
                if obj.get("stages") and obj["stages"][0].get("stage_id"):
                    initial_stage_id_to_set = obj["stages"][0].get("stage_id")
                else: 
                    obj["stages"] = [{"stage_id": "default", "description": "Objective activated.", "is_current_stage": True}]
                    initial_stage_id_to_set = "default"
            
            obj["current_stage_id"] = initial_stage_id_to_set
            for stage in obj.get("stages", []):
                stage["is_current_stage"] = (stage.get("stage_id") == initial_stage_id_to_set)
            
            current_stage_desc = self.get_current_stage_for_objective(objective_id).get('description', 'initial stage')
            if self.is_player: # Player memories are simple strings
                self.memory_about_player.append(f"New objective active or re-activated: '{obj.get('description', 'Unnamed Objective')}' (Current stage: '{current_stage_desc}').")
            print(f"[DEBUG] Player {self.name} activated objective: {obj.get('description')} - now at stage '{current_stage_desc}'")
            return True
        return False

    def check_skill(self, skill_name: str, difficulty_threshold: int = 1) -> bool:
        """
        Checks if the character succeeds at a skill check.
        Rolls a d6, adds skill value, compares to (difficulty_threshold + 3).
        """
        skill_value = self.skills.get(skill_name, 0)
        d6_roll = random.randint(1, 6)
        
        # Formula from prompt: (skill + roll) >= (threshold + 3)
        target_number = difficulty_threshold + 3
        success = (skill_value + d6_roll) >= target_number
        
        # Debug message as specified in prompt
        print(f"[Skill Check] {self.name} attempting {skill_name} (Value: {skill_value}, Roll: {d6_roll}, Threshold: {difficulty_threshold}): {'Success' if success else 'Failure'}")
        return success