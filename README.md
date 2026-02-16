<p align="center">
  <strong>🪓 Crime and Punishment</strong><br>
  <em>A Generative Text Adventure</em>
</p>

<p align="center">
  <a href="https://github.com/AntoanBG3/crimeandpunishment/releases"><img src="https://img.shields.io/github/v/release/AntoanBG3/crimeandpunishment?style=flat-square&label=latest%20release" alt="Latest Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-yellow?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/powered%20by-Gemini%20API-4285F4?style=flat-square" alt="Gemini API">
</p>

---

> *"To go wrong in one's own way is better than to go right in someone else's."*
> — Fyodor Dostoevsky

Step into 19th-century St. Petersburg and inhabit the minds of Dostoevsky's most iconic characters. Every conversation, every observation, every moral crossroad is shaped in real time by Google's Gemini API — creating a text adventure where the novel's world genuinely *reacts* to you.

---

## ✨ Highlights

| | Feature | What it means for gameplay |
|---|---|---|
| 🎭 | **Three playable protagonists** | Play as **Raskolnikov**, **Sonya**, or **Porfiry** — each with unique objectives, inventories, skills, and psychological profiles |
| 🧠 | **AI-driven NPCs** | Characters remember past conversations, pursue their own goals, and adjust tone based on relationship scores and psychology |
| 🗺️ | **Living city** | NPCs follow daily schedules, move between locations, and interact with each other — even when you're not around |
| 📖 | **Branching objectives** | Multi-stage quest lines that mirror the novel's arc: Raskolnikov's *Grapple with Crime*, Sonya's *Guide Raskolnikov*, Porfiry's pursuit of truth |
| 🎲 | **Skill checks** | d6 + skill value vs. difficulty — persuasion, observation, and more determine outcomes of key interactions |
| 📰 | **Dynamic events** | Marmeladov's tavern confession, Katerina's public lament, anonymous notes, street-life vignettes, NPC-to-NPC encounters |
| 🌫️ | **Atmospheric generation** | AI-crafted descriptions that shift with time of day, location, and your character's mental state |
| 💾 | **Named save slots** | Multiple named saves plus autosave keep your progress safe across sessions |

## 🕹️ Quick Start

### Option A — Download a release (recommended)

1. Go to the [**Releases**](https://github.com/AntoanBG3/crimeandpunishment/releases) page.
2. Download the executable for your OS.
3. Run it:
   - **Windows:** double-click the `.exe`
   - **Linux / macOS:** `chmod +x <file> && ./<file>`

### Option B — Run from source

```bash
# Clone the repository
git clone https://github.com/AntoanBG3/crimeandpunishment.git
cd crimeandpunishment

# Create a virtual environment & install dependencies
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux / macOS

pip install -r requirements.txt

# Launch the game
python main.py
```

### 🔑 First-run API setup

On first launch the game will prompt you for a **Google Gemini API key**. You can also set the `GEMINI_API_KEY` environment variable or place a `gemini_config.json` file in the project root. Get your key here: [ai.google.dev](https://ai.google.dev/gemini-api/docs/api-key).

> **No key? No problem.** The game ships with static fallback text for every AI-generated element, so you can explore St. Petersburg in a reduced-AI mode if you prefer.

## 📜 Commands at a Glance

| Command | Alias | Description |
|---|---|---|
| `look [target]` | `l` | Observe your surroundings, an NPC, item, or scenery |
| `talk to <name>` | `speak to`, `ask` | Start a conversation with a character |
| `move to <place>` | `go to` | Travel to a connected location |
| `take <item>` | `pick up`, `grab` | Pick up an item from the environment |
| `drop <item>` | | Leave an item at the current location |
| `use <item>` | | Use or read an item from your inventory |
| `give <item> to <name>` | | Hand an item to an NPC |
| `persuade <name>` | | Attempt a persuasion skill check on an NPC |
| `inventory` | `i` | List carried items |
| `status` | `stats` | Show character stats, psychology, and relationships |
| `objectives` | `goals`, `quests` | Review your current objectives |
| `think` | `reflect` | Trigger an AI-generated inner monologue |
| `journal` | `diary` | Review your journal entries |
| `wait` | | Pass time and let the world advance |
| `save [slot]` / `load [slot]` | | Save or load your game |
| `help [category]` | | Show commands — optionally filtered by `movement`, `social`, `items`, or `meta` |
| `theme <name>` | | Switch color theme (`default`, `muted`, `none`) |
| `verbosity <level>` | `density` | Adjust text density |
| `quit` | `exit` | Exit the game |

Natural-language input is also supported — the NLP parser will try to interpret free-form sentences into game actions.

## 🏗️ Project Structure

```
CrimeAndPunishment/
├── main.py                      # Entry point
├── game_engine/
│   ├── game_state.py            # Core game loop, commands, world state
│   ├── character_module.py      # Character class — inventory, skills, objectives, memory
│   ├── event_manager.py         # Scripted & emergent story events
│   ├── gemini_interactions.py   # Gemini API wrapper & NLP intent parser
│   ├── game_config.py           # Colors, constants, static fallbacks
│   └── location_module.py       # Location data loader
├── data/
│   ├── characters.json          # NPC & protagonist definitions
│   ├── items.json               # Item catalogue with properties & effects
│   └── locations.json           # Map of St. Petersburg locations & exits
├── tests/                       # Pytest test suite
├── docs/                        # Design documents
├── requirements.txt
└── LICENSE                      # MIT
```

## 🧪 Running Tests

```bash
pip install pytest
pytest tests/
```

## 🤝 Contributing

Contributions, bug reports, and ideas are welcome! Feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.