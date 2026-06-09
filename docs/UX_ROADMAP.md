# UX Roadmap — Leftover Tasks

Tier 1 (foundation), Tier 2 (Rich presentation layer), Tier 3A (prompt_toolkit
input layer), and all of the smaller items discovered along the way are
implemented. What remains is the optional Textual TUI (3B) and the
gameplay-level UX items (3C) minus the two already done (3C.8 load picker,
3C.9 polish).

> **See [TIER3_PLAN.md](TIER3_PLAN.md) for the extensive, step-by-step Tier 3
> implementation plan** (architecture sketches, file-level changes, testing and
> packaging notes, sequencing). The sections below are the short summary.

## Where things stand

All game output flows through `game_engine/terminal.py`, which uses Rich to
word-wrap at `min(terminal width, 88)`, parse the ANSI codes embedded by the
`Colors` class, and honor `NO_COLOR` / dumb terminals / piped output. The final
emit goes through `builtins.print`, so tests keep patching the same seam.

On top of that funnel: status, objectives, inventory, help, the conversation
`history` panel, and the `saves` listing render as Rich panels/tables via
`_print_renderable`; dialogue prints with a hanging indent via
`write_dialogue`/`_print_dialogue`; the AI spinner is `console.status`; dreams,
endings, and progression narration go through `write_narrative` (paragraph
pacing, toggled with `pace on`, persisted in saves). `load` without a slot
offers a numbered picker when several saves exist; a typed scene number
examines the item. Piped/non-TTY input auto-skips the API-key prompt. The
`blessed` dependency and the dead `SPINNER_FRAMES`/`SEPARATOR_LINE` constants
are gone.

## Tier 3A — prompt_toolkit input layer — DONE

Implemented: `terminal.read_line` uses a lazy `PromptSession` when stdin/stdout
is a real terminal (plain `input()` everywhere else, so tests and pipes are
unaffected). Persistent up-arrow history in `~/.crimeandpunishment_history`;
Tab completion via `game_engine/completion.py` (`GameCompleter`), fed by
`CommandHandler._build_intent_context()` — verbs from `COMMAND_SYNONYMS`, then
NPCs after `talk to`/`persuade`, scene items after `take`, inventory after
`drop`/`use`/`give`, both after `read`/`look`, exits after `move to`; no
completion inside conversations (free-form dialogue). Bottom toolbar shows the
same day/period/location/state line as the turn header (`_status_line_text`).

## Tier 3B — Full TUI with Textual (4–8 weeks, reassess after 3A)

A refactor, not a port: run the blocking game loop in a worker thread;
`terminal.write_line` posts to a scrollable `RichLog` pane via
`call_from_thread`; input arrives through a queue from an `Input` widget.
Thanks to the `terminal.py` funnel this touches only that module plus a new
`tui_app.py`. Layout: narrative log, status sidebar, input bar, command
palette. Costs: input-mocking tests break for TUI mode (keep plain console as
the default/test mode with a `--no-tui` fallback); PyInstaller needs
`--collect-all textual`. 3A delivers most of the felt gain at a fraction of the
cost — only do this if the ambition justifies it.

## Tier 3C — Gameplay/design UX (parallel, library-agnostic)

- `map` command rendering known locations and exits from `accessible_locations`
  plus `visited_locations` (data already in `LOCATIONS_DATA`).
- Extend the existing `journal` with objective-stage completions and a capped
  log of notable AI moments (extend `_remember_ai_output`), persisted in saves.
- Setting-gated screen clear on `move to` so each location reads as a fresh page.
- Paging for long output (help, dreams, generated documents) via `console.pager()`.
- `actions` command exposing the full numbered verb–target list.
- Trigger-based tutorial: fire hints off actual player behavior (first
  conversation, first room fully explored) instead of a flat action count.
- Verbosity at generation time: prompt Gemini for the target length per
  verbosity level (prompt templates in `gemini_interactions.py`) instead of
  generating long and trimming after the fact.

## Discovered during implementation — all resolved

- ~~Interactive save/load picker~~ — **done.** `load` with no slot and multiple
  saves shows the numbered `saves` table (`_handle_saves_command(numbered=True)`)
  and dispatches the choice via `numbered_actions_context` (`load_slot` type);
  a single named save with no default file loads directly.
- ~~Hanging indent for dialogue~~ — **done.** `terminal.write_dialogue` indents
  wrapped continuation lines; NPC dialogue, persuasion, and NPC–NPC interaction
  go through `DisplayMixin._print_dialogue`.
- ~~Conversation history headers~~ — **done.** The in-conversation `history`
  sub-command renders a dim "Recent Conversation" panel.
- ~~`display_help` flat list~~ — **done** in Tier 2 (per-category Rich panels).
- ~~Endings/scripted events bypass `write_narrative`~~ — **done.** The
  game-ending conclusion and objective-progression `narrate` texts go through
  `_print_narrative`, so `pace on` covers them.
- ~~`pace` not persisted~~ — **done.** `narrative_pace` is saved and restored
  in `save_game`/`load_game`.
- ~~Dead `SPINNER_FRAMES`/`SEPARATOR_LINE`~~ — **done.** Removed from
  `game_config.py`.
- ~~`blessed` dependency~~ — **done.** Dropped from `requirements.txt`;
  deleted `tests/blessed_manual.py` and `tests/blessed_sanity.py`.
- ~~API-key prompt loop on piped input~~ — **done.** Non-TTY stdin skips
  straight to placeholder responses instead of looping to EOFError.
- ~~Numbered scene items prompt "what to do with…"~~ — **done.** A typed number
  now examines the item (`look_at_item`); take/use/give remain word commands.
