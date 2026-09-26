# Remediation campaign

## Order and compatibility

1. Record the baseline, inspect ownership, and reproduce state/crash defects.
2. Repair persistence and crash handling with regressions; commit each fix.
3. Repair small command/UI issues and document actual behavior.
4. Separate persistent state, services, command outcomes, and injected runtime
   dependencies; preserve existing commands, save JSON and narrative content.
5. Measure engine/TUI long sessions and optimize demonstrated retention/cost.
6. Add routine cross-platform CI, dependency constraints, and packaged smoke tests.
7. Re-run acceptance scenarios and record unresolved external verification.

No live API request or publishing action is part of ordinary verification.

## Architecture map

`main.choose_mode` selects console or Textual. `Game` owns mutable world state and
inherits presentation and item/NPC handlers. CommandHandler parses and dispatches;
WorldManager advances time and schedules; EventManager applies narrative events;
objective_progression advances data-backed objectives. All services currently
hold the Game instance. JSON content is lazily loaded into module caches.

Terminal functions bridge console rendering/input or a Textual backend. Textual
owns the event loop and a blocking game worker; the backend posts UI callbacks and
waits on an input queue. TerminalSession owns each UI's backend, providers, pacing
and history settings; context activation adapts legacy module calls. Color profiles
still use module globals. Save/load writes relative to the working directory;
history writes to the user's home. Gemini configuration is a relative JSON file,
and Gemini client calls are synchronous. These are the external-state boundaries
that the isolated harness must control.

## Acceptance ledger

| Criterion | Status |
|-----------|--------|
| Baseline tests and linters | Passed locally; see AUDIT_BASELINE.md |
| Invalid saves preserve current session | Passed: R001, real-file regressions and 335-test suite |
| Unexpected worker errors produce diagnostics | Passed: R002, headless real-app regression |
| Three protagonist offline paths and all main endings | Three command-level paths passed; existing progression tests cover alternate endings |
| Actual SDK with mocked transport | Passed: R004, six real-SDK contract tests |
| 10,000-action engine / 1,000-command TUI soak | Both completed before/after retention fixes; see AUDIT_BENCHMARKS.json |
| Routine Python 3.10/3.13 OS matrix | Configured; clean macOS 3.10/3.13 pass 363 tests; remote runs pending |
| Frozen Windows/Linux/macOS smoke checks | macOS clean build and console smoke passed; Windows/Linux pending |
| Live Gemini compatibility | Unverified; requires optional credentials/service check |

## Backlog policy

Each confirmed finding receives an ID, severity, confidence, reproduction, location,
proposed fix, regression and resolving commit in AUDIT_REPORT.md. Update this ledger
after verification, not after merely writing a test or a CI job. Do not mark remote
platform checks as passed on the strength of local macOS tests.

## Completed structural boundaries

- `refactor: split readable-item handlers without changing story effects`: reading
  dispatch delegates newspapers, letters, scripture, notes, IOUs and books to
  focused methods. Eight seeded before/after snapshots compare return values,
  exact rendered text, character state, event summaries and notoriety; all match.

- `refactor: name command outcomes and isolate selected-item dispatch`: dispatch
  returns immutable named results, and the main loop branches on TurnOutcome.
  A tuple-compatible adapter preserves existing handler consumers. The selected
  item interaction is now a separate method; command wiring remains AST-checked.
  Full pre-addition suite: 347 passing; four outcome/wiring tests pass afterward.

- `refactor: separate gameplay state and inject session dependencies`: GameState
  owns mutable gameplay fields; explicit compatibility descriptors keep existing
  handlers working while services remain on Game. Game accepts AI, terminal and RNG
  dependencies. Character skill checks, world events and narrative choices share
  the injected RNG; defaults preserve existing callers. State isolation, deterministic
  random sequences and injected output are regression tested.

## Reproducible scenarios

TerminalSession now isolates worker and UI callback settings. Tests cover concurrent
workers, nested context restoration after an exception, independent history paths,
and per-game pacing. The legacy terminal module remains a compatibility adapter.
Shutdown retains a closed backend until the worker exits, preventing a late read
from unexpectedly falling through to console input.

Additional audit regressions validate every authored location/item reference and
reachability of all 16 locations from all three starting positions. Seed 1729
drives 205 malformed/blank/Unicode/long command inputs with unchanged player state.
The TUI resizes down to 20×5 and quits by Ctrl+Q during controlled in-flight work;
the worker's subsequent input request receives EOF. Save checks inject denied
reads, partial writes and failed replacement while preserving the last valid file.
Console subprocess checks cover Ctrl+C at the startup prompt on POSIX and broken
output pipes. Rich intentionally exits 1 on a broken pipe; the direct main boundary
exits 0. Both terminate without a traceback or crash report. Windows console control
events still require an interactive console check; Ctrl+Q is covered through Textual.

Run `.venv/bin/python scripts/audit_scenarios.py --scenario NAME`, where NAME is
`endings`, `console`, `engine`, or `tui`. Use `--actions 10000` for the engine and
`--actions 1000` for TUI. Each invocation starts a child process in a temporary
Unicode/spaced working directory with isolated history/config/saves, no inherited
Gemini credentials, seeded randomness, and a 180-second process deadline.

Endings use authored starting locations with stationary NPC schedules to make
command sequences reproducible; engine soaks exercise the real moving schedules.
TUI soak exercises the real thread/input/rendering bridge with controlled narrative,
not 1,000 story actions. Engine memory measurements include the benchmark's latency
list. Wall-clock results are observations, not portable performance promises.
