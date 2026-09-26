# Codebase Audit Report

**Project:** Crime and Punishment
**Date:** 2026-09-26
**Scope:** Full engine, content, console/TUI, AI, persistence, tooling and releases.

## Executive Summary

The campaign identified 14 confirmed findings: four high, eight medium and two
low severity. Fixes preserve failed-load state, retain crash diagnostics, restore
authored mechanics and item contents, and correct command, AI and UI edge cases.
Each implementation was verified and committed separately. No confirmed high or
critical crash, data-loss or progression blocker remains open in this inventory.

At source commit `7dbda3d`, all 384 local tests pass with clean Flake8 and Pylint
10.00/10. Coverage is 91.93% of statements, 82.21% of branches, 88.93% combined;
the baseline at `1aa3721` had 332 tests and 88.19% combined coverage. These numbers
are evidence of exercised paths, not proof that the application has no defects.
All six interpreter/OS jobs and three frozen console smokes passed in CI run
36256853518. Cross-platform evidence and remaining manual/service checks are tracked in
[the remediation ledger](docs/REMEDIATION_PLAN.md); every tracked production area
has a review outcome in [the inventory](docs/AUDIT_BASELINE.md).

## Critical Issues

### R001 — Failed loads destroy the current session

- **Category / severity / confidence:** Robustness / High / Confirmed.
- **Effort:** Medium. **Status:** Fixed; commit identified by `5bbd205`.
- **Location:** `game_engine/game_state.py:215`; `game_engine/persistence.py:117`.
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
- **Expected behavior:** A rejected save leaves the existing playable session intact; successful legacy loads restore the supported JSON fields.
- **Dependencies:** Character serialization and world data; no save-format migration required beyond legacy defaults.

R001 follow-up (`c95a968`):
legacy text memories migrate to readable structured entries. Nested text/numeric
memory fields and overflowing numbers are rejected before state replacement.
The new legacy/invalid-type regressions initially failed six cases and raised an
overflow once; all 367 tests now pass with clean lint and Pylint 10.00/10.

### R002 — Unexpected worker exceptions close the TUI

- **Category / severity / confidence:** Robustness / High / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `57accd8`.
- **Location:** `game_engine/tui_app.py:221`; `game_engine/diagnostics.py:8`; `main.py:92`.
- **Evidence:** A runner raising ValueError made the real Textual app stop; the new
  headless regression failed its `app.is_running` assertion before the fix.
- **Implementation:** Keep the diagnostic visible, disable further input, allow
  Ctrl+Q, and return failure status. Console failures also write a sanitized report;
  broken pipes terminate quietly. Reports retain exception type and stack locations,
  never exception messages, source lines, locals, API keys or conversation text.
- **Verification:** Runtime/TUI/mode suite (39 tests), secret-redaction and unwritable
  diagnostic tests, Flake8 and Pylint. No automatic save of potentially damaged state.
- **Expected behavior:** Unexpected worker failure stays visible with a recoverable quit path and safe diagnostics.
- **Dependencies:** Existing subsystem tests; independent of broader restructuring.

### R003 — New games discard authored character mechanics

- **Category / severity / confidence:** Robustness / High / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `127f809`.
- **Location:** `game_engine/world_manager.py:173`.
- **Evidence:** The ten characters with authored skill modifiers had empty skills instead of their JSON
  modifiers; the new initialization test failed ten subcases before the change.
- **Implementation:** Pass authored skills, psychology and NPC relationships into
  Character, using its existing defensive copies. This restores intended mechanics
  rather than changing authored balance.
- **Verification:** 339 tests pass, Flake8 clean, Pylint 10.00/10.
- **Expected behavior:** New characters receive the modifiers, psychology and relationships authored in their data.
- **Dependencies:** Existing subsystem tests; independent of broader restructuring.

### R010 — Item transfers discard generated documents

- **Category / severity / confidence:** Robustness / High / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `db2d276`.
- **Location:** `game_engine/item_interaction_handler.py:57`; `game_engine/item_interaction_handler.py:534`; `game_engine/item_interaction_handler.py:1263`.
- **Evidence:** Taking a generated anonymous note removed its text, making it
  unreadable. Giving and rejected transfers similarly lost instance details.
  A legacy stack with omitted quantity also raised KeyError on take.
- **Implementation:** Copy instance details on accepted transfers, restore the exact
  inventory on rejection, and consistently treat omitted quantity as one.
- **Regression:** Three real-world transfer regressions initially raised errors;
  tests now cover take/read/drop/retake, give/rejection, and legacy stack quantities.
- **Expected behavior:** Transfers preserve instance text and rejected transfers preserve the original inventory.
- **Dependencies:** Existing Character inventory acceptance rules.

## High-Priority Improvements

### R004 — Production AI behavior changes under test runners

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Medium. **Status:** Fixed; commit `69199b5`.
- **Location:** `game_engine/gemini_interactions.py:148`.
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
- **Expected behavior:** Tests exercise the same SDK boundary as production; setup failures release clients and return usable fallbacks.
- **Dependencies:** Pinned google-genai SDK and mocked HTTP transport.

### R005 — Persuasion advances time twice and bypasses shared behavior

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `fe8ec38`.
- **Location:** `game_engine/npc_interaction_handler.py:308`.
- **Evidence:** A command plus world-update regression recorded two `advance_time(1)`
  calls; an article/surname target failed despite the shared matcher supporting it.
  The handler also called a configured model while LOW-AI was enabled.
- **Implementation:** Let the main turn own time, use the shared NPC matcher, respect
  LOW-AI, and correct the restored atmospheric-cache attribute name.
- **Verification:** Two focused regressions plus the full suite and linters.
- **Expected behavior:** A persuasion command advances one turn and shares normal target and LOW-AI rules.
- **Dependencies:** Existing subsystem tests; independent of broader restructuring.

### R006 — Long sessions retain unbounded UI history and recent events

- **Category / severity / confidence:** Performance / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `d2b26b7`.
- **Location:** `game_engine/tui_app.py:135`; `game_engine/terminal.py:235`; `game_engine/world_manager.py:43`.
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
- **Expected behavior:** UI memory and recent-event summaries remain bounded, and input submitted while busy cannot become a later action.
- **Dependencies:** Scenario harness measurements and real Textual bridge tests.

### R007 — Save selection crashes on invalid metadata or disappearing files

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `28f852d`.
- **Location:** `game_engine/game_state.py:269`.
- **Evidence:** Three regressions initially produced a Rich type error, a missing-file
  error, and stale numbered actions after an empty save picker.
- **Implementation:** Render metadata as text, tolerate unavailable timestamps, clear
  picker state before listing. Candidate loading also rejects non-text readable-item
  content and invalid memory fields before they can enter the active session (R001).
- **Verification:** 360 tests pass, Flake8 clean, Pylint 10.00/10.

- **Expected behavior:** Bad listing metadata or a vanished save cannot terminate the picker or preserve stale choices.
- **Dependencies:** Existing subsystem tests; independent of broader restructuring.

### R008 — Advertised Python 3.10 support was not routinely exercised

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Medium. **Status:** Implemented in `e1e7be0`; all six platform test jobs and three frozen smokes passed at final source `7dbda3d`.
- **Location:** `.github/workflows/ci.yml:1`; `scripts/build_release.py:11`; `constraints.txt:1`.
- **Evidence:** Only tag/manual validation on Python 3.13 existed, with unpinned
  dependencies. A clean Python 3.10 run caught newer f-string quoting introduced
  during this campaign; it was corrected before publication of the validation batch.
- **Implementation:** Pin the universal dependency graph, share release/build logic,
  run six interpreter/OS test combinations and three frozen console smokes on
  ordinary development pushes and PRs. Keep publication restricted to release tags.
- **Verification:** Clean macOS Python 3.10/3.13 environments pass all 363 tests and
  dependency checks; its frozen binary passes startup/look/quit/EOF from an isolated
  Unicode directory. The sandbox semaphore restriction required an unsandboxed
  frozen smoke. Cross-platform results are linked below.

First CI run [36191659270](https://github.com/AntoanBG3/crimeandpunishment/actions/runs/36191659270)
passed all six interpreter/OS test-and-soak jobs and the macOS/Linux frozen checks.
The Windows executable built, but the smoke harness assumed UTF-8 while frozen
Python emitted locale-encoded text. This was a harness decoding failure, not a
demonstrated game crash. `4866b9c`
adds a failing-then-passing real subprocess fixture emitting Windows-style bytes
and checks ASCII markers directly. All nine jobs passed in [run 36227963595](https://github.com/AntoanBG3/crimeandpunishment/actions/runs/36227963595). Final-source [run 36256853518](https://github.com/AntoanBG3/crimeandpunishment/actions/runs/36256853518) also passed all nine jobs.

- **Expected behavior:** Every advertised interpreter/OS combination is routinely tested with reproducible package versions.
- **Dependencies:** GitHub Actions runners and dependency index; publishing remains separate.

### R009 — Empty AI text bypasses item and event fallbacks

- **Category / severity / confidence:** Robustness / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `55b9cb2`.
- **Location:** `game_engine/gemini_interactions.py:67`; `game_engine/item_interaction_handler.py:790`.
- **Evidence:** Whitespace newspaper responses produced empty narration; non-text and
  indented OOC responses were recorded as AI news. Empty-response diagnostics included
  the first 200 characters of the prompt, potentially containing conversation text.
- **Implementation:** Use the shared text validator across item/event fallbacks and
  the generation boundary. Keep prompt content out of generation diagnostics.
- **Regression:** `tests/test_ai_fallback_boundary.py` initially failed six subcases
  and errored twice; it now verifies static news and content-free failure logs.

R009 parser follow-up (`fa9a146`): non-text intent
responses raised AttributeError and overflowing confidence raised OverflowError;
NaN/Infinity confidence became 1.0. A failing regression now ensures these responses
have zero confidence. AI progress indicators also use the injected terminal service.

- **Expected behavior:** Empty, blocked, OOC or malformed model responses cannot become successful game narration or high-confidence intents.
- **Dependencies:** Shared response validator from R004.

### R011 — Target selection differs between commands and survives movement

- **Category / severity / confidence:** UX / Medium / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `1791534`.
- **Location:** `game_engine/command_handler.py:65`; `game_engine/world_manager.py:603`.
- **Evidence:** Three failing regressions demonstrated exact-name ambiguity (`note`
  versus `notebook`), stale numbered actions after movement, and giving rejecting
  an article/surname accepted by other NPC commands.
- **Implementation:** Prefer exact matches, reuse NPC resolution when giving,
  and clear numbered actions on successful movement. Run `actions` for a new list.
- **Verification:** All 373 tests pass, Flake8 clean, Pylint 10.00/10.
- **Expected behavior:** Exact targets win over partial matches, and numbered choices describe the current scene.
- **Dependencies:** Existing subsystem tests; independent of broader restructuring.

### R013 — Windows closed output pipes produce false crash reports

- **Category / severity / confidence:** Robustness / Medium / Confirmed on Windows CI.
- **Effort:** Small. **Status:** Fixed in `7dbda3d`; both Windows regression jobs pass in run 36256853518.
- **Location:** `main.py:27`.
- **Evidence:** Both Windows Python versions in CI run 36228403106 exited 120 after
  `OSError: [Errno 22] Invalid argument`, wrote a crash report, then failed final
  stdout flushing when their output reader had closed. POSIX cases passed.
- **Implementation:** Recognize Windows EINVAL only when a non-terminal stdout also
  fails flushing; redirect its final flush to the null device. Ordinary filesystem
  failures retain diagnostics. The same subprocess regression now passes on Windows 3.10 and 3.13.
- **Local regression:** Verify healthy stdout and unrelated permission errors are
  never classified as a broken pipe; verify the Windows flush-failure condition.
- **Expected behavior:** Closing an output reader terminates without a false crash report on Windows as on POSIX.
- **Dependencies:** Windows CI regression added in `b37acc2`.

## Quality of Life Improvements

### R012 — Completion suggests unowned reading targets and omits carried inspection

- **Category / severity / confidence:** QoL / Low / Confirmed.
- **Effort:** Small. **Status:** Fixed; commit `422f7a4`.
- **Location:** `game_engine/completion.py:17`.
- **Evidence:** `read` offered room items that its handler requires the player to
  carry; `look` omitted carried items that inspection supports.
- **Implementation:** Complete reading from inventory and inspection from both
  inventory and room targets. Two updated/new regression cases failed before the fix.
- **Expected behavior:** Suggested targets satisfy the ownership rules of the chosen command.
- **Dependencies:** Existing subsystem tests; independent of broader restructuring.

### R014 — Documentation promises behavior the game does not provide

- **Category / severity / confidence:** QoL / Low / Confirmed.
- **Effort:** Small. **Status:** Corrected in `7b4e47b`.
- **Location:** `README.md:8`; `AGENTS.md:64`.
- **Evidence:** README named MIT despite the GPL version 3-or-later notice in
  LICENSE.md; it advertised multi-action NLP and deterministic offline play despite
  a single-intent schema and random world/skill checks. The legacy driver inherits
  credentials/configuration, so piped input alone does not guarantee offline play.
- **Implementation:** Correct these claims and document the isolated harness,
  updated state boundaries, locked dependencies and ordinary CI.
- **Verification:** Compare claims with local implementation and license notice;
  run the documented ending scenario, shell syntax check and whitespace review.
- **Expected behavior:** Documentation accurately describes the license notice, offline setup and supported single-action commands.
- **Dependencies:** Existing subsystem tests; independent of broader restructuring.

## Quick Wins

All entries below are implemented; their IDs link the evidence above to the commits.

| # | Improvement | Category | Location |
|---|-------------|----------|----------|
| R003 | Restore authored skills and relationships | Robustness | world_manager.py:173 |
| R005 | Fix persuasion timing and matching | Robustness | npc_interaction_handler.py:308 |
| R007 | Keep malformed save listings usable | Robustness | game_state.py:269 |
| R010 | Preserve generated documents when transferred | Robustness | item_interaction_handler.py:57 |
| R011 | Prefer exact targets and clear departed actions | UX | command_handler.py:65 |
| R012 | Complete targets the command can act on | QoL | completion.py:17 |
| R014 | Correct setup, licensing and command claims | QoL | README.md:8 |

## Summary Statistics

Counts describe confirmed findings, including resolved ones. Zero entries mean no
confirmed finding in that category, not a comprehensive accessibility/security certification.
Historical per-fix test counts above are checkpoints; the latest full suite has 384 tests.

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| UX | 0 | 0 | 1 | 0 |
| QoL | 0 | 0 | 0 | 2 |
| Robustness | 0 | 4 | 6 | 0 |
| Performance | 0 | 0 | 1 | 0 |
| Accessibility | 0 | 0 | 0 | 0 |
| Security | 0 | 0 | 0 | 0 |
