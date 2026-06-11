<p align="center">
  <strong>Crime and Punishment</strong><br>
  <em>A Generative Text Adventure</em>
</p>

<p align="center">
  <a href="https://github.com/AntoanBG3/crimeandpunishment/releases"><img src="https://img.shields.io/github/v/release/AntoanBG3/crimeandpunishment?style=for-the-badge&color=darkred" alt="Latest Release"></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-black?style=for-the-badge" alt="MIT License"></a>
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
- **Robust Save System** – Multiple named save slots, autosave, and a numbered load picker preserve your progress.
- **Polished Terminal UX** – Tab completion for commands and targets, persistent command history, a live status toolbar, word-wrapped prose, and Rich panels for status, objectives, inventory, map, and journal. Honors `NO_COLOR` and degrades gracefully when piped.
- **Full-Screen TUI by Default** – Launching in a terminal opens the Textual interface: a scrollable narrative log, a persistent status bar, and a dedicated input field with Tab completion and persistent history. Prefer the classic console? `python main.py --no-tui` (or `CRIME_TUI=0`). Piped/scripted runs fall back to the console automatically.

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
.\.venv\Scripts\activate      
# On Linux / macOS
# source .venv/bin/activate  

pip install -r requirements.txt

# Launch the game (full-screen TUI by default)
python main.py

# Or the classic console
python main.py --no-tui
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
| **Observe** | `look [at target]` | `l`, `examine` | Examine your surroundings, a character, or an item. |
| **Travel** | `move to <place>` | `go to` | Move to a connected, adjacent location. |
| **Map** | `map` | `where am i` | Tree of known places and the ways between them. |
| **Actions** | `actions` | `options` | Numbered list of everything you can do right now. |
| **Chat** | `talk to <name>` | `speak to`, `ask` | Initiate a conversation with an NPC. |
| **Persuade** | `persuade <name> that <…>` | `convince` | Attempt a skill check to influence an NPC. |
| **Take** | `take <item>` | `get`, `pick up` | Add an item from the scene to your inventory. |
| **Drop** | `drop <item>` | `leave`, `discard` | Leave a carried item at your current location. |
| **Inventory** | `inventory` | `i`, `inv` | View the items you are currently carrying. |
| **Give** | `give <item> to <name>` | `offer` | Hand an item directly to an NPC. |
| **Use / Read** | `use <item>` / `read <item>` | `use <item> on <target>` | Use or read an item from your inventory. |
| **Status** | `status` | `char`, `profile`, `st` | Check psychological state, skills, and relationships. |
| **Goals** | `objectives` | `goals`, `obj` | Review your current missions and storyline progress. |
| **Ponder** | `think` | `reflect` | Generate an internal monologue reflecting your mental state. |
| **Diary** | `journal [filter]` | `notes` | Review journal entries; filter with `journal dreams`, `journal rumors`, … |
| **Pass Time** | `wait` | `pass time` | Allow time to pass and the world to organically advance. |
| **Progress** | `save [slot]` / `load [slot]` | `saves` lists slots | Manage saves; bare `load` offers a numbered picker. |
| **More** | `more` | | Reveal the rest of the last trimmed narrative text. |
| **Repeat** | `!!` | | Repeat your previous command. |
| **Style** | `theme <name>` | | Switch between `default`, `high-contrast`, and `mono`. |
| **Density** | `verbosity <level>` | `brief`, `standard`, `rich` | Adjust narrative text length (also steers the AI). |
| **Pacing** | `pace [on\|off]` | | Reveal dreams and major beats paragraph by paragraph. |
| **Screen** | `clearscreen [on\|off]` | | Clear the terminal when moving to a new place. |
| **Help** | `help [category]` | | Show commands. Filter by `movement`, `social`, `items`, or `meta`. |
| **Exit** | `quit` | `exit`, `q` | Leave the game and return to your terminal. |

Press **Tab** at the prompt to complete commands and targets; **↑/↓** browses your command history across sessions.

---

## Project Architecture

```
CrimeAndPunishment/
├── main.py                          # Application entry point
├── game_engine/
│   ├── game_state.py                # Game hub: main loop, save/load, think/wait
│   ├── terminal.py                  # Single I/O seam: Rich rendering, wrapping, prompt_toolkit input
│   ├── tui_app.py                   # Optional Textual TUI backend (--tui / CRIME_TUI=1)
│   ├── completion.py                # Tab completion fed by scene context
│   ├── display_mixin.py             # Output composition: panels, map, journal, tutorial, verbosity
│   ├── command_handler.py           # Parsing, target matching, the dispatch table
│   ├── item_interaction_handler.py  # take/drop/use/give/read and the scene listing
│   ├── npc_interaction_handler.py   # talk to / persuade / confess
│   ├── world_manager.py             # Time, schedules, movement, dreams, endings
│   ├── event_manager.py             # Scripted scenarios & emergent events
│   ├── objective_progression.py     # Data-driven objective stage advancement
│   ├── gemini_interactions.py       # Google Gemini API wrapper & intent parsing
│   ├── static_fallbacks.py          # Offline narrative fallbacks for every AI call
│   ├── character_module.py          # Entity mechanics (inventory, skills, objectives, memory)
│   ├── game_config.py               # Colors/themes, constants, COMMAND_SYNONYMS
│   └── location_module.py           # Spatial data loader
├── data/
│   ├── characters.json              # Protagonist specifications & NPC definitions
│   ├── items.json                   # Item catalogue: properties & mechanical effects
│   └── locations.json               # Map of St. Petersburg connections
├── tests/                           # unittest suite (no network, no TTY required)
├── docs/                            # UX roadmap and Tier 3 design docs
├── requirements.txt                 # google-genai, rich, prompt_toolkit, textual
└── LICENSE.md                       # MIT License
```

---

## Running Tests
To ensure the engine logic and deterministic behaviors remain fully functional during development:

```bash
python -m unittest discover tests          # full suite
coverage run -m unittest discover tests && coverage report
```

---

## Contributing
Contributions, bug reports, and features are welcome! Feel free to open an issue or proactively submit a pull request. Make sure tests continue to pass!

---

## License
This project is open-sourced under the **MIT License**. See the [LICENSE](LICENSE.md) file for comprehensive details.