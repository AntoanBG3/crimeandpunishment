# Crime and Punishment: A Text Adventure

> *"To go wrong in one's own way is better than to go right in someone else's." - Fyodor Dostoevsky*

Step into the tormented mind of Rodion Raskolnikov, the saintly Sonya Marmeladova, or the cunning Porfiry Petrovich in this immersive text-based adventure. Navigate the grim, atmospheric streets of 19th-century St. Petersburg, grapple with profound moral dilemmas, and witness the raw human condition as depicted in Dostoevsky's masterpiece. Powered by Google's Gemini API, every conversation and observation brings the world of "Crime and Punishment" to life with unprecedented dynamism.

## Why Delve into Dostoevsky's St. Petersburg?

* **Live the Novel:** Experience a narrative deeply intertwined with the pivotal events, characters, and philosophical struggles of "Crime and Punishment".
* **Dynamic, Intelligent NPCs:** Engage in conversations that matter. Characters remember your past interactions, their personas shape their responses, and their objectives drive their actions, all powered by the Gemini API.
* **Multiple Perspectives:** Play as iconic characters like Raskolnikov, grappling with his theory and the murder; Sonya, striving for her family's survival and Raskolnikov's soul; or Porfiry Petrovich, employing psychological tactics to uncover the truth.
* **Atmosphere You Can Read:** Feel the oppressive weight of St. Petersburg through subtle, AI-generated atmospheric details that reflect your character's internal state and the grim reality around them.
* **Meaningful Choices:** Your actions and dialogue influence your relationships, character objectives with multiple stages, and the unfolding narrative, leading to different outcomes.
* **Living World:** NPCs follow their own schedules, events unfold dynamically, and the city reacts to your notoriety.

## Features

* **Rich Narrative Core:** Follow branching objectives mirroring the novel's complexity, such as Raskolnikov's "Grapple with Crime" or Sonya's "Guide Raskolnikov".
* **Interactive Item System:** Find, use, and give items like "Raskolnikov's axe," "Sonya's New Testament," or AI-generated "Anonymous Notes" that can drive the plot or reveal character insights.
* **Dynamic Events:** Encounter scripted and emergent events, from Marmeladov's tragic tavern confessions to Katerina Ivanovna's public laments, or even find mysterious notes reacting to your deeds.
* **Psychological Depth:** Explore your character's inner world through AI-generated reflections, dreams, and observations.
* **Persistent World:** Save and load your progress at any time.
* **Enhanced Terminal UI:** A more readable and structured interface using the `blessed` library.

## Technologies Used

* **Python 3:** Core programming language.
* **Google Gemini API:** For dynamic NPC dialogue, atmospheric descriptions, player reflections, and other generative text.
* **Blessed:** Python library for an improved terminal interface.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/AntoanBG3/crimeandpunishment.git
    cd crimeandpunishment
    ```
2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    This will install `google-generativeai` and `blessed`.
4.  **Set Up Your Gemini API Key:**
    The game requires a Google Gemini API key. It will search in this order:
    * **Environment Variable (Most Secure):** Set `GEMINI_API_KEY` to your API key.
    * **Configuration File (`gemini_config.json`):** In the root directory, create `gemini_config.json`. The game can store both your API key and preferred model in this file. If you create it manually, it can look like this:
        ```json
        {
            "gemini_api_key": "YOUR_ACTUAL_API_KEY_HERE",
            "chosen_model_name": "gemini-2.0-flash" // Or your preferred model
        }
        ```
    * **Manual Input:** If no key is found, the game will prompt you at startup.

    *Obtain your Gemini API key from Google's official documentation.*

## How to Play

1.  **Run the game from your terminal:**
    ```bash
    python main.py
    ```
   
2.  **Start or Load:** Choose to `load` a saved game or press Enter for a new game. If new, select your character.
3.  **Interact with the World:**
    Use text commands to explore and interact. Type `help` for a full list of actions. Key commands include:

    * `look` / `l` / `examine [target]`: Observe your surroundings or focus on specifics.
    * `talk to [character name]`: Engage in conversation.
    * `move to [location/exit description]`: Navigate St. Petersburg.
    * `inventory` / `i`: Check your items.
    * `take [item]` / `drop [item]`: Manage your possessions.
    * `use [item]` / `use [item] on [target]`: Interact with items.
    * `read [item]`: Peruse readable items like letters or newspapers.
    * `persuade [character] that/to [argument]`: Attempt to influence NPCs.
    * `objectives` / `obj`: Review your current goals.
    * `think` / `reflect`: Access your character's inner thoughts.
    * `journal` / `notes`: Read your collected notes, news, and rumors.
    * `save` / `load`: Manage your game progress.
    * `quit` / `exit`: Leave the game.

    *(Command synonyms are supported for flexibility, see `game_config.py`)*