<p align="center">
  <strong>Crime and Punishment</strong><br>
  <em>A Generative Text Adventure</em>
</p>

<p align="center">
  <a href="https://github.com/AntoanBG3/crimeandpunishment/releases"><img src="https://img.shields.io/github/v/release/AntoanBG3/crimeandpunishment?style=for-the-badge&color=darkred" alt="Latest Release"></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-GPLv3%2B-black?style=for-the-badge" alt="GPL version 3 or later"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/powered%20by-Gemini%20API-orange?style=for-the-badge" alt="Gemini API">
</p>

---

> *"To go wrong in one's own way is better than to go right in someone else's."*  
> — Fyodor Dostoevsky

Step into 19th-century St. Petersburg as one of three protagonists from Dostoevsky's novel. **Crime and Punishment** combines authored objectives and game rules with optional **Google Gemini API** dialogue and narration. Static text keeps the adventure playable offline.

---

## Features

- **Three Playable Protagonists** – Play as **Raskolnikov**, **Sonya**, or **Porfiry**. Each character has unique objectives, inventories, skills, and distinct psychological profiles.
- **AI-Driven NPCs** – The inhabitants of St. Petersburg remember past interactions, hold grudges, pursue their own goals, and dynamically adjust their tone based on your relationship and psychological state.
- **A Living City** – Actions advance world time. NPCs follow daily schedules, move between locations, and participate in world events as turns pass.
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

With the Gemini SDK installed, an interactive launch prompts for an API key if no usable key is configured. Enter `skip` to play offline, or supply a key through the prompt or `GEMINI_API_KEY`. The game also reads `gemini_config.json` from the directory where you launch it and offers to save a verified key there. Keep that file private. Get a key at [ai.google.dev](https://ai.google.dev/gemini-api/docs/api-key).

> **Offline play:** Without the SDK or a usable key, the game uses static fallback text. Random skill checks and world events still occur. Piped input skips the key prompt, but a configured key can still enable API calls; use the isolated audit harness for guaranteed offline verification.

---

## Commands at a Glance

With AI configured, the **Natural Language Parser (NLP)** can translate a free-form sentence into one supported action, such as *"I would like to examine the desk"*. Enter one action at a time. The explicit commands below also work offline.

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
│   ├── session_state.py             # Gameplay state with compatibility accessors
│   ├── persistence.py               # Validate a detached candidate before restoring saves
│   ├── command_result.py            # Named, tuple-compatible command outcomes
│   ├── diagnostics.py               # Content-free crash reports
│   ├── terminal.py                  # Single I/O seam: Rich rendering, wrapping, prompt_toolkit input
│   ├── tui_app.py                   # Textual TUI backend (default in a TTY; --no-tui opts out)
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
├── docs/                            # Audit evidence, remediation backlog, dependencies
├── scripts/                         # Isolated audit scenarios, builds, commit reminder
├── requirements.txt                 # google-genai, rich, prompt_toolkit, textual
└── LICENSE.md                       # GPL version 3 or later notice
```

---

## Running Tests
To ensure the engine logic and deterministic behaviors remain fully functional during development:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m unittest discover tests          # offline suite, including real SDK mocks
coverage run --branch --source=game_engine,main -m unittest discover tests
coverage report
python scripts/audit_scenarios.py --scenario endings
```

See the [audit report](AUDIT_REPORT.md), [verification and remaining work](docs/REMEDIATION_PLAN.md), and [dependency/build instructions](docs/DEPENDENCIES.md). Routine CI checks Python 3.10 and 3.13 on Windows, Linux, and macOS independently of release publication.

---

## Contributing
Contributions, bug reports, and features are welcome! Feel free to open an issue or proactively submit a pull request. Make sure tests continue to pass!

---

## License
This project carries a **GNU GPL version 3 or later** notice. See [LICENSE.md](LICENSE.md).
