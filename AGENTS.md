# AGENTS.md

Guidance for coding agents working in this repository.

## Scope

These instructions apply to the whole repository.

## Communication

Be concise, direct, and factual. Base conclusions on repository files, command output,
or user-provided context. Do not invent APIs, test results, issue numbers, or project
history.

Before changing code, inspect the relevant files and understand the current structure.
Prefer small, focused changes that preserve existing style and behavior.

## Project Overview

This is a Python terminal text adventure inspired by *Crime and Punishment*.
`main.py` instantiates `game_engine.game_state.Game` and calls `run()`.

Core code lives in `game_engine/`:

- `game_state.py` owns the main `Game` object, save/load state, player state, command
  processing entry points, and orchestration.
- `command_handler.py` parses deterministic commands, command history, fuzzy matches,
  and Gemini-backed natural-language intents.
- `world_manager.py` handles time, NPC scheduling, ambient rumors, dynamic location
  items, and character initialization.
- `character_module.py` defines `Character` and loads `data/characters.json`.
- `location_module.py` loads `data/locations.json`.
- `game_config.py` contains constants, color themes, command synonyms, default item
  loading, and fallback configuration.
- `gemini_interactions.py` wraps the Google Gemini SDK and provides static fallback
  behavior when the SDK or API key is unavailable.
- `display_mixin.py`, `item_interaction_handler.py`, `npc_interaction_handler.py`,
  and `event_manager.py` contain focused behavior mixed into or composed by `Game`.
- `static_fallbacks.py` contains deterministic text generation helpers and static text.

Data is JSON-driven:

- `data/characters.json`
- `data/items.json`
- `data/locations.json`

Keep schema changes coordinated with loaders, game logic, and tests.

## Environment

Use the repository virtual environment when available:

```bash
.venv/bin/python --version
.venv/bin/python -m pip install -r requirements.txt
```

The current source requirements are minimal:

- `google-genai`
- `blessed`

Do not install new dependencies, modify global Python configuration, or rewrite
environment setup unless the user approves.

## Common Commands

Run the game:

```bash
.venv/bin/python main.py
```

Run the documented unittest suite:

```bash
.venv/bin/python -m unittest discover tests
```

Run one unittest module:

```bash
.venv/bin/python -m unittest tests/test_game_logic.py
```

Some test files are pytest-style and import `pytest`, but `pytest` is not listed in
`requirements.txt`. A full discovered test run may fail with `ModuleNotFoundError:
No module named 'pytest'` until test dependencies are installed or declared.

Style configuration exists for Flake8 and Pylint:

```bash
.venv/bin/python -m flake8 .
.venv/bin/python -m pylint game_engine tests main.py
```

These tools are not listed in `requirements.txt`; verify they are installed before
treating those commands as required checks.

## Testing Notes

Tests are under `tests/`. The suite mixes `unittest.TestCase` tests with pytest-style
functions and fixtures. Preserve compatibility with both styles when editing tests.

When adding behavior:

- Add or update focused tests near the affected module.
- Prefer deterministic tests that mock Gemini calls and random behavior.
- Avoid requiring a real Gemini API key in tests.
- Be aware that save/load tests may touch ignored `savegame*.json` files.

After changes, run the most relevant available check and report exactly what passed
or failed.

## AI and Fallback Behavior

`GeminiAPI` reads credentials from `GEMINI_API_KEY` or `gemini_config.json`.
`gemini_config.json` is user-specific and ignored by git. Do not print, commit, or
rewrite real API keys.

The game is designed to run without Gemini by using static fallbacks. When adding any
new Gemini-generated feature, add deterministic fallback text or behavior and test the
no-key/no-SDK path.

`NaturalLanguageParser` should return structured intents only for available exits,
items, NPCs, and inventory objects. Preserve the safety guard that maps unsafe input
to `unknown`.

## Save Files and Local Artifacts

Ignored local files include:

- `.venv/`, `venv/`
- `gemini_config.json`
- `savegame.json`, `savegame*.json`
- `.coverage`, `htmlcov/`, `.pytest_cache/`
- `*.log`
- `CLAUDE.md`

Do not commit user saves, API config, logs, coverage output, virtual environments, or
other local artifacts.

## Coding Conventions

Follow existing Python style:

- 100-character line length, matching `.flake8` and `.pylintrc`.
- Standard-library imports first, then local imports.
- Keep comments sparse and useful.
- Use explicit, readable names consistent with the existing modules.
- Prefer structured JSON parsing/loading over ad hoc string handling.
- Keep terminal output compatible with the existing `Colors`/display helpers.

When touching data loading, preserve PyInstaller support through
`game_config.get_data_path()` and the `sys._MEIPASS` fallback path.

When touching command behavior, update `COMMAND_SYNONYMS`, parser handling, help text,
and tests together when applicable.

When touching world or event behavior, note that `Game` composes an `EventManager`
instance as `self.event_manager`. Do not assume event state is global.

## Safety

Do not run destructive git commands, delete files, reset branches, overwrite user work,
install new dependencies, or change global/system configuration without explicit user
approval.

Before editing, check `git status --short`. If unrelated changes exist, leave them
alone. If changes overlap with your task, inspect them and work with them rather than
reverting them.

## Completion Expectations

For code changes, summarize:

- changed files
- what changed
- checks run and their results
- remaining risks or follow-ups

If checks were skipped or unavailable, say why.
