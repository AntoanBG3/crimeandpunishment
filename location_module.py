# location_module.py
from game_config import DEFAULT_ITEMS

LOCATIONS_DATA = {
    "Tavern": {
        "description": "The air in this St. Petersburg tavern is thick with the acrid smell of cheap makhorka tobacco, stale beer, the greasy steam of cheap food, and unwashed bodies. Grimy wooden tables are scarred with countless rings from wet glasses and spilled drink. A cacophony of the city's underbelly fills the space: low, guttural laughter from one corner, hushed, desperate whispers from another, sharp arguments flaring up and dying down, and the occasional burst of drunken song. Shadows cling to the corners, and the flickering gaslight casts a jaundiced glow on the faces of the varied patrons – students, minor officials, workmen, and more shadowy figures – each seemingly lost in their own private miseries, fleeting revelries, or intense, low-voiced conversations that might concern anything from petty gossip to life-altering decisions. It's a place where crucial information might be overheard by chance, or a fateful encounter could occur.",
        "exits": {"Haymarket Square": "Push through the heavy, creaking door back into the sensory assault of Haymarket Square."},
        "items_present": [{"name": "dusty bottle", "quantity": 2}, {"name": "worn coin", "quantity": 1}, {"name": "cheap vodka", "quantity": 1}],
        "time_effects": {
            "Night": " The tavern is rowdier now, filled with more drunken shouts and the desperate gaiety of those trying to forget the coming dawn."
        }
    },
    "Raskolnikov's Garret": {
        "description": "This tiny garret, more like a cupboard or a 'coffin' of a room, is tucked away oppressively under the very eaves of a towering, five-storied house. The ceiling presses down, so low you feel you could touch it without standing. Dusty, yellowed, and peeling wallpaper, adorned with a barely discernible floral pattern, seems to absorb what little light filters through the grimy window, contributing to the room's sense of psychological confinement. The air is perpetually stuffy, heavy with the scent of dust, abject poverty, and unspoken, feverish thoughts. A rickety table, a chair, and a wretched sofa covered in tattered chintz are the sole, miserable furnishings.",
        "exits": {"Stairwell (Outside Raskolnikov's Garret)": "Open the flimsy door and step out into the dim, echoing stairwell."},
        "items_present": [{"name": "old newspaper", "quantity": 1}],
        "time_effects": {
            "Night": " The room is even more oppressive in the darkness, shadows deepening the sense of confinement. The city's distant noises seem louder here."
        }
    },
    "Stairwell (Outside Raskolnikov's Garret)": {
        "description": "The stairwell is a dark, narrow passage, spiraling down into the building's depths. The air is cool and damp, carrying a mélange of odors: stale cooking smells from other apartments, the faint scent of lye from a recent, perfunctory cleaning, and an underlying mustiness. Each creak of the wooden steps underfoot echoes ominously. Faint sounds of life – a distant argument, a child's cry, a snatch of a song – drift from behind closed doors.",
        "exits": {
            "Raskolnikov's Garret": "Climb the last few steps back to the garret door.",
            "Haymarket Square": "Descend the seemingly endless flights of stairs, emerging into the clamor of Haymarket Square.",
            "Quiet Courtyard": "Descend to the ground floor and find a passage leading to a secluded courtyard."
        },
        "items_present": []
    },
    "Sonya's Room": {
        "description": "Sonya Marmeladova's room at the Kapernaumovs' is surprisingly large, though the ceiling is oppressively low, giving it a barn-like feeling. It's an irregularly shaped space, with a sharp angle cutting into one wall. Furnishings are meager: a plain wooden bed with a thin blanket, a simple table, a few mismatched chairs, and a small, battered chest of drawers. On the table, a well-worn copy of the New Testament is often visible, a testament to her deep faith. Despite its bareness and poverty, there's a sense of desperate tidiness, a quiet battle against encroaching squalor. The room is filled with a palpable atmosphere of sorrow, faith, and profound suffering.",
        "exits": {
            "Haymarket Square": "Leave the quiet sorrow of the room and return to the jarring noise of Haymarket Square.",
            "Katerina Ivanovna's Apartment": "A short, grim walk takes you to the even more chaotic dwelling of Katerina Ivanovna." # New Exit
            },
        "items_present": [],
         "time_effects": {
            "Evening": " A single candle often burns, casting long, flickering shadows that dance with Sonya's quiet movements."
        }
    },
    "Police Station (General Area)": {
        "description": "The general office of the police station is a scene of controlled chaos and bureaucratic indifference. Wooden benches line the walls, occupied by a motley collection of petitioners, informants, and the unfortunate. Harried clerks with ink-stained fingers scratch away with pens at high desks, occasionally barking orders or questions. The air smells of official paper, sealing wax, damp wool, and the faint, ever-present odor of despair. The constant shuffling of feet and the murmur of voices create a dull, oppressive hum.",
        "exits": {
            "Haymarket Square": "Escape the oppressive atmosphere of the station and find yourself back near Haymarket Square.",
            "Porfiry's Office": "Navigate through a corridor to the examining magistrate's office."
        },
        "items_present": [{"name": "old newspaper", "quantity": 3}]
    },
    "Porfiry's Office": {
        "description": "Porfiry Petrovich's office is somewhat more orderly than the general area, though still utilitarian. A large, cluttered desk dominates the room, piled with case files and legal documents. Bookshelves laden with dusty tomes line one wall. The room is typically hazy with tobacco smoke, as Porfiry is a frequent smoker. A couple of worn armchairs for visitors are placed before the desk, inviting an interrogation that feels more like a casual, albeit unsettling, conversation.",
        "exits": {"Police Station (General Area)": "Step out of the intense scrutiny of the office and back into the general area of the police station."},
        "items_present": []
    },
    "Haymarket Square": {
        "description": "Haymarket Square is an oppressive sensory explosion, the beating, often diseased heart of this part of St. Petersburg, especially under the stifling summer heat. The air is a thick, choking soup of smells: rotting vegetables, fresh hay, horse manure, cheap vodka, unwashed bodies, and the greasy aroma of street food from countless stalls, all mingling with fine, pervasive dust. A relentless cacophony of sounds assaults the ears – the shouts of vendors hawking their wares, the rumbling of cartwheels on cobblestones, the whinnying of horses, the cries of beggars, and the drunken, desperate singing from nearby taverns. The crowd is a dense, ever-shifting mass of humanity – a cross-section of the city's poor, drunk, and desperate – navigating the chaotic, filthy space, contributing to an atmosphere that feels both overwhelmingly vibrant and deeply unsettling.",
        "exits": {
            "Tavern": "Duck into a nearby tavern, seeking either oblivion or company.",
            "Stairwell (Outside Raskolnikov's Garret)": "Weave through the throng towards the tall tenement building where Raskolnikov lodges.",
            "Sonya's Room": "Navigate the crowded streets towards the Kapernaumovs' building, where Sonya lives.",
            "Police Station (General Area)": "Make your way towards the imposing, grey facade of the local police station.",
            "Voznesensky Bridge": "Head towards the wide expanse of the Voznesensky Bridge, seeking a moment's respite.",
            "Pulcheria's Lodgings": "Find the quieter side street leading to the modest rooms where Raskolnikov's mother and sister are staying.",
            "Pawnbroker's Apartment Building": "Turn down a familiar, grim street towards the building where Alyona Ivanovna, the old pawnbroker, met her end.",
            "Katerina Ivanovna's Apartment": "Follow a narrow, squalid alley towards the Marmeladovs' chaotic dwelling.", # New Exit
            "Quiet Courtyard": "Slip through a narrow archway into a surprisingly quiet courtyard."
        },
        "items_present": [{"name": "tattered handkerchief", "quantity": 1}, {"name": "worn coin", "quantity": 2}],
        "time_effects": {
            "Morning": " The market is at its busiest, with farmers and traders shouting their prices.",
            "Evening": " The crowds begin to thin, but a more desperate, shadowy element emerges."
        }
    },
    "Pawnbroker's Apartment Building": {
        "description": "The entrance to this tenement is dark and unwelcoming. The paint on the walls of the stairwell is peeling, revealing layers of grime underneath. A familiar, unsettling chill seems to emanate from the very stones of the building. Each step on the worn wooden stairs creaks, the sound echoing in the oppressive silence. You remember the layout of the floors, the specific door, with a vividness that is deeply disturbing.",
        "exits": {
            "Haymarket Square": "Retreat from the building's oppressive atmosphere, back to the relative anonymity of Haymarket Square.",
            "Pawnbroker's Apartment": "Your feet, heavy with memory, carry you up the stairs towards the door of the pawnbroker's former apartment."
        },
        "items_present": []
    },
    "Pawnbroker's Apartment": {
        "description": "Alyona Ivanovna's small apartment, though rather cluttered, is surprisingly clean, a testament to Lizaveta's diligent work. The walls are covered in cheap, yellow wallpaper. Simple muslin curtains hang over the windows, which look out onto the courtyard. Pots of geraniums line the windowsills, adding a touch of incongruous life to the otherwise severe room. The main room contains a sofa with a high wooden back, a round table, a chest of drawers, and a few chairs. The air is usually thick with the smell of whatever Alyona is cooking or the general scent of old belongings. Despite the cleanliness, there's an underlying sense of tension and suspicion, largely emanating from the old pawnbroker herself.",
        "exits": {"Pawnbroker's Apartment Building": "Turn your back on the scene and leave the apartment, returning to the stairwell."},
        "items_present": [{"name": "Lizaveta's bundle", "quantity": 1}] # Lizaveta's bundle might be found here.
    },
    "Voznesensky Bridge": {
        "description": "Standing on the Voznesensky Bridge, you feel the city's pulse around you, yet also a strange sense of detachment. The wide expanse of the murky canal flows beneath, its dark waters reflecting the grey St. Petersburg sky. Horse-drawn carts rattle across the cobblestones, and pedestrians hurry past, wrapped in their own concerns. It's a place of transit, but also one for contemplation, where the vastness of the city and the weight of one's thoughts can feel overwhelming.",
        "exits": {"Haymarket Square": "Leave the bridge's exposed expanse and walk back towards the chaotic embrace of Haymarket Square."},
        "items_present": [],
         "time_effects": {
            "Evening": " Gas lamps along the bridge cast long, wavering reflections on the dark water below."
        }
    },
    "Pulcheria's Lodgings": {
        "description": "The rented rooms where Pulcheria Alexandrovna and Dunya are staying are modest but kept meticulously clean, a stark contrast to Raskolnikov's garret. There's a smell of lavender and old linen. Simple furniture is arranged neatly, and a samovar might be hissing quietly in a corner. Despite the attempt at creating a homely atmosphere, an undercurrent of anxiety and hopeful, almost painful expectation for Rodya pervades the rooms.",
        "exits": {"Haymarket Square": "Take your leave from the lodgings and head back towards the bustling activity of Haymarket Square."},
        "items_present": []
    },
    "Katerina Ivanovna's Apartment": {
        "description": "A cramped, squalid room, overflowing with the detritus of poverty and shattered pride. Three young children – Polenka, Kolya, and Lida – often huddle in a corner, their eyes wide with fear or hunger. Katerina Ivanovna herself, flushed with fever and consumption, dominates the space with her shrill voice, lamentations, and fits of coughing. The air is stale, thick with the smell of illness, unwashed linen, and cheap tobacco (from Semyon's past presence). It's a scene of utter destitution and unbearable tension.",
        "exits": {
            "Haymarket Square": "Escape the suffocating misery and noise, returning to the relative chaos of Haymarket Square.",
            "Sonya's Room": "A short walk takes you to Sonya's slightly less chaotic, but equally sorrowful, room." # New Exit
            },
        "items_present": [{"name": "tattered handkerchief", "quantity": 2}], # Katerina always needs them
        "time_effects": {
            "Afternoon": " The children might be playing listlessly or crying, while Katerina Ivanovna is often in a state of high agitation.",
            "Evening": " Katerina might be trying to put the children to bed, her voice softer but filled with despair, or she could be loudly berating Sonya if she's present."
        }
    },
    "Quiet Courtyard": {
        "description": "Tucked away behind a crumbling archway, this small, forgotten courtyard offers a rare pocket of stillness amidst the city's cacophony. Moss clings to the damp cobblestones, and a few tenacious weeds sprout near the base of the surrounding tenement walls. The air is cool and smells of damp earth and distant chimney smoke. It feels like a place where secrets might be shared or a moment of troubled peace found.",
        "exits": {
            "Haymarket Square": "Pass back through the archway into the noise of Haymarket Square.",
            "Stairwell (Outside Raskolnikov's Garret)": "Find the passage back to the stairwell of Raskolnikov's tenement building."
        },
        "items_present": [{"name": "old newspaper", "quantity": 1}, {"name": "worn coin", "quantity": 1}],
        "time_effects": {
            "Afternoon": " Shadows from the tall tenements stretch long across the cobblestones, deepening the sense of seclusion.",
            "Night": " The courtyard is very dark, only faint light spills from distant windows, making it feel somewhat eerie."
        }
    },
    "Svidrigaïlov's Lodging": {
        "description": "Svidrigaïlov has taken rooms in a quiet, somewhat secluded part of the same building as Sonya's, though his are more spacious and less overtly squalid. The main feature of note is that his rooms adjoin Sonya's through a thin wall, and it is known he can, and does, listen to conversations in her room from an empty, connecting chamber he also rents. The air here often feels heavy with his cynical amusement and unspoken intentions. The furnishings are adequate but unremarkable, betraying little of the man's true nature beyond a desire for basic comfort and privacy.",
        "exits": {
            "Sonya's Room": "A door that presumably leads to a common hallway or area near Sonya's room.",
            "Haymarket Square": "Descend to the street and make your way back to the bustle of Haymarket Square."
            # Consider if an exit to a generic 'Apartment Hallway' might be better than directly to Sonya's,
            # depending on how eavesdropping is mechanically handled. For now, 'Sonya's Room' implies proximity.
        },
        "items_present": [], # No specific items noted for now, can be added later.
        "time_effects": {
            "Night": " The rooms are often quiet, but a faint light might be seen under his door, suggesting his late hours and restless thoughts."
        }
    }
}