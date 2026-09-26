# AGENTS.md

Repository guidance for coding agents. Read the relevant implementation before editing;
use `CLAUDE.md` for additional background, and verify its details against current code.

## Working style

- Be concise, direct, and practical. Avoid praise, filler, and emojis.
- Base conclusions on code, logs, command output, or user-provided information.
  State uncertainty; do not invent results or project context.
- Prefer small, focused changes. Preserve existing architecture, naming, formatting,
  and unrelated user changes.
- After changes, run relevant checks. Report changed files, behavior, checks actually
  run, and remaining risks. If a check was skipped, explain why.

## Feature commits

- Commit each completed feature, bug fix, or independent documentation change after
  its relevant checks pass, before starting the next feature. Do not wait until the
  end of a multi-feature task to make one large commit.
- Inspect the diff and stage only the files or hunks belonging to that change.
  Preserve pre-existing user edits; never sweep them into a commit with `git add .`.
- Use a concise, descriptive commit message. Keep the implementation and its tests
  together. Do not commit unfinished or failing work just to satisfy a checkpoint.
- When pushing is authorized, push completed features in small batches. Do not
  accumulate unrelated features into a massive update or push automatically merely
  because a local commit was made.
- A user's explicit instruction not to commit takes precedence. If a commit is
  blocked, explain why and leave the changes intact.
- `.codex/hooks.json` runs `scripts/feature_commit_hook.py` at session start and
  stop. It reminds the agent of this workflow and requests one commit-review pass
  when the tree is dirty. It does not infer feature boundaries, stage files, commit,
  or push by itself; the agent performs the reviewed commit. See
  `docs/FEATURE_COMMITS.md` for activation and limitations.

## Project and development commands

This is a Python terminal adventure based on *Crime and Punishment*, with Raskolnikov,
Sonya, and Porfiry as playable protagonists. Gemini supplies optional generated text;
the game must remain playable without the SDK or an API key. Rich handles rendering,
prompt_toolkit handles console input, and Textual provides the default interactive TUI.

Use the existing `.venv` (Python 3.13). Run commands from the repository root:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
python main.py                     # TUI in an interactive terminal
python main.py --no-tui            # Classic console
python -m unittest discover tests  # Canonical full test suite
python -m unittest tests.test_game_logic
flake8 .
pylint game_engine
coverage run -m unittest discover tests
coverage report
```

Install dependencies only when needed. The canonical test runner is `unittest`, even
though the development requirements include pytest. Non-TTY streams and missing
Textual fall back to the console; preserve the mode-selection behavior in `main.py`.

## Architecture and ownership

- `main.py`: UI selection, version output, and application startup.
- `game_engine/game_state.py`: `Game`, the main loop, save/load, and shared state.
  `Game` inherits `DisplayMixin`, `ItemInteractionHandler`, and
  `NPCInteractionHandler`; these mixins operate on the live `Game` instance.
- `session_state.py`: `GameState` owns gameplay fields; compatibility descriptors
  on `Game` preserve existing handlers. Inject AI, randomness and terminal services
  through `Game` instead of detecting a test runner.
- `persistence.py`: validates detached save candidates before replacing live state.
- `command_result.py`: tuple-compatible `CommandResult` and explicit `TurnOutcome`.
- `world_manager.py`, `command_handler.py`, and `event_manager.py`: service objects
  holding references to `Game`. **EventManager is not a mixin**; access it through
  `game.event_manager`. Check all services when renaming shared state attributes.
- `terminal.py`: the shared input/output boundary for console and TUI.
  `display_mixin.py` composes presentation; `tui_app.py` bridges the blocking game
  loop and Textual using a worker thread and input queue.
  `TerminalSession` isolates backend, providers, pacing and history; activate the
  session around legacy module calls and keep a closed backend until its worker exits.
- `gemini_interactions.py`: Gemini integration and natural-language parsing.
  `static_fallbacks.py`: offline narrative text and generators.
- `objective_progression.py`: objective progression rules.
- `game_config.py`: command aliases, themes, timing/probability constants, version,
  and resource-path helpers. Read values here instead of copying them from docs.
- `data/characters.json`, `data/locations.json`, and `data/items.json`: game content.
  Engine filenames above are relative to `game_engine/`.

## Rules to preserve

### Input and presentation

- Route game input/output through `terminal.py`, preferably using the existing
  `DisplayMixin` wrappers such as `_print_color`, `_print_block`, `_print_renderable`,
  `_print_dialogue`, `_print_narrative`, and `_input_color`.
- Do not introduce direct `print()` or `input()` in gameplay code. Existing debug
  and validation output is an exception, not a pattern for player-facing output.
- Keep console, non-TTY, and TUI behavior working. Interactive features must degrade
  gracefully when terminal capabilities are unavailable; respect `NO_COLOR`.
- Preserve Textual's thread bridge and EOF shutdown behavior. Avoid manipulating
  Textual widgets directly from the game worker thread.

### Commands and game state

- Add command aliases to `COMMAND_SYNONYMS` and dispatch handling to
  `CommandHandler._process_command()`. Update help and, for non-action commands,
  the main loop's INFO-icon classification. Run `tests.test_command_wiring`.
- Reuse `_resolve_prefix_match` and `_get_matching_exit` for targets. Preserve
  article stripping, word-boundary matching, and `look at` connective handling.
- Use `_build_intent_context()` for scene context shared by NLP, completion, and
  hints. Keep numbered scene actions consistent with `look` and `actions`.
- Preserve the command result tuple:
  `(action_taken, show_atmospherics, time_to_advance, special_flag)`.
  `load_triggered` restarts the loop; other truthy special flags quit.
  Prefer `CommandResult` and its `outcome` property while retaining tuple compatibility.
- Conversation exchanges advance time internally. Do not also advance time for
  `talk to` at the main-loop level.
- Mutate `dynamic_location_items` for live world inventory, not static JSON data.
  Check character-specific effects and avoid double-consuming items; `cheap vodka`
  already removes itself in its self-use handler.

### AI and persistence

- Every AI content type needs a non-empty static fallback. Handle missing, empty,
  blocked, or `(OOC:` responses and LOW-AI mode; reuse existing response-validation
  helpers. Exercise parser changes without AI so generated prose cannot hide bugs.
- Keep tests offline with mocked/stubbed Gemini calls. Do not require credentials
  or a live API request for ordinary verification.
- Keep verbosity, `gemini_api.response_length_pref`, and the `more` command's saved
  full text consistent, including after loading a save.
- Preserve save-slot sanitization, character `to_dict()`/`from_dict()` behavior,
  dynamic world state, triggered events, and persisted UX settings. When adding
  persisted fields, supply defaults for older saves and check a save/load round trip.
- Use `get_base_path()`/`get_data_path()` for bundled resources and preserve lazy
  JSON loading. Do not assume the current working directory contains game data.
- Keep API keys, `gemini_config.json`, save files, and local runtime artifacts out
  of commits.

## Verification and packaging

- Start with the tests for the changed subsystem; run the full suite for shared
  engine behavior. Add regression coverage for fixes that affect gameplay.
- Mock the existing display wrappers for output assertions. For Rich objects,
  inspect text with `terminal.renderable_to_text()`.
- Some tests use top-level functions registered through `load_tests` and
  `tests/unittest_function_loader.py`. Preserve their discovery under unittest.
  Update lightweight state fixtures when services require new `Game` methods.
- UI changes should cover both the console seam and the Textual app. Relevant
  suites include `test_main_mode`, `test_terminal_and_ux`, `test_completion`, and
  `test_tui`; TUI tests use `App.run_test()`.
- Follow `.flake8` and `.pylintrc`; aim for the existing 100-column style without
  unrelated formatting churn. Documentation-only changes need a diff/whitespace
  review rather than gameplay tests unless they change executable examples.
- `.github/workflows/release.yml` runs tests across Windows, Linux, and macOS and
  builds PyInstaller executables. Preserve bundled `data`, Textual resources
  (`--collect-all textual`), and dynamic Gemini import collection.
  `.github/workflows/ci.yml` also validates ordinary pushes and PRs on Python 3.10
  and 3.13. Use `scripts/build_release.py` and the pinned requirements for builds;
  `scripts/audit_scenarios.py` isolates saves, configuration and credentials for smokes.
- For release work, `game_config.GAME_VERSION` must match the release tag;
  the workflow checks this. Do not change the version for unrelated edits.
