# Tier 3 — Detailed Implementation Plan

All of Tier 3 is now implemented (3A prompt_toolkit input, 3B Textual TUI,
3C gameplay UX), on top of Tier 1 (foundation: wrapping, dedup, compact scene
UI, minimal prompt) and Tier 2 (Rich presentation layer: panels, tables,
rules, status spinner, paced narrative). This document is kept as the design
record: each track opens with a summary of what shipped, followed by the
original plan. It assumes the current architecture:

- **All terminal I/O flows through `game_engine/terminal.py`**: `write_line`
  (wrapped, ANSI-parsed output), `write_renderable` (Rich panels/tables),
  `write_narrative` (paced paragraphs), `read_line` (input), `status`
  (spinner). The final emit goes through `builtins.print`, which is the seam
  the test suite patches.
- `CommandHandler._build_intent_context()` returns
  `{"exits": [{"name": ...}, ...], "items": [...], "npcs": [...], "inventory": [...]}`
  and is the single source of truth for "what is in the scene".
- `COMMAND_SYNONYMS` in `game_config.py` is the single source of truth for
  command words; `numbered_actions_context` on `Game` powers numeric selection.
- The game loop (`Game.run()`) is a blocking while-loop; conversations run a
  nested blocking loop inside `NPCInteractionHandler._handle_talk_to_command`.

Tier 3 has three tracks. **Recommended order: 3A → 3C (parallel-friendly) →
reassess 3B.** Nothing in 3A or 3C is thrown away if 3B happens later.

---

## 3A — prompt_toolkit input layer — DONE

Implemented as specified below: PromptSession with file history in
`terminal.read_line` behind a strict non-TTY fallback, `GameCompleter` in
`game_engine/completion.py`, bottom toolbar via `_status_line_text`, and no
completion inside conversations. Verified with completer unit tests
(`tests/test_completion.py`) and a pty-driven smoke run.

### Goal

Replace bare `input()` with `prompt_toolkit.PromptSession` to get persistent
command history, context-aware tab completion, and a bottom toolbar — the
single biggest discoverability win available without restructuring the game.

### Why prompt_toolkit coexists with Rich

Rich owns *output* (we render to a string and `print` it); prompt_toolkit
owns the *input line* (it draws and erases its own prompt area). They do not
fight over the terminal as long as Rich never prints while a prompt is
active, which is already true: the game is strictly turn-based
(print → prompt → print). The spinner (`terminal.status`) only runs between
prompts.

### Step 1 — Input seam in `terminal.py`

All input already goes through `terminal.read_line(prompt_text, color)`.
Extend it, keeping the plain-`input()` path as fallback:

```python
# terminal.py (sketch)
_session = None          # PromptSession, created lazily
_completer_provider = None  # callable -> prompt_toolkit Completer or None
_toolbar_provider = None    # callable -> str or None

def set_completer_provider(fn): ...
def set_toolbar_provider(fn): ...

def _interactive_input_supported():
    return _console.is_terminal and sys.stdin.isatty()

def read_line(prompt_text, color=""):
    rendered = ...  # existing Rich rendering of the prompt
    if not _interactive_input_supported():
        return input(rendered)            # tests / pipes / dumb terminals
    session = _get_session()              # lazy PromptSession(history=FileHistory(...))
    return session.prompt(
        ANSI(rendered),                   # prompt_toolkit.formatted_text.ANSI
        completer=_completer_provider() if _completer_provider else None,
        bottom_toolbar=_toolbar_provider() if _toolbar_provider else None,
        complete_while_typing=False,      # complete on Tab only; less noisy
    )
```

Key details:

- `prompt_toolkit.formatted_text.ANSI` accepts the ANSI-styled prompt string
  we already render, so the green `> ` arrow carries over unchanged.
- **Fallback rule (non-negotiable, mirrors the AI fallback rule):** when
  stdin/stdout is not a TTY, `read_line` must behave exactly like today's
  `input()`. The entire test suite, piped runs, and `GEMINI_API_KEY`
  non-interactive startup depend on this.
- History: `FileHistory(os.path.expanduser("~/.crimeandpunishment_history"))`
  or a project-local gitignored file (add to `.gitignore`). Up-arrow then
  works across sessions; keep `!!` working as-is (it's handled before
  parsing in `_get_player_input`).

### Step 2 — Context-aware completer

Build one `Completer` fed by the same context dict that already powers NLP
and tutorial hints. New module `game_engine/completion.py`:

```python
class GameCompleter(Completer):
    """First word completes from COMMAND_SYNONYMS (canonical + aliases).
    After a recognized verb, complete the argument from scene context."""

    def __init__(self, context_provider):  # -> _build_intent_context() dict
        self._context = context_provider

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lower()
        ctx = self._context()
        # 1. completing the verb
        if " " not in text:
            yield from match(all_command_words(), text)
            return
        # 2. completing the argument by verb category
        verb, partial = split_longest_known_prefix(text)  # reuse parse_action logic
        if verb == "talk to":        pool = ctx["npcs"]
        elif verb in ("take", "drop", "read", "use"):  pool = ctx["items"] + ctx["inventory"]
        elif verb in ("look",):      pool = ctx["items"] + ctx["npcs"]
        elif verb == "move to":      pool = [e["name"] for e in ctx["exits"]]
        else:                        pool = []
        yield from match(pool, partial)
```

Implementation notes:

- Reuse `CommandHandler.parse_action`'s longest-match logic for
  `split_longest_known_prefix` rather than duplicating it — factor the
  "find longest matching command word" loop into a small helper on
  `CommandHandler` and call it from both places.
- Wire-up in `Game.__init__` (after `command_handler` exists):
  `terminal.set_completer_provider(lambda: GameCompleter(self.command_handler._build_intent_context))`.
- Inside conversations (`talk to` loop), the prompt is free-form dialogue —
  pass *no completer* there. Easiest: `read_line` takes an optional
  `completer=False` override used by the conversation loop's `_input_color`
  call path (add a kwarg that `_input_color` forwards).

### Step 3 — Bottom toolbar

The turn header currently prints `Day 1, Morning · Location · state ·
LOW-AI` once per turn. With a toolbar, that line can live persistently at
the bottom of the screen:

```python
terminal.set_toolbar_provider(lambda: game._toolbar_text())  # same content as _print_turn_header
```

Decision to make at implementation time: keep both (header in scrollback,
toolbar live) or gate the header off when the toolbar is active
(`turn_headers_enabled` already exists as the setting). Recommendation:
when toolbar is active, default `turn_headers_enabled` to off but respect an
explicit `turnheaders on`.

### Step 4 — Numbered actions integration

`numbered_actions_context` keeps working untouched (numeric input is parsed
before commands). Optional polish: a completer entry that shows the numbered
actions as completion candidates with their display text as metadata
(`Completion(text="3", display="3. father's silver watch")`).

### Testing

- Unit-test `GameCompleter` directly with `prompt_toolkit.document.Document`
  fixtures — no terminal needed.
- The non-TTY fallback keeps every existing test green; add one test
  asserting `read_line` uses `input()` when `sys.stdin.isatty()` is False.
- Manual: history persistence across two runs; Tab on empty line lists
  verbs; `talk to <Tab>` lists NPCs present; completion absent inside
  conversations.

### Packaging

prompt_toolkit is pure Python; PyInstaller needs no hooks. Add
`prompt_toolkit` to `requirements.txt`. Windows terminals (legacy conhost)
are supported by prompt_toolkit natively.

### Effort and risks

~1–2 weeks. Risks: low. The only subtle bug class is output printed while a
prompt is active (e.g. a future async feature) — not possible in the current
synchronous loop.

---

## 3B — Full TUI with Textual — DONE

Implemented per the design below. What shipped (as of 3B; the follow-up in
[TUI_PARITY_PLAN.md](TUI_PARITY_PLAN.md) later extended the backend protocol
to `read(prompt_text, completion, secret)`, added Tab completion and shared
history to the Textual `Input`, and made the TUI the default in a TTY):

- **Backend seam in `terminal.py`**: `set_backend(backend)` / `get_backend()`.
  A backend provides `emit(renderable)`, `read(prompt_text)`, `clear()`, and
  `status(message)` (a context manager). With no backend — the default, and
  always the case under tests — every function takes the classic console path
  unchanged, so the existing suite needed zero edits.
- **`game_engine/tui_app.py`**: `TextualBackend` + `CrimeAndPunishmentApp`
  (RichLog narrative pane, one-line status bar, Input widget). The blocking
  game loop runs in a daemon thread; output crosses threads via
  `call_from_thread`; input blocks on a queue; a `_QUIT` sentinel raises
  `EOFError` in the game thread at shutdown. The status bar doubles as the
  toolbar (`toolbar_active()` returns True, keeping the per-turn header
  suppressed) and as the AI "thinking" indicator; `clear_screen()` becomes a
  rule in the log; the pager and the prompt_toolkit `PromptSession` are
  bypassed entirely (the pane scrolls; Textual owns the keyboard).
- **Entry point**: the TUI shipped opt-in (`--tui` / `CRIME_TUI=1`, with a
  graceful warning if textual is missing); the parity plan later flipped the
  default — `--no-tui` / `CRIME_TUI=0` now opt back into the console.
- **Tests** (`tests/test_tui.py`): backend-seam delegation tests with a fake
  backend, plus real-app tests via `App.run_test()` (round trip, quit
  sentinel, status message lifecycle).
- **Packaging**: `textual` added to `requirements.txt`; PyInstaller builds
  including the TUI need `--collect-all textual`.

Deliberately deferred polish: completion inside the Textual `Input` (since
delivered by the parity plan), a command palette fed by `COMMAND_SYNONYMS`,
and a richer sidebar (objectives / inventory snapshot) — the one-line status
bar carries the same content as the console toolbar.

The original design follows for reference.

### Honest framing

This is a refactor, not a port. Textual is async and event-driven; the game
is a blocking loop that prints imperatively from deep call stacks
(`event_manager` actions, `world_manager` validation, nested conversation
loops). The saving grace is that Tiers 1–3 funneled **all** I/O through
`terminal.py`, so the adapter has exactly one seam to intercept.

### The seam as it exists today (post-3A/3C — read before designing)

`terminal.py`'s full surface, every function of which the Textual backend
must map or consciously no-op:

| Function | Console behavior today | Textual mapping |
|---|---|---|
| `write_line(text, color, end)` | Rich-render + `print()` | `RichLog.write` via `call_from_thread` |
| `write_dialogue(text)` | hanging-indent variant | same pane, keep the indent or use CSS padding |
| `write_narrative(text)` | paragraph pacing when `pace on` | timed `RichLog.write` calls or skip pacing |
| `write_renderable(r, allow_paging)` | panels/tables/trees; system pager when tall | `RichLog.write(r)`; paging is free (pane scrolls) |
| `read_line(prompt, color, completion)` | `PromptSession` (TTY) / `input()` | block worker on a queue fed by `Input` widget |
| `set_completer_provider` / `set_toolbar_provider` | prompt_toolkit completer + bottom toolbar | feed Textual `Input` autocomplete + a status bar widget |
| `toolbar_active()` | suppresses the per-turn header | return True in TUI mode (status bar is persistent) |
| `status(message)` | Rich spinner | `LoadingIndicator` / status-bar text |
| `clear_screen()` | `console.clear()` on move (`clearscreen on`) | insert a rule/marker in the log instead |
| `ensure_blank_line` / `separator` / `render_width` | rhythm + width helpers | pane-internal equivalents |

prompt_toolkit interplay: in TUI mode the `PromptSession` path must not be
used at all (Textual owns the event loop and the keyboard); the
`GameCompleter` logic in `completion.py` is UI-agnostic enough to reuse for
an `Input` autocomplete dropdown, but the prompt_toolkit `Completion`
objects would need a thin adapter.

### Architecture: worker-thread adapter

```
┌────────────────────────── Textual App (main thread, async) ─────────────────────────┐
│  ┌───────────────────────────────┐  ┌──────────────────────────────┐               │
│  │ RichLog (narrative, scrolls)  │  │ Sidebar: day/time/location,  │               │
│  │                               │  │ state, objectives summary,   │               │
│  │                               │  │ inventory count              │               │
│  └───────────────────────────────┘  └──────────────────────────────┘               │
│  ┌─────────────────────────────────────────────────────────────────┐               │
│  │ Input widget (single line)            Footer: keybindings       │               │
│  └─────────────────────────────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────────────────────────--┘
                 ▲ call_from_thread(log.write, renderable)      │ input_queue.put(line)
                 │                                              ▼
        ┌─────────────────────────────────────────────────────────────┐
        │ Game thread: existing Game().run() loop, completely blocking │
        │ terminal.write_line → post renderable to app                 │
        │ terminal.read_line  → block on input_queue.get()             │
        └─────────────────────────────────────────────────────────────┘
```

Concrete pieces:

1. **`game_engine/tui_app.py`** — the Textual `App` with the layout above.
   `RichLog` accepts Rich renderables directly, so `write_renderable`
   (panels/tables/rules) and `write_line` (`Text.from_ansi` output) need no
   conversion.
2. **Backend switch in `terminal.py`** — a module-level backend object:

   ```python
   class ConsoleBackend:   # today's behavior (default; used by tests)
       def emit(self, renderable, end="\n"): ...   # capture + print
       def read(self, prompt_rendered): ...        # input() / PromptSession

   class TextualBackend:
       def emit(self, renderable, end="\n"):
           self.app.call_from_thread(self.app.narrative_log.write, renderable)
       def read(self, prompt_rendered):
           self.app.call_from_thread(self.app.show_prompt, prompt_rendered)
           return self.input_queue.get()           # blocks the game thread only
   ```

   `write_line` / `write_renderable` / `read_line` delegate to the active
   backend. `set_backend()` is called once by `tui_app.py` at startup.
3. **Entry point** — `main.py` gains a mode decision: `--no-tui` flag or
   `CRIME_TUI=0` env → classic console; otherwise launch
   `tui_app.run()`, which starts the game thread. Classic mode remains the
   default until the TUI is proven (flip the default later).
4. **Spinner** — `terminal.status()` in TUI mode maps to a Textual
   `LoadingIndicator` or a sidebar "thinking…" state, not Rich's
   `console.status` (which assumes terminal ownership).
5. **Sidebar updates** — after each turn the game thread posts a snapshot
   (day/time/location/state/objective summary) via a small dataclass;
   the app renders it. Don't share live `Game` state across threads — copy
   into the snapshot.
6. **Command palette** — Textual's built-in palette
   (`COMMANDS` provider) mapped from `COMMAND_SYNONYMS` canonical entries;
   selecting one pastes the verb into the input.
7. **Conversation mode** — the nested `talk to` loop works unchanged
   (it blocks on `read_line` like everything else), but style the prompt
   differently (the app knows a conversation is active via the snapshot) and
   consider an inline "end conversation" button/keybinding that injects
   "goodbye" into the queue.

### What breaks and how to handle it

- **Tests:** all input/output mocking assumes the console backend. Keep
  `ConsoleBackend` the default under the test runner (same detection trick
  as the Gemini stub). TUI-specific logic gets its own tests via
  `textual.pilot` (`App.run_test()`), which can drive the input widget and
  assert log contents — budget real time for this.
- **PyInstaller:** Textual ships CSS data files → add
  `--collect-all textual` to the build spec for all three platforms; verify
  the Windows build in a real conhost/Windows Terminal.
- **Ctrl-C / quit:** the game thread must be a daemon thread, and `quit`
  must signal the app to exit (`call_from_thread(app.exit)`); conversely
  app shutdown must unblock a pending `input_queue.get()` (sentinel value).
- **`screen-clear on move`** (3C item) becomes trivial: a marker/separator
  in the `RichLog` instead of an actual clear.

### Effort and recommendation

4–8 weeks including test migration and packaging verification. 3A delivers
most of the *felt* UX gain (history, completion, toolbar) for a fraction of
this cost. Build 3B only if a persistent layout (always-visible status,
scrollback separation, mouse support) is genuinely wanted. The
`terminal.py` backend split is designed so this decision can be deferred
indefinitely without accumulating cost.

---

## 3C — Gameplay/design UX — DONE

All items below are implemented: `map` (Rich tree, visited/unvisited marking),
`journal` panel with category filtering plus automatic Progress entries on
objective advances, `actions` (shared `_display_scene_actions` helper),
`clearscreen on|off` (persisted, clears on move), paging for taller-than-screen
help output, the trigger-based tutorial (`tutorial_steps_done`, persisted,
hints offered at most twice and only when the scene allows the action), and
generation-time verbosity (`response_length_pref` appends a length instruction
in `_generate_content_with_fallback`). A command-wiring test
(`tests/test_command_wiring.py`) now guards COMMAND_SYNONYMS/dispatch
agreement via ast.

## 3C — original plan (for reference)

Independent items, roughly ordered by value/effort. Each follows the
existing pattern: `COMMAND_SYNONYMS` entry + `_process_command` branch +
help entry + the INFO-icon list in `Game.run()` for non-action commands +
tests.

### 3C.1 `map` command (small)

Render known geography from data that already exists:

- Sources: `LOCATIONS_DATA[loc]["exits"]`,
  `player_character.accessible_locations`, `game_state.visited_locations`.
- Render a Rich `Tree` rooted at the current location: exits as branches,
  visited locations plain, unvisited-but-accessible dimmed with "(unvisited)",
  inaccessible omitted entirely (no spoilers).
- One screen, no scrolling ambition; `_print_renderable(tree)`.
- Tests: visited/unvisited marking, current location highlighted.

### 3C.2 `journal` upgrade (small-medium)

`journal` exists (rumors, news, dreams via `add_journal_entry`). Extend it:

- Add entries for objective stage completions (hook the spot where
  `advance_objective_stage` succeeds for the player) and for fired story
  events (`event_manager` after a successful trigger).
- Cap the list (e.g. 50 entries) at append time.
- Render as a Rich table: turn/time, category, text; `journal dreams` /
  `journal rumors` filters by category.
- Persistence: journal lives on `Character` and is already serialized via
  `to_dict()` — verify, and add the new categories to the save round-trip
  test.

### 3C.3 `actions` command (small)

Print the current `numbered_actions_context` on demand (it's only shown
after `look` today). If the context is empty, run the same population logic
`_handle_look_command` uses (factor the scene-listing block into a helper
both call). Also feeds 3A completion metadata for free.

### 3C.4 Scene-change clearing (small)

Setting-gated (`clearscreen on|off`, default off, persisted like
`turn_headers_enabled`): on successful `move to`, emit
`terminal.clear_screen()` (`console.clear()` when TTY; no-op otherwise) so
each location reads as a fresh page. In 3B this becomes a log separator.

### 3C.5 Paging for long output (small)

Wrap genuinely long outputs — full `help`, generated documents
(`get_generated_text_document`), `journal` — in `console.pager()` when the
output exceeds the terminal height and stdout is a TTY. Add
`terminal.paged()` context manager so call sites stay one-liners. Skip
under tests/pipes (pager already no-ops there, but be explicit).

### 3C.6 Trigger-based tutorial (medium)

Replace the flat "first 5 actions" counter with behavior triggers:

- State: a `tutorial_steps_done: set[str]` on `Game` (persisted in saves).
- Triggers: `looked` (after first `look`), `examined` (first `look at`),
  `talked` (first conversation), `moved` (first `move to`),
  `objectives_checked` (first `objectives`).
- After each turn, if a step's prerequisite is met and its hint not yet
  shown, show the *next* most useful hint (e.g. only suggest `talk to` when
  an NPC is actually present — `_build_intent_context` again).
- Keep `tutorial_turn_limit` as a hard stop so hints never outstay their
  welcome. Delete `_tutorial_hint_shown_for_step` bookkeeping in favor of
  the set.

### 3C.7 Verbosity at generation time (medium)

Today AI text is generated long and trimmed by `_apply_verbosity`. Better:
ask for the right length up front.

- In `gemini_interactions.py`, thread a `target_length` hint into the prompt
  templates: brief → "in 1–2 sentences", standard → "in one short
  paragraph", rich → no constraint.
- `GeminiAPI` methods take an optional `verbosity` arg; call sites pass
  `game.verbosity_level`. Keep `_apply_verbosity` as a safety net (the model
  will not always comply) — it already never cuts mid-sentence.
- Measure: with brief verbosity this also cuts token usage meaningfully.

### 3C.8 Interactive save/load picker — DONE

Implemented: `load` with no argument and multiple save files prints the
numbered saves table and dispatches the choice through
`numbered_actions_context` (`load_slot` action type); a single named save
with no default file loads directly.

### 3C.9 Polish items carried from Tier 2 — DONE

All implemented: `terminal.write_dialogue` hanging indent (used by
`_print_dialogue` for NPC/persuasion/NPC–NPC lines), conversation `history`
as a dim panel, endings and progression `narrate` texts through
`_print_narrative`, `narrative_pace` persisted in saves, non-TTY API-key
auto-skip, and removal of `SPINNER_FRAMES`/`SEPARATOR_LINE`, the `blessed`
dependency, and its two sanity scripts.

---

## Sequencing summary

| Order | Work | Effort | Depends on |
|-------|------|--------|------------|
| 1 | 3A prompt_toolkit (seam → completer → toolbar) | 1–2 wk | — |
| 2 | 3C.1 map, 3C.3 actions, 3C.8 load picker, 3C.9 polish | days each | — |
| 3 | 3C.2 journal, 3C.6 tutorial, 3C.7 generation-time verbosity | ~1 wk each | — |
| 4 | 3C.4 clear, 3C.5 paging | days | — |
| 5 | 3B Textual TUI | 4–8 wk | reassess after 1–4 |

Every step keeps the suite green via the same two rules that made Tiers 1–2
safe: all I/O goes through `terminal.py`, and non-TTY environments always
fall back to plain `print`/`input`.
