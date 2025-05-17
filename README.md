Crime and Punishment: A Text Adventure
"To go wrong in one's own way is better than to go right in someone else's." - Fyodor Dostoevsky

Welcome to a text-based adventure game that immerses you in the dark and psychologically complex world of Fyodor Dostoevsky's masterpiece, "Crime and Punishment." Navigate the grimy streets of 19th-century St. Petersburg, interact with iconic characters, and grapple with profound moral and philosophical dilemmas. This game leverages the power of Google's Gemini API to create dynamic dialogues, rich atmospheric details, and a deeply personal narrative experience.
Core Concept

Step into the shoes of characters like Rodion Raskolnikov, Sonya Marmeladova, or Porfiry Petrovich. Experience their struggles, motivations, and the oppressive atmosphere of Dostoevsky's world. Your choices in dialogue and action will shape your relationships, your understanding of your character's psyche, and the unfolding narrative, which aims to explore themes of guilt, redemption, alienation, and the nature of morality.
Key Features

    Deep Narrative Immersion: Experience a story closely tied to the events and themes of "Crime and Punishment."

    Dynamic NPC Interactions: Engage in conversations powered by Google's Gemini API. NPCs react to your character's state, what they are carrying, and the history of your interactions, providing unique and in-character responses.

    Playable Characters: Choose to play as different key characters from the novel, each with their own perspectives, objectives, and challenges.

    Atmospheric Storytelling: Gemini generates subtle atmospheric details, enhancing the mood and reflecting the psychological state of your character.

    Branching Objectives: Pursue character-specific objectives with multiple stages and potential outcomes based on your choices, mirroring the novel's complex plotlines.

    Item System: Find, take, drop, and use items that can influence interactions and objectives.

    NPC Schedules & Movement: NPCs have their own routines and can move between locations, making the world feel more alive.

    Save/Load System: Save your progress and return to your journey through St. Petersburg at any time.

    Enhanced Terminal UI: Utilizes the blessed library for a more structured and readable text-based interface.

Technologies Used

    Python 3: The core programming language.

    Google Gemini API: Powers NPC dialogue, atmospheric descriptions, player reflections, and other generative text elements.

    Blessed: A Python library for creating more sophisticated terminal interfaces.

Setup and Installation

    Clone the Repository:

    git clone https://github.com/AntoanBG3/crimeandpunishment.git
    cd <repository-name>

    Create a Virtual Environment (Recommended):

    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    Install Dependencies:

    pip install -r requirements.txt

    (The requirements.txt file includes all necessary Python packages like google-generativeai and blessed.)

    Set Up Your Gemini API Key:
    This game requires a Google Gemini API key to function fully. The game will look for the API key in the following order:

        Environment Variable (Most Secure): Set an environment variable named GEMINI_API_KEY to your actual API key. This is the recommended method.

        Configuration File (Less Secure): As a fallback, the game will check for a gemini_config.json file in the root directory with the content:

        {"gemini_api_key": "YOUR_ACTUAL_API_KEY_HERE"}

        Important: If you use this file, ensure it is listed in your .gitignore file to prevent accidental exposure of your API key.

        Manual Input: If no key is found via the methods above, the game will prompt you to enter it when it starts.

    Please refer to Google's official documentation for instructions on acquiring a Gemini API key.

How to Play

    Run the game from your terminal:

    python main.py

    At the start, you can choose to load a saved game or press Enter to start a new one.

    If starting a new game, select your character.

    Interact with the world using text commands. Type help at any time to see a list of available actions. Common commands include:

        look or l: Examine your surroundings.

        look at [thing/person]: Get more details.

        talk to [character name]: Initiate a conversation.

        move to [location name/exit description]: Change locations.

        inventory or i: Check your items.

        take [item name]: Pick up an item.

        drop [item name]: Leave an item.

        use [item name] or use [item name] on [target]: Use an item.

        objectives: View your current goals.

        think: See your character's inner thoughts.

        journal or notes: Review your character's journal entries (e.g., overheard rumors, read news).

        save / load: Manage game progress.

        quit: Exit the game.

Future Enhancements

    Deeper implementation of branching narratives and consequences for all objectives.

    More complex item interactions and environmental puzzles.

    Expanded NPC knowledge bases and reactions.

    Further refinements to the terminal UI for an even more immersive experience.

Contributing

Contributions are welcome! If you have ideas for improvements, bug fixes, or new features, please feel free to:

    Fork the repository.

    Create a new branch (git checkout -b feature/YourAmazingFeature).

    Make your changes.

    Commit your changes (git commit -m 'Add some YourAmazingFeature').

    Push to the branch (git push origin feature/YourAmazingFeature).

    Open a Pull Request.

Please ensure your code adheres to the project's style and that any new features align with the game's thematic and narrative goals.
License

This project is currently unlicensed.

"Svidrigailov was a man who had somehow run out of meaning, and when you run out of meaning, you have to find something to feel."