# Audit baseline and inventory

- Baseline commit: `1aa3721`.
- Python: 3.13.5; macOS arm64.
- Tests: 332 passed. Flake8 clean; Pylint 10.00/10.
- Branch-enabled combined coverage: 88%; not an acceptance target by itself.

## Installed baseline packages

- `google-genai==2.8.0`
- `rich==15.0.0`
- `prompt_toolkit==3.0.52`
- `textual==8.2.7`
- `httpx==0.28.1`
- `coverage==7.13.5`
- `flake8==7.3.0`
- `pylint==4.0.5`
- `pyinstaller==6.20.0`

## Review inventory

| Path | Review | Exercise |
|------|--------|----------|
| `.claude/settings.json` | Pending detailed review | Pending |
| `.claude/skills/run-crimeandpunishment/SKILL.md` | Pending detailed review | Pending |
| `.codex/hooks.json` | Pending detailed review | Pending |
| `.flake8` | Pending detailed review | Pending |
| `.github/workflows/release.yml` | Pending detailed review | Pending |
| `.pylintrc` | Pending detailed review | Pending |
| `AGENTS.md` | Pending detailed review | Pending |
| `LICENSE.md` | Pending detailed review | Pending |
| `README.md` | Pending detailed review | Pending |
| `data/characters.json` | Pending detailed review | Pending |
| `data/items.json` | Pending detailed review | Pending |
| `data/locations.json` | Pending detailed review | Pending |
| `docs/FEATURE_COMMITS.md` | Pending detailed review | Pending |
| `game_engine/__init__.py` | Pending detailed review | Baseline suite |
| `game_engine/character_module.py` | Pending detailed review | Baseline suite |
| `game_engine/command_handler.py` | Pending detailed review | Baseline suite |
| `game_engine/completion.py` | Pending detailed review | Baseline suite |
| `game_engine/display_mixin.py` | Pending detailed review | Baseline suite |
| `game_engine/event_manager.py` | Pending detailed review | Baseline suite |
| `game_engine/game_config.py` | Pending detailed review | Baseline suite |
| `game_engine/game_state.py` | Pending detailed review | Baseline suite |
| `game_engine/gemini_interactions.py` | Pending detailed review | Baseline suite |
| `game_engine/item_interaction_handler.py` | Pending detailed review | Baseline suite |
| `game_engine/location_module.py` | Pending detailed review | Baseline suite |
| `game_engine/npc_interaction_handler.py` | Pending detailed review | Baseline suite |
| `game_engine/objective_progression.py` | Pending detailed review | Baseline suite |
| `game_engine/static_fallbacks.py` | Pending detailed review | Baseline suite |
| `game_engine/terminal.py` | Pending detailed review | Baseline suite |
| `game_engine/tui_app.py` | Pending detailed review | Baseline suite |
| `game_engine/world_manager.py` | Pending detailed review | Baseline suite |
| `main.py` | Pending detailed review | Pending |
| `requirements-dev.txt` | Pending detailed review | Pending |
| `requirements.txt` | Pending detailed review | Pending |
| `scripts/feature_commit_hook.py` | Pending detailed review | Pending |
| `tests/__init__.py` | Pending detailed review | Baseline suite |
| `tests/test_character_and_gemini.py` | Pending detailed review | Baseline suite |
| `tests/test_character_module.py` | Pending detailed review | Baseline suite |
| `tests/test_command_handler.py` | Pending detailed review | Baseline suite |
| `tests/test_command_wiring.py` | Pending detailed review | Baseline suite |
| `tests/test_completion.py` | Pending detailed review | Baseline suite |
| `tests/test_coverage_gaps.py` | Pending detailed review | Baseline suite |
| `tests/test_display_mixin.py` | Pending detailed review | Baseline suite |
| `tests/test_event_manager.py` | Pending detailed review | Baseline suite |
| `tests/test_feature_commit_hook.py` | Pending detailed review | Baseline suite |
| `tests/test_game_logic.py` | Pending detailed review | Baseline suite |
| `tests/test_game_state.py` | Pending detailed review | Baseline suite |
| `tests/test_gemini_interactions.py` | Pending detailed review | Baseline suite |
| `tests/test_item_interaction_handler.py` | Pending detailed review | Baseline suite |
| `tests/test_main_mode.py` | Pending detailed review | Baseline suite |
| `tests/test_npc_interaction_handler.py` | Pending detailed review | Baseline suite |
| `tests/test_objective_progression.py` | Pending detailed review | Baseline suite |
| `tests/test_supplemental.py` | Pending detailed review | Baseline suite |
| `tests/test_terminal_and_ux.py` | Pending detailed review | Baseline suite |
| `tests/test_tui.py` | Pending detailed review | Baseline suite |
| `tests/unittest_function_loader.py` | Pending detailed review | Baseline suite |
