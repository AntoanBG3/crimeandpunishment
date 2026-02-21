<p align="center">
  <strong>Crime and Punishment</strong><br>
  <em>A Generative Text Adventure</em>
</p>

<p align="center">
  <a href="https://github.com/AntoanBG3/crimeandpunishment/releases"><img src="https://img.shields.io/github/v/release/AntoanBG3/crimeandpunishment?style=for-the-badge&color=darkred" alt="Latest Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-black?style=for-the-badge" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/powered%20by-Gemini%20API-orange?style=for-the-badge" alt="Gemini API">
</p>

---

> *"To go wrong in one's own way is better than to go right in someone else's."*  
> — Fyodor Dostoevsky

Step into 19th-century St. Petersburg and inhabit the minds of Dostoevsky's most iconic characters. **Crime and Punishment** is a terminal-based text adventure dynamically powered by the **Google Gemini API**. Every conversation, observation, and moral crossroad is generated and shaped in real-time, creating a world that genuinely *reacts* to your choices.

---

## Features

- **Three Playable Protagonists** – Play as **Raskolnikov**, **Sonya**, or **Porfiry**. Each character has unique objectives, inventories, skills, and distinct psychological profiles.
- **AI-Driven NPCs** – The inhabitants of St. Petersburg remember past interactions, hold grudges, pursue their own goals, and dynamically adjust their tone based on your relationship and psychological state.
- **A Living City** – The world operates continuously. NPCs follow daily schedules, move between locations independently, and interact with each other in emergent ways.
- **Branching Objectives** – Experience multi-stage quest lines mirroring the novel. Help Raskolnikov *Grapple with Crime*, guide him as Sonya, or pursue the truth as Porfiry.
- **RPG Mechanics & Skill Checks** – Utilize a D6 + Modifier system. Skills like *Persuasion*, *Observation*, and others actively determine the outcomes of key interactions.
- **Atmospheric Generation** – The game’s text adapts dynamically based on the time of day, your exact location, and your character’s current mental state, creating unparalleled ambiance.
- **Robust Save System** – Multiple named save slots and autosave securely preserve your progress.

---

## Quick Start

### Option A — Download a Release (Recommended)

1. Go to the [**Releases**](https://github.com/AntoanBG3/crimeandpunishment/releases) page.
2. Download the executable for your OS.
3. Run the application:
   - **Windows:** Double-click the `.exe` file.
   - **Linux / macOS:** `chmod +x <file> && ./<file>`

### Option B — Run from Source

```bash
# Clone the repository
git clone https://github.com/AntoanBG3/crimeandpunishment.git
cd crimeandpunishment

# Create a virtual environment & install dependencies
python -m venv .venv
# On Windows
.\venv\Scripts\activate      
# On Linux / macOS
# source .venv/bin/activate  

pip install -r requirements.txt

# Launch the game
python main.py
```

### First-Run API Setup

On your first launch, the game will prompt you for a **Google Gemini API key**. You can confidently provide it in-game, set the `GEMINI_API_KEY` environment variable, or place a `gemini_config.json` file in the project's root directory. Get your key here: [ai.google.dev](https://ai.google.dev/gemini-api/docs/api-key).

> **No key? No problem.** The game seamlessly ships with a robust set of static fallback text for every AI-generated element. You can still fully explore St. Petersburg in a deterministic, reduced-AI mode.

---

## Commands at a Glance

The game features an intelligent **Natural Language Parser (NLP)** that translates your free-form sentences into game actions (e.g., *"Pick up the axe and go to the tavern"*).

Below are the core, deterministic commands:

| Action | Command | Alias / Variations | Description |
|---|---|---|---|
| **Observe** | `look [target]` | `l` | Examine your surroundings, a character, or an item. |
| **Travel** | `move to <place>` | `go to` | Move to a connected, adjacent location. |
| **Chat** | `talk to <name>` | `speak to`, `ask` | Initiate a conversation with an NPC. |
| **Persuade** | `persuade <name>` | | Attempt a skill check to influence an NPC. |
| **Take** | `take <item>` | `pick up`, `grab` | Add an ambient item to your inventory. |
| **Drop** | `drop <item>` | | Leave a carried item at your current location. |
| **Inventory** | `inventory` | `i` | View the items you are currently carrying. |
| **Give** | `give <item> to <name>` | | Hand an item directly to an NPC. |
| **Use** | `use <item>` | | Use or read an item from your inventory. |
| **Status** | `status` | `stats` | Check psychological states, skills, and relationships. |
| **Goals** | `objectives` | `quests` | Review your current missions and storyline progress. |
| **Ponder** | `think` | `reflect` | Generate an internal monologue reflecting your mental state. |
| **Diary** | `journal` | | Review your securely gathered personal journal entries. |
| **Pass Time** | `wait` | | Allow time to pass and the world to organically advance. |
| **Progress**| `save [slot]` / `load` | | Manually manage your specific game saves. |
| **Style** | `theme <name>` | | Switch color themes between `default`, `muted`, or `none`. |
| **Density** | `verbosity <level>`| `density` | Adjust the amount and detail of generated text. |
| **Help** | `help [category]` | | Show commands. Filter by `movement`, `social`, `items`, or `meta`. |
| **Exit** | `quit` | `exit` | Leave the game and return to your terminal. |

---

## Project Architecture

```
CrimeAndPunishment/
├── main.py                      # Application Entry Point
├── game_engine/
│   ├── game_state.py            # Core engine loop, command processing, temporal mechanics
│   ├── character_module.py      # Entity mechanics (inventory, skills, objectives, AI memory)
│   ├── event_manager.py         # Systems for scripted scenarios & emergent events
│   ├── gemini_interactions.py   # Secure Google Gemini API wrapper & intent parsing
│   ├── game_config.py           # Aesthetic configuration, constants, fallback systems
│   └── location_module.py       # Spatial data loader and graph traversal
├── data/
│   ├── characters.json          # Protagonist specifications & NPC definitions
│   ├── items.json               # Item catalogues outlining properties & mechanical effects
│   └── locations.json           # Graphical map of St. Petersburg connections
├── tests/                       # Automated Pytest suite for deterministic verification
├── docs/                        # Foundational design documents & architecture schemas
├── requirements.txt             # Virtual environment dependencies
└── LICENSE                      # Open-source MIT License
```

---

## Running Tests
To ensure the engine logic and deterministic behaviors remain fully functional during development:

```bash
pip install pytest coverage
python -m unittest discover tests
```

---

## Contributing
Contributions, bug reports, and features are welcome! Feel free to open an issue or proactively submit a pull request. Make sure tests continue to pass!

---

## License
This project is open-sourced under the **MIT License**. See the [LICENSE](LICENSE) file for comprehensive details.