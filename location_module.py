# location_module.py

# LOCATIONS_DATA remains largely the same but is now in this file.
LOCATIONS_DATA = {
    "Tavern": {
        "description": "The air in this St. Petersburg tavern is thick with the acrid smell of cheap makhorka tobacco, stale beer, and unwashed bodies. Grimy wooden tables are scarred with countless rings from wet glasses. Low, guttural laughter and hushed, desperate whispers mingle, creating a cacophony of the city's underbelly. Shadows cling to the corners, and the flickering gaslight casts a jaundiced glow on the faces of the patrons, each seemingly lost in their own private miseries or fleeting revelries.",
        "exits": {"Haymarket Square": "Push through the heavy, creaking door back into the sensory assault of Haymarket Square."},
        "npc_names_present": ["Dmitri Razumikhin", "Arkady Svidrigailov"],
        "time_effects": {
            "Night": " The tavern is rowdier now, filled with more drunken shouts and the desperate gaiety of those trying to forget the coming dawn."
        }
    },
    "Raskolnikov's Garret": {
        "description": "This 'coffin' of a room, tucked away under the very eaves of a towering, five-storied house, is suffocating. The ceiling presses down, so low you feel you could touch it without standing. Yellowed, peeling wallpaper, adorned with a barely discernible floral pattern, seems to absorb what little light filters through the grimy window. The air is perpetually stuffy, heavy with the scent of dust, poverty, and unspoken thoughts. A rickety table, a chair, and a wretched sofa covered in tattered chintz are the sole furnishings.",
        "exits": {"Stairwell (Outside Raskolnikov's Garret)": "Open the flimsy door and step out into the dim, echoing stairwell."},
        "npc_names_present": [],
        "time_effects": {
            "Night": " The room is even more oppressive in the darkness, shadows deepening the sense of confinement. The city's distant noises seem louder here."
        }
    },
    "Stairwell (Outside Raskolnikov's Garret)": {
        "description": "The stairwell is a dark, narrow passage, spiraling down into the building's depths. The air is cool and damp, carrying a mélange of odors: stale cooking smells from other apartments, the faint scent of lye from a recent, perfunctory cleaning, and an underlying mustiness. Each creak of the wooden steps underfoot echoes ominously. Faint sounds of life – a distant argument, a child's cry, a snatch of a song – drift from behind closed doors.",
        "exits": {
            "Raskolnikov's Garret": "Climb the last few steps back to the garret door.",
            "Haymarket Square": "Descend the seemingly endless flights of stairs, emerging into the clamor of Haymarket Square."
        },
        "npc_names_present": []
    },
    "Sonya's Room": {
        "description": "Sonya Marmeladova's room at the Kapernaumovs' is surprisingly large, though the ceiling is oppressively low. It is irregularly shaped, with a sharp angle cutting into one wall, making it feel like a barn. Furnishings are meager: a plain wooden bed with a thin blanket, a simple table, a few mismatched chairs, and a small, battered chest of drawers. A worn copy of the New Testament lies on the table. Despite its bareness, there's a sense of desperate tidiness, a quiet battle against encroaching squalor. The room is filled with a palpable atmosphere of sorrow, faith, and profound suffering.",
        "exits": {"Haymarket Square": "Leave the quiet sorrow of the room and return to the jarring noise of Haymarket Square."},
        "npc_names_present": ["Sonya Marmeladova"],
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
        "npc_names_present": []
    },
    "Porfiry's Office": {
        "description": "Porfiry Petrovich's office is somewhat more orderly than the general area, though still utilitarian. A large, cluttered desk dominates the room, piled with case files and legal documents. Bookshelves laden with dusty tomes line one wall. The room is typically hazy with tobacco smoke, as Porfiry is a frequent smoker. A couple of worn armchairs for visitors are placed before the desk, inviting an interrogation that feels more like a casual, albeit unsettling, conversation.",
        "exits": {"Police Station (General Area)": "Step out of the intense scrutiny of the office and back into the general area of the police station."},
        "npc_names_present": ["Porfiry Petrovich"]
    },
    "Haymarket Square": {
        "description": "Haymarket Square is a sensory explosion, the beating, often diseased heart of this part of St. Petersburg. The air is a thick soup of smells: rotting vegetables, fresh hay, horse manure, cheap vodka, unwashed bodies, and the aroma of street food from countless stalls. A cacophony of sounds assaults the ears – the shouts of vendors hawking their wares, the rumbling of cartwheels on cobblestones, the whinnying of horses, the cries of beggars, and the drunken singing from nearby taverns. The crowd is a dense, ever-shifting mass of humanity, a cross-section of the city's poor and desperate.",
        "exits": {
            "Tavern": "Duck into a nearby tavern, seeking either oblivion or company.",
            "Stairwell (Outside Raskolnikov's Garret)": "Weave through the throng towards the tall tenement building where Raskolnikov lodges.",
            "Sonya's Room": "Navigate the crowded streets towards the Kapernaumovs' building, where Sonya lives.",
            "Police Station (General Area)": "Make your way towards the imposing, grey facade of the local police station.",
            "Voznesensky Bridge": "Head towards the wide expanse of the Voznesensky Bridge, seeking a moment's respite.",
            "Pulcheria's Lodgings": "Find the quieter side street leading to the modest rooms where Raskolnikov's mother and sister are staying.",
            "Pawnbroker's Apartment Building": "Turn down a familiar, grim street towards the building where Alyona Ivanovna, the old pawnbroker, met her end."
        },
        "npc_names_present": ["Dunya Raskolnikova", "Dmitri Razumikhin"],
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
        "npc_names_present": []
    },
    "Pawnbroker's Apartment": {
        "description": "The air inside Alyona Ivanovna's small apartment is stale and heavy with an almost tangible silence. Dust motes dance in the weak shafts of light that penetrate the grimy windows. The sparse furniture – a few chairs, a chest, a bed – is draped in ghostly stillness. Every object seems to hold a memory, a silent testament to the violent events that transpired here. The place feels cold, violated, and haunted by an unspeakable dread.",
        "exits": {"Pawnbroker's Apartment Building": "Turn your back on the scene and leave the apartment, returning to the stairwell."},
        "npc_names_present": []
    },
    "Voznesensky Bridge": {
        "description": "Standing on the Voznesensky Bridge, you feel the city's pulse around you, yet also a strange sense of detachment. The wide expanse of the murky canal flows beneath, its dark waters reflecting the grey St. Petersburg sky. Horse-drawn carts rattle across the cobblestones, and pedestrians hurry past, wrapped in their own concerns. It's a place of transit, but also one for contemplation, where the vastness of the city and the weight of one's thoughts can feel overwhelming.",
        "exits": {"Haymarket Square": "Leave the bridge's exposed expanse and walk back towards the chaotic embrace of Haymarket Square."},
        "npc_names_present": [],
         "time_effects": {
            "Evening": " Gas lamps along the bridge cast long, wavering reflections on the dark water below."
        }
    },
    "Pulcheria's Lodgings": {
        "description": "The rented rooms where Pulcheria Alexandrovna and Dunya are staying are modest but kept meticulously clean, a stark contrast to Raskolnikov's garret. There's a smell of lavender and old linen. Simple furniture is arranged neatly, and a samovar might be hissing quietly in a corner. Despite the attempt at creating a homely atmosphere, an undercurrent of anxiety and hopeful, almost painful expectation for Rodya pervades the rooms.",
        "exits": {"Haymarket Square": "Take your leave from the lodgings and head back towards the bustling activity of Haymarket Square."},
        "npc_names_present": ["Pulcheria Alexandrovna Raskolnikova", "Dunya Raskolnikova"]
    }
}
