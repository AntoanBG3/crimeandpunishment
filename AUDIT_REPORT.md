# Codebase Audit Report

**Project:** Crime and Punishment
**Date:** 2026-09-25
**Scope:** Full engine, content, console/TUI, AI, persistence, tooling and releases.

## Executive Summary

The baseline at `1aa3721` passes 332 tests under Python 3.13.5 on macOS arm64.
Flake8 passes and Pylint reports 10.00/10. Branch-enabled coverage is 88% combined
statement/branch coverage: 4,312 statements, 2,004 branches. These results do not
establish cross-platform, packaged-runtime, or live-service compatibility.

This is a living audit. Findings require reproduction or concrete control-flow
evidence; investigation targets are not counted as confirmed defects. The campaign
prioritizes state preservation and diagnostic failures before structural cleanup.
Inventory, dependencies, acceptance evidence and deferred work are maintained in
`docs/REMEDIATION_PLAN.md` and `docs/AUDIT_BASELINE.md`.

## Critical Issues

### R001 — Failed loads destroy the current session

- **Category / severity / confidence:** Robustness / High / Confirmed.
- **Effort:** Medium. **Status:** Fixed; commit identified by `fix: preserve live state when save validation fails`.
- **Location:** `game_engine/game_state.py:load_game`, `game_engine/persistence.py:prepare_restore`.
- **Evidence:** New real-file regressions failed on the baseline: malformed saves
  set `player_character` to None, mutated time/world state, and retained old numbered
  selections after a successful load (10 failing subcases).
- **Recommendation / implementation:** Prepare a validated candidate with detached
  characters/world inventory, then apply it once. Retain the old state on rejection,
  validate numeric/container fields and locations, and clear transient scene state.
  Keep the legacy JSON shape and defaults; unknown removed NPCs remain skippable.
- **Verification:** `tests.test_persistence_boundary`; full suite 335 tests passes.
  Existing synthetic fixtures now supply consistent location data, and the old test
  that expected player destruction now asserts preservation.

### R002 — Unexpected worker exceptions close the TUI

- **Category / severity / confidence:** Robustness / High / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `fix: retain safe diagnostics for unexpected runtime failures`.
- **Location:** `game_engine/tui_app.py:_run_game`, `main.py`, `game_engine/diagnostics.py`.
- **Evidence:** A runner raising ValueError made the real Textual app stop; the new
  headless regression failed its `app.is_running` assertion before the fix.
- **Implementation:** Keep the diagnostic visible, disable further input, allow
  Ctrl+Q, and return failure status. Console failures also write a sanitized report;
  broken pipes terminate quietly. Reports retain exception type and stack locations,
  never exception messages, source lines, locals, API keys or conversation text.
- **Verification:** Runtime/TUI/mode suite (39 tests), secret-redaction and unwritable
  diagnostic tests, Flake8 and Pylint. No automatic save of potentially damaged state.

### R003 — New games discard authored character mechanics

- **Category / severity / confidence:** Robustness / High / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `fix: initialize authored character skills and relationships`.
- **Location:** `game_engine/world_manager.py:load_all_characters`.
- **Evidence:** All ten authored characters had empty skills instead of their JSON
  modifiers; the new initialization test failed ten subcases before the change.
- **Implementation:** Pass authored skills, psychology and NPC relationships into
  Character, using its existing defensive copies. This restores intended mechanics
  rather than changing authored balance.
- **Verification:** 339 tests pass, Flake8 clean, Pylint 10.00/10.

## High-Priority Improvements

### R008 — Advertised Python 3.10 support was not routinely exercised

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Medium. **Status:** Validation added; remote matrix pending.
- **Location:** `.github/workflows/ci.yml`, `constraints.txt`, `scripts/build_release.py`.
- **Evidence:** Only tag/manual validation on Python 3.13 existed, with unpinned
  dependencies. A clean Python 3.10 run caught newer f-string quoting introduced
  during this campaign; it was corrected before publication of the validation batch.
- **Implementation:** Pin the universal dependency graph, share release/build logic,
  run six interpreter/OS test combinations and three frozen console smokes on
  ordinary development pushes and PRs. Keep publication restricted to release tags.
- **Verification:** Clean macOS Python 3.10/3.13 environments pass all 363 tests and
  dependency checks; its frozen binary passes startup/look/quit/EOF from an isolated
  Unicode directory. The sandbox semaphore restriction required an unsandboxed
  frozen smoke. Cross-platform results will be recorded separately.

First CI run [36191659270](https://github.com/AntoanBG3/crimeandpunishment/actions/runs/36191659270)
passed all six interpreter/OS test-and-soak jobs and the macOS/Linux frozen checks.
The Windows executable built, but the smoke harness assumed UTF-8 while frozen
Python emitted locale-encoded text. This was a harness decoding failure, not a
demonstrated game crash. `fix: inspect frozen smoke markers without locale assumptions`
adds a failing-then-passing real subprocess fixture emitting Windows-style bytes
and checks ASCII markers directly. Windows revalidation is pending.

### R004 — Production AI behavior changes under test runners

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Medium. **Status:** Fixed; commit `refactor: inject AI clients and verify the real SDK offline`.
- **Location:** `game_engine/gemini_interactions.py:GeminiAPI`, `game_engine/game_state.py:run`.
- **Evidence:** A regression importing the actual installed SDK found a SimpleNamespace
  substitute instead. Whitespace and non-string responses were also accepted as text.
- **Implementation:** Remove test-runner detection, allow explicit SDK/client/UI injection,
  validate usable text, close clients on failed setup and session exit, configure a
  10-second transport timeout and one attempt instead of implicit SDK retries.
- **Verification:** 344-test full suite passed, then six SDK contract tests passed,
  covering real serialization, timeout settings, HTTP 401/403/404/429/500/503,
  transport exceptions and empty/blocked responses using httpx.MockTransport.
  No live API requests were used. Transport timeouts are not a hard process deadline.
- **Source:** [Google SDK HTTP options](https://googleapis.github.io/python-genai/genai.html),
  checked against installed 2.8.0 types and actual request extensions.
### R006 — Long sessions retain unbounded UI history and recent events

- **Category / severity / confidence:** Performance / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `perf: bound long-session history and serialize TUI input`.
- **Location:** `game_engine/tui_app.py`, `game_engine/terminal.py:load_history_lines`,
  `game_engine/world_manager.py:advance_time`.
- **Evidence:** 1,000 TUI commands retained 1,000 history entries and 2,000 rendered
  lines; 10,000 engine actions grew the recent-event list to 41. Rapid submissions
  queued an unwanted second command in a failing real-app test.
- **Implementation:** Keep 200 in-memory history entries, 1,000 rendered log lines,
  and 10 recent events. Parse history with a bounded deque. Accept one command per
  prompt and close a full input queue without blocking shutdown. History remains
  persisted on disk; this change bounds retained entries, not the history file size.
- **Verification:** Both full soaks completed before and after; exact observations
  are in `docs/AUDIT_BENCHMARKS.json`. Regression tests cover recent-event retention,
  input duplication, bounded history, and existing shutdown behavior.

### R005 — Persuasion advances time twice and bypasses shared behavior

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `fix: make persuasion use shared matching and turn timing`.
- **Location:** `game_engine/npc_interaction_handler.py:_handle_persuade_command`.
- **Evidence:** A command plus world-update regression recorded two `advance_time(1)`
  calls; an article/surname target failed despite the shared matcher supporting it.
  The handler also called a configured model while LOW-AI was enabled.
- **Implementation:** Let the main turn own time, use the shared NPC matcher, respect
  LOW-AI, and correct the restored atmospheric-cache attribute name.
- **Verification:** Two focused regressions plus the full suite and linters.

## Quality of Life Improvements

### R011 — Target selection differs between commands and survives movement

- **Category / severity / confidence:** UX / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `fix: resolve exact targets and clear departed scene actions`.
- **Location:** `command_handler.py` matchers, `world_manager.py` movement,
  `item_interaction_handler.py` giving.
- **Evidence:** Three failing regressions demonstrated exact-name ambiguity (`note`
  versus `notebook`), stale numbered actions after movement, and giving rejecting
  an article/surname accepted by other NPC commands.
- **Implementation:** Prefer exact matches, reuse NPC resolution when giving,
  and clear numbered actions on successful movement. Run `actions` for a new list.
- **Verification:** All 373 tests pass, Flake8 clean, Pylint 10.00/10.

### R010 — Item transfers discard generated documents

- **Category / severity / confidence:** Robustness / High / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `fix: preserve item contents across inventory transfers`.
- **Location:** `item_interaction_handler.py` take/drop/give handlers.
- **Evidence:** Taking a generated anonymous note removed its text, making it
  unreadable. Giving and rejected transfers similarly lost instance details.
  A legacy stack with omitted quantity also raised KeyError on take.
- **Implementation:** Copy instance details on accepted transfers, restore the exact
  inventory on rejection, and consistently treat omitted quantity as one.
- **Regression:** Three real-world transfer regressions initially raised errors;
  tests now cover take/read/drop/retake, give/rejection, and legacy stack quantities.

### R009 — Empty AI text bypasses item and event fallbacks

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `fix: reject unusable AI narration consistently`.
- **Location:** `gemini_interactions.py:_generate_content_with_fallback`, item/event handlers.
- **Evidence:** Whitespace newspaper responses produced empty narration; non-text and
  indented OOC responses were recorded as AI news. Empty-response diagnostics included
  the first 200 characters of the prompt, potentially containing conversation text.
- **Implementation:** Use the shared text validator across item/event fallbacks and
  the generation boundary. Keep prompt content out of generation diagnostics.
- **Regression:** `tests/test_ai_fallback_boundary.py` initially failed six subcases
  and errored twice; it now verifies static news and content-free failure logs.

### R007 — Save selection crashes on invalid metadata or disappearing files

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `fix: tolerate invalid save-menu metadata`.
- **Location:** `game_engine/game_state.py:_handle_saves_command`.
- **Evidence:** Three regressions initially produced a Rich type error, a missing-file
  error, and stale numbered actions after an empty save picker.
- **Implementation:** Render metadata as text, tolerate unavailable timestamps, clear
  picker state before listing. Candidate loading also rejects non-text readable-item
  content and invalid memory fields before they can enter the active session (R001).
- **Verification:** 360 tests pass, Flake8 clean, Pylint 10.00/10.

R001 follow-up (`fix: preserve legacy memories and reject malformed nested saves`):
legacy text memories migrate to readable structured entries. Nested text/numeric
memory fields and overflowing numbers are rejected before state replacement.
The new legacy/invalid-type regressions initially failed six cases and raised an
overflow once; all 367 tests now pass with clean lint and Pylint 10.00/10.

- Audit stale UI-default documentation, misleading multi-action NLP examples,
  malformed save-slot metadata and stale numbered scene actions.

## Quick Wins

| # | Improvement | Category | Location |
|---|-------------|----------|----------|
| 1 | Correct TUI-default and NLP documentation after behavior verification | QoL | README.md, game_engine/tui_app.py |
| 2 | Run validation on pull requests as well as releases | Robustness | .github/workflows |

## Summary Statistics

Confirmed finding counts will be populated after reproductions; no zero-defect
claim is implied by this initial inventory.

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| UX | pending | pending | pending | pending |
| QoL | pending | pending | pending | pending |
| Robustness | pending | pending | pending | pending |
| Performance | pending | pending | pending | pending |
| Accessibility | pending | pending | pending | pending |
| Security | pending | pending | pending | pending |
