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

## High-Priority Improvements

- Investigate automatic Gemini substitution under unittest/pytest: production
  behavior depends on imported test modules and ordinary tests cannot exercise SDK
  compatibility through that path.
- Investigate session lifetime, unbounded input/output retention, and request
  deadlines with controlled failures and measured long-session scenarios.

## Quality of Life Improvements

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
