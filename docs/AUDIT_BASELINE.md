# Audit baseline and inventory

Baseline: `1aa3721`, Python 3.13.5, macOS arm64; 332 tests passed, Flake8 clean,
Pylint 10.00/10. Combined branch/statement coverage was 88.19% (3,939/4,312
statements; 1,631/2,004 branches). At `7dbda3d`, 384 tests pass locally;
coverage is 4,282/4,658 statements and 1,710/2,080 branches (88.93% combined).

Baseline installed direct/tool packages: google-genai 2.8.0, rich 15.0.0,
prompt_toolkit 3.0.52, textual 8.2.7, httpx 0.28.1, coverage 7.13.5,
flake8 7.3.0, pylint 4.0.5 and pyinstaller 6.20.0. The tested complete dependency
graph now lives in `constraints.txt`; see `DEPENDENCIES.md` for regeneration.

## Review inventory

Every tracked source/content/build/hook area is listed below. Review means the
specified responsibility or risk was inspected; exercise records actual checks.
It does not claim all possible paths or every terminal emulator were covered.
The ignored local `CLAUDE.md` was read as background and contains historical module
and roadmap references; current repository guidance is in `AGENTS.md`.

| Path | Review outcome | Exercise / remaining limit |
|------|----------------|----------------------------|
| `.claude/settings.json` | Local Bash command allowlist; does not grant production behavior | JSON read; host-specific agent activation not exercised |
| `.claude/skills/run-crimeandpunishment/SKILL.md` | Corrected offline and harness instructions; legacy driver limitations explicit | Documented ending command and driver syntax check |
| `.claude/skills/run-crimeandpunishment/driver.sh` | Legacy Bash/tmux workflow inherits config and writes local state; prefer isolated harness | bash -n passed; tmux capture paths not exercised in this campaign |
| `.codex/hooks.json` | SessionStart/Stop reminders delegate to read-only Python hook | JSON reviewed and Python logic tested; app activation not independently verified |
| `.flake8` | 100-column preference; E501 ignored, selected E402 exceptions | Full repository lint passed |
| `.gitattributes` | Text normalization only | Git checkout in each OS job |
| `.github/workflows/ci.yml` | Ordinary push/PR validation, locked installs, artifacts and separate frozen jobs | Six OS/interpreter jobs plus three frozen jobs |
| `.github/workflows/release.yml` | Tag/version guard, draft publication, shared locked build/smoke steps | Shared builder exercised in CI; actual release publishing not invoked |
| `.gitignore` | Runtime saves/config, secrets, logs and build artifacts excluded; CLAUDE.md local | Working-tree review; temporary harness keeps runtime files isolated |
| `.pylintrc` | Broad complexity/docstring exceptions; score is not structural-quality proof | game_engine lint passed at 10.00/10 |
| `AGENTS.md` | Feature commits, state ownership and compatibility guidance updated | Instruction/code comparison and diff check |
| `AUDIT_REPORT.md` | Evidence, commands and stated limitations reviewed against current campaign | Diff/whitespace and cross-reference review; executable examples checked where changed |
| `LICENSE.md` | GPL version 3-or-later notice; README previously contradicted it | Text review only; no licensing change |
| `README.md` | Setup, command, offline, architecture and license claims corrected; R014 | Examples compared to implementation and ending scenario run |
| `app_icon.ico` | Existing icon asset; shared build script does not reference it | File type inspected; no functional runtime dependency |
| `constraints.txt` | Resolved universal pinned graph, including conditional OS/Python dependencies | Clean pip installs and pip check across six combinations |
| `data/characters.json` | 14 entries: authored stats, inventories, starting locations, schedules and objectives | References for every entry; R003 initialization and protagonist endings |
| `data/items.json` | 19 item definitions, effects, hidden locations and readable content | Reference integrity, transfer/read/consumption suites |
| `data/locations.json` | 16 locations, exits, contents and navigation reachability | Every location reachable from all three starts; moving-schedule soak |
| `docs/AUDIT_BASELINE.md` | Evidence, commands and stated limitations reviewed against current campaign | Diff/whitespace and cross-reference review; executable examples checked where changed |
| `docs/AUDIT_BENCHMARKS.json` | Evidence, commands and stated limitations reviewed against current campaign | Diff/whitespace and cross-reference review; executable examples checked where changed |
| `docs/DEPENDENCIES.md` | Evidence, commands and stated limitations reviewed against current campaign | Diff/whitespace and cross-reference review; executable examples checked where changed |
| `docs/FEATURE_COMMITS.md` | Evidence, commands and stated limitations reviewed against current campaign | Diff/whitespace and cross-reference review; executable examples checked where changed |
| `docs/REMEDIATION_PLAN.md` | Evidence, commands and stated limitations reviewed against current campaign | Diff/whitespace and cross-reference review; executable examples checked where changed |
| `game_engine/__init__.py` | Package initialization; no additional runtime ownership | Imports in all suites and frozen startup |
| `game_engine/character_module.py` | Inventory, copies, memories, skills, objectives and serialization; R001/R003/R010 | Character, persistence, transfer and objective suites |
| `game_engine/command_handler.py` | Aliases, dispatch, shared matching, numbered choices and NLP gate; R011 | Command wiring/results, target selection, malformed-input and engine scenarios |
| `game_engine/command_result.py` | Named result retains tuple fields and explicit loop outcomes | Command-result compatibility and command wiring tests |
| `game_engine/completion.py` | Shared scene context and ownership-compatible candidates; R012 | Completion suite for console and TUI candidates |
| `game_engine/diagnostics.py` | Exception type and stack locations only; no prompt/message/locals | Runtime failure redaction and denied-write tests |
| `game_engine/display_mixin.py` | Rich output, map/journal, help, verbosity, more, presentation seams | Display, terminal/UX and full engine scenarios |
| `game_engine/event_manager.py` | Event prerequisites, one-shot flags, generated items and fallback use; R009 | Event, fallback, objective and soak tests |
| `game_engine/game_config.py` | Lazy resources, constants, aliases and global color settings; color isolation deferred | Command wiring, NO_COLOR tests and frozen foreign-directory startup |
| `game_engine/game_state.py` | Startup, session loop, save writing and settings; R001/R007 | Full suite; partial write/replace, permission, legacy and invalid-save regressions |
| `game_engine/gemini_interactions.py` | SDK/client lifecycle, transport options, config, parsing and bounded prompt inputs; R004/R009 | Actual SDK mocked transport; configuration, response and parser regressions |
| `game_engine/item_interaction_handler.py` | Targeting, transfer ownership, consumption and readable content; R009/R010/R011 | Item/transfer suites, seeded read snapshots and protagonist scenarios |
| `game_engine/location_module.py` | Lazy content loading and bundled resource resolution | Reference/reachability tests and frozen foreign-directory startup |
| `game_engine/npc_interaction_handler.py` | Dialogue sub-loop/time, persuasion and confession; R005 | NPC/persuasion, objective and ending scenarios |
| `game_engine/objective_progression.py` | Prerequisites, stage transitions, rewards and supported endings | Objective tests and all three scripted protagonist endings |
| `game_engine/persistence.py` | Detached candidate validation, numeric/container checks and legacy defaults; R001 | Real-file malformed/legacy loads and live-state preservation tests |
| `game_engine/session_state.py` | Mutable gameplay ownership and compatibility descriptors | Two-game isolation, RNG and persistence round trips |
| `game_engine/static_fallbacks.py` | Fallback signatures, narrative availability and injected random choices | Fallback, deterministic RNG and offline ending scenarios |
| `game_engine/terminal.py` | Console IO, history, paging, non-TTY/NO_COLOR, secret input and session context; R006 | Terminal/UX, history retention and concurrent/nested session tests |
| `game_engine/tui_app.py` | Thread/queue lifecycle, busy input, errors, history and resizing; R002/R006 | Real App.run_test tests, shutdown tests and 1,000-command soak |
| `game_engine/world_manager.py` | Character initialization, time/day rollover, schedules, movement, event summaries and endings; R003/R006/R011 | World initialization, game logic, reachability, progression and 10,000-action soak |
| `main.py` | Mode selection, controlled exits, Windows closed-pipe diagnostics; R002/R013 | Mode, subprocess shutdown and frozen console checks |
| `requirements-build.txt` | PyInstaller constrained by shared lock | Three OS frozen builds |
| `requirements-dev.txt` | Offline test/lint packages constrained by shared lock | Full tests, branch coverage, lint |
| `requirements.in` | Direct version inputs to lock generation | Universal resolution and clean environments |
| `requirements.txt` | Runtime packages constrained by shared lock | Clean installs and source/frozen smokes |
| `scripts/audit_scenarios.py` | Isolated child processes, stripped credentials, seed, deadline and invariant checks | Console/endings, 10,000 engine actions and 1,000 TUI commands on CI |
| `scripts/build_release.py` | Shared portable build command; Textual/data/dynamic SDK collection | Three OS frozen builds and isolated console smokes |
| `scripts/feature_commit_hook.py` | Read-only reminder, dirty-tree review guard, no auto-staging/commit/push | Temporary Git repository tests on all six CI combinations |
| `tests/__init__.py` | Package marker only; no test-runner SDK substitution | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_ai_fallback_boundary.py` | Discovered regression scope: ai fallback boundary | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_audit_invariants.py` | Discovered regression scope: audit invariants | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_audit_scenarios.py` | Discovered regression scope: audit scenarios | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_character_and_gemini.py` | Discovered regression scope: character and gemini | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_character_module.py` | Discovered regression scope: character module | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_command_handler.py` | Discovered regression scope: command handler | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_command_results.py` | Discovered regression scope: command results | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_command_wiring.py` | Discovered regression scope: command wiring | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_completion.py` | Discovered regression scope: completion | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_coverage_gaps.py` | Discovered regression scope: coverage gaps | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_display_mixin.py` | Discovered regression scope: display mixin | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_event_manager.py` | Discovered regression scope: event manager | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_feature_commit_hook.py` | Discovered regression scope: feature commit hook | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_game_logic.py` | Discovered regression scope: game logic | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_game_state.py` | Discovered regression scope: game state | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_gemini_interactions.py` | Discovered regression scope: gemini interactions | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_item_interaction_handler.py` | Discovered regression scope: item interaction handler | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_item_transfers.py` | Discovered regression scope: item transfers | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_main_mode.py` | Discovered regression scope: main mode | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_npc_interaction_handler.py` | Discovered regression scope: npc interaction handler | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_objective_progression.py` | Discovered regression scope: objective progression | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_persistence_boundary.py` | Discovered regression scope: persistence boundary | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_persuasion_regressions.py` | Discovered regression scope: persuasion regressions | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_process_shutdown.py` | Discovered regression scope: process shutdown | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_retention_limits.py` | Discovered regression scope: retention limits | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_runtime_failures.py` | Discovered regression scope: runtime failures | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_save_menu.py` | Discovered regression scope: save menu | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_sdk_contract.py` | Discovered regression scope: sdk contract | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_session_dependencies.py` | Discovered regression scope: session dependencies | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_supplemental.py` | Discovered regression scope: supplemental | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_target_selection.py` | Discovered regression scope: target selection | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_terminal_and_ux.py` | Discovered regression scope: terminal and ux | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_terminal_sessions.py` | Discovered regression scope: terminal sessions | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_tui.py` | Discovered regression scope: tui | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/test_world_initialization.py` | Discovered regression scope: world initialization | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |
| `tests/unittest_function_loader.py` | Function discovery and temporary-fixture compatibility reviewed | Canonical unittest suite; test discovery retained on Python 3.10/3.13 |

## Test-quality limits

Existing suites use extensive mocks and synthetic Game stand-ins. New boundary
checks add real files, real subprocesses, the actual SDK with mocked HTTP transport,
and real headless Textual apps. The test inventory records discovery and exercised
scope, not a line-by-line certification of every legacy assertion. Full-suite results
must be interpreted together with command-level scenarios and explicit external
verification limits in `REMEDIATION_PLAN.md`.
