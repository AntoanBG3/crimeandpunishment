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

## Getting Started

1. **Download the Latest Release:**
   - Go to the [Releases page](https://github.com/AntoanBG3/crimeandpunishment/releases) for this repository.
   - Download the appropriate executable file for your operating system from the latest release.
2. **Run the Game:**
   - **Windows:** Double-click the downloaded `.exe` file.
   - **Linux/macOS:** Open your terminal, navigate to the directory where you downloaded the file, make it executable (`chmod +x <filename>`), and then run it (`./<filename>`).
3. **API Key Setup (First Run):**
   - The first time you run the game, it will guide you through setting up your Google Gemini API key if it's not already configured. Follow the on-screen prompts. You can obtain your Gemini API key from [Google's official documentation](https://ai.google.dev/gemini-api/docs/api-key).
4. **Basic Controls:**
   Once the game starts, type `help` to see a list of available commands. Common commands include:
   - `look` / `l`: Observe your surroundings.
   - `talk to [character name]`: Engage in conversation.
   - `move to [location]`: Go to a new place.
   - `inventory` / `i`: Check your items.
   - `quit`: Exit the game.

## Technologies Used

* **Python 3:** Core programming language.
* **Google Gemini API:** For dynamic NPC dialogue, atmospheric descriptions, player reflections, and other generative text.
* **Blessed:** Python library for an improved terminal interface.