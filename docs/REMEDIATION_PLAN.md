# Remediation campaign

## Current outcome

The five implementation waves are delivered in separate verified commits. Sixteen
confirmed findings are recorded in [AUDIT_REPORT.md](../AUDIT_REPORT.md), with no
unresolved confirmed critical/high crash, data-loss or progression blocker. Ordinary
CI and frozen console validation now cover all shipped platforms. Manual frozen-TUI,
Windows console-control and optional live-service checks remain explicitly open.

## Architecture and ownership

Startup flows through `main.choose_mode` to a console TerminalSession or the Textual
app and its own TerminalSession. `Game` creates/injects AI, random and terminal
services. `GameState` owns mutable gameplay fields; compatibility descriptors expose
the old Game attributes to its display/item/NPC mixins and service objects.

CommandHandler resolves aliases and scene targets, optionally classifies a single
AI intent, and dispatches to a handler. CommandResult retains the four legacy tuple
fields and exposes continue/load/quit outcomes. Successful actions mutate gameplay
state; WorldManager advances time/schedules and EventManager checks event rules.
Conversation exchanges own their time advancement. Objective progression owns stage
rules. Rendering uses DisplayMixin and the terminal boundary.

Save writes retain the legacy JSON shape and replace the destination atomically.
Load parses and validates detached character/world candidates in `persistence.py`
before applying them to Game. Saves and Gemini configuration live relative to the
launch working directory; history lives under the user's home. Lazy content caches
are module-owned, and color profiles still use module globals. These retained
boundaries and their limitations are listed below.

The TUI owns a blocking daemon worker and a single-slot input queue. UI callbacks
are posted onto the Textual loop, busy input is rejected, and close signals unblock
input. A closed backend remains attached until the worker finishes, preventing a
late read from falling through to console input. Unexpected worker exceptions leave
a visible diagnostic and a quit path. Main console failures write sanitized stack
locations; expected EOF, interrupts and closed output pipes terminate controllably.

Gemini uses synchronous SDK calls with a 10-second transport timeout and one attempt.
Setup failures and session shutdown close the client. Shared response validation
selects static fallbacks; tests inject dependencies instead of changing production
behavior when a test runner is imported. A transport timeout is not a hard wall-clock
process deadline.

## Acceptance ledger

| Criterion | Evidence and status |
|-----------|---------------------|
| Production/content/build/hook inventory | Every tracked area has an outcome in AUDIT_BASELINE.md; no production area remains unassigned |
| Local tests and lint | Source `a6dfa85`: 386 tests pass, Flake8 clean, Pylint 10.00/10 |
| Branch coverage | 91.93% statements, 82.26% branches, 88.94% combined; baseline 88.19% combined |
| Invalid/legacy saves | Real-file malformed/nested types, unknown locations, failed reads, partial writes and failed replacement pass; existing session and last valid save preserved |
| Crash/shutdown boundaries | Worker errors remain visible; redacted diagnostics, denied diagnostic writes, EOF, busy-input shutdown and broken-pipe tests pass; POSIX Ctrl+C tested |
| Main protagonist paths | Scripted offline Raskolnikov `siberia`, Sonya `follow_to_siberia`, Porfiry `case_solved` passed; objective suite covers alternate defined endings |
| Actual Gemini SDK | google-genai 2.8.0 serialization, configured timeout/retries, HTTP failures, empty/blocked/non-text responses and cleanup tested with mocked transport; no live API requests |
| Engine soak | 10,000 seeded actions with moving NPC schedules and save/load round trips completed; recent events capped at 10 |
| TUI soak | 1,000 commands through actual thread/input/rendering bridge completed; history capped at 200 and RichLog at 1,000 lines |
| Python 3.10/3.13 across Windows/Linux/macOS | All six test/ending/soak jobs passed at `73de17d` in run 36257692464 (and at `7dbda3d` in run 36256853518) |
| Frozen Windows/Linux/macOS | All three builds and isolated startup/look/quit/EOF/version smokes passed at `73de17d` in run 36257692464 (and at `7dbda3d` in run 36256853518) |
| Narrow/resized TUI | Headless source app resized to 20×5 then 100×30 and shut down during controlled in-flight work |
| Frozen interactive TUI and Windows real-console Ctrl+C | macOS frozen builds exercised for all three protagonists (startup, scene, completion/history, resize, Ctrl+Q); Windows/Linux interactive checks remain unverified |
| Live Gemini/model availability | Unverified; optional service test requires credentials and a live request |

CI evidence: [first fully passing matrix](https://github.com/AntoanBG3/crimeandpunishment/actions/runs/36227963595),
[pre-heading-fix validation](https://github.com/AntoanBG3/crimeandpunishment/actions/runs/36256853518),
[final-source validation](https://github.com/AntoanBG3/crimeandpunishment/actions/runs/36257692464).
Run 36256853518 at `7dbda3d` and final-source run 36257692464 at `73de17d` both completed successfully: all six interpreter/OS test
and soak jobs plus all three frozen build/smoke jobs passed, including the Windows
closed-output-pipe regression that failed in run 36228403106.

## Completed implementation waves

| Wave | Delivered boundaries / fixes | Commits |
|------|-----------------------------|---------|
| 1: crashes, data integrity and progression | Detached load validation, preserved live state, visible worker diagnostics, authored character attributes, preserved item text | `5bbd205`, `57accd8`, `127f809`, `c95a968`, `db2d276` |
| 2: quick wins | Persuasion timing, save picker, response validity, shared matching, completion, Windows closed pipe, full-width TUI headings, `look at` completion and accurate documentation | `fe8ec38`, `28f852d`, `55b9cb2`, `1791534`, `fa9a146`, `422f7a4`, `7dbda3d`, `7b4e47b`, `73de17d`, `a6dfa85` |
| 3: internal boundaries | AI injection, named tuple-compatible results, gameplay state/RNG injection, TerminalSession, split readable-item handlers | `69199b5`, `e1c858a`, `1fbf75b`, `32ace4b`, `a111c65` |
| 4: measured retention | Isolated scenario harness and bounded UI history, output and recent events | `35fc25d`, `d2b26b7` |
| 5: release hardening | Universal pinned dependencies, six-combination ordinary CI, three shared frozen builds, byte-safe smoke checks and shutdown/invariant regressions | `e1e7be0`, `4866b9c`, `b37acc2` |

The read-handler refactor preserves exact output and state across eight seeded
before/after snapshots: old/fresh newspaper, mother's letter, scripture, anonymous
note, IOU, student book and generic book. Command outcomes retain tuple compatibility;
Game/terminal state changes have dedicated isolation and full-suite coverage.

## Reproducing verification

Use the existing environment or install runtime and development requirements from
the shared constraints. The canonical suite is `python -m unittest discover tests`;
branch coverage uses `coverage run --branch --source=game_engine,main -m unittest discover tests`.
Run Flake8 and `pylint game_engine` after implementation changes.

```sh
python scripts/audit_scenarios.py --scenario console
python scripts/audit_scenarios.py --scenario endings
python scripts/audit_scenarios.py --scenario engine --actions 10000
python scripts/audit_scenarios.py --scenario tui --actions 1000
```

Each invocation starts a child process in a temporary Unicode/spaced directory with
isolated history/config/saves, no inherited Gemini credentials, seed 1729 and a
180-second deadline. Failures expose exit status/traceback; assertions identify
scenario input. Tests add 205 seeded malformed/blank/Unicode/long inputs, all authored
references and reachability of 16 locations from every protagonist start.

Endings hold NPCs at authored starting locations to make command sequences stable;
the engine soak uses moving schedules. The TUI soak exercises the bridge with
controlled narrative, rather than 1,000 story actions. SDK contracts use real SDK
objects with mocked HTTP transport; network timing and service availability are not
established by those tests. CI retains coverage and scenario metrics as artifacts.

## Performance evidence

`AUDIT_BENCHMARKS.json` retains comparable before/after observations plus a later
recheck. The original 1,000-command TUI retained 1,000 history entries and 2,000 log
lines; the fixed version retains 200 and 1,000. Traced memory decreased from 14.04 MB
to 12.10 MB in those runs. The timing increased from 6.45 to 17.34 seconds with input
gating; no speedup is claimed. Recent engine events now stay at 10 rather than 41.

The later engine recheck completed 10,000 actions in 3.71 seconds (median local
command 0.191 ms, p95 0.998 ms); TUI completed in 16.87 seconds with 11.83 MB retained.
These instrumented measurements include the harness and latency samples and do not
prove flat memory over arbitrarily long sessions. Authored journals/memories and the
benchmark's sample list account for additional retained state.

A five-process offline startup/select/look/quit observation had median 444.7 ms.
Separate cProfile runs of 100 operations measured median save 3.00 ms, load 2.49 ms,
world update 0.00125 ms and representative Rich-panel conversion 0.145 ms. Serialization
and defensive copying dominate save/load profiles. Those diagnostic timings include
profiler overhead; no further latency optimization is justified by this small local
scenario. Live model latency is absent from all these figures.

## Ordered remaining work

| Order | Work / rationale | Severity / effort | Follow-up verification / dependencies |
|-------|------------------|-------------------|---------------------------------------|
| 1 | Visually exercise frozen TUI and native console shutdown on every shipped OS. Headless source tests and frozen console smokes do not prove terminal-emulator behavior. | Verification gap / Medium | Download the exact CI artifacts, select each protagonist, resize, exercise completion/history/secret prompt, quit during work; send Ctrl+C from a real Windows console. Requires those interactive platforms. |
| 2 | Optional live Gemini smoke for the configured model. Mocked transport cannot establish current model availability or real timeout behavior. | Verification gap / Small | With authorized credentials, run startup probe and one narrative/intent request, observe bounded recovery and client cleanup without retaining keys/prompts. |
| 3 | Isolate the remaining global color profile if multiple games must render concurrently. The shipped UI has one active session, so this is not a confirmed current gameplay defect. | Low maintenance / Medium | Reproduce color cross-talk between two games before migrating Colors behind a terminal/session adapter; preserve NO_COLOR/theme save compatibility. |
| 4 | Split remaining long dialogue/self-use and character-specific handlers only with characterization coverage. Existing tests and endings pass; length alone does not establish a defect. | Low maintenance / Medium | Snapshot return/text/state for affected characters and item effects, then refactor one responsibility per commit. |
| 5 | Decide whether persisted command history needs rotation. In-memory retention is bounded; deleting disk history would change existing behavior and no disk bottleneck was measured. | Low resource follow-up / Small | Measure loading a realistically large history file and test a user-chosen retention policy, including Unicode and malformed entries. |
| 6 | Add a strict wall-clock AI cancellation boundary if required. One SDK attempt with per-transport timeouts is not equivalent to killing blocked work at ten seconds. | Reliability investigation / Medium | Controlled stalled DNS/connect/read transport or worker tests; verify no duplicate action and no late console fallback after shutdown. Avoid speculative concurrency. |
| 7 | Replace more legacy mocks with boundary tests when touching those areas. Current suite discovery is checked, but high line coverage does not validate every assertion. | Low maintenance / Ongoing | Prefer real temporary files, state invariants and subprocess/real-app tests; preserve ordinary offline execution. |

These items are explicit follow-ups, not hidden failures or confirmed high-severity
bugs. No release was published during the audit; tag/version/signing/publication
behavior remains separate from the exercised build and smoke paths.

## Interactive macOS artifact check

Downloaded `crimeandpunishment-macos` from CI run 36256853518 (source `7dbda3d`),
SHA-256 `79e8b98842e75adb5318b4083a0683f65c2d7c870cec9d5d22b588322c161b7f`.
Executed in a separate tmux server with a temporary spaced/Unicode working directory
and home, cleared Gemini environment keys, and selected `skip` at the masked prompt.
Raskolnikov startup, scene/status rendering, completion cycling, `look`, history
recall, resizing 100×30 → 40×15 → 100×30 and Ctrl+Q all worked. The isolated server
exited afterward. No credentials or personal conversation content were used.

This check exposed R015: Rule headings used only 20 columns in a wide terminal.
The regression failed before `73de17d` and passes at widths 100 and 40 afterward.
A fresh local build from `73de17d` was also launched in an isolated 100-column tmux
terminal: both the full game title and `Choose Your Character` rendered without
truncation, and Ctrl+Q closed the app.
RichLog retains already-rendered lines at their original width after resizing;
new output wraps at the current width. That is a retained UI limitation, not evidence
that older content reflows. Windows/Linux interactive terminal behavior remains unverified; engine ending paths
and headless UI behavior are covered separately.

Heading-fix CI: [run 36257692464](https://github.com/AntoanBG3/crimeandpunishment/actions/runs/36257692464)
at source `73de17d` completed successfully: all six interpreter/OS test and soak
jobs and all three frozen build/smoke jobs passed.

A further macOS build from `2c7eb3a` (source identical to `73de17d`; SHA-256
`25de94e4ef78c005450c23f8e96979e31d09b474983a14cee091579b28d27e34`) was run in the
same isolation for Sonya and Porfiry. Both selections started, rendered full-width
headings, scene listings, objectives and the status bar; argument completion
(`take liz`, `move to hay`), numbered exits, history recall, resizing 100×30 → 40×15
→ 100×30 and Ctrl+Q (exit status 0) worked. This check exposed R016: Tab on
`look at liz`, the form the tutorial hint suggests, offered nothing. The fix in
`a6dfa85` was confirmed in the source TUI; it has not yet been through CI.
