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

Pending reproduction: failed save restoration mutates the running game before
validation completes; TUI worker exceptions can close the application without a
recoverable in-app diagnostic. Severity will be assigned after reproduction.

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
