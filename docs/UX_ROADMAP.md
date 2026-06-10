# UX Roadmap — Leftover Tasks

Tier 1 (foundation), Tier 2 (Rich presentation layer), Tier 3A (prompt_toolkit
input layer), and all of the smaller items discovered along the way are
implemented, as is all of Tier 3C. The only remaining roadmap item is the
optional Textual TUI (3B).

> **See [TIER3_PLAN.md](TIER3_PLAN.md) for the extensive, step-by-step Tier 3
> implementation plan** (architecture sketches, file-level changes, testing and
> packaging notes, sequencing). The sections below are the short summary.

## Where things stand

All game output flows through `game_engine/terminal.py`, which uses Rich to
word-wrap at `min(terminal width, 88)`, parse the ANSI codes embedded by the
`Colors` class, and honor `NO_COLOR` / dumb terminals / piped output. The final
emit goes through `builtins.print`, so tests keep patching the same seam.

On top of that funnel: status, objectives, inventory, help, `map`, `journal`,
the conversation `history` panel, and the `saves` listing render as Rich
panels/tables/trees via `_print_renderable` (help pages when taller than the
terminal); dialogue prints with a hanging indent via
`write_dialogue`/`_print_dialogue`; the AI spinner is `console.status`; dreams,
endings, and progression narration go through `write_narrative` (paragraph
pacing, toggled with `pace on`, persisted in saves). `load` without a slot
offers a numbered picker when several saves exist; a typed scene number
examines the item. Piped/non-TTY input auto-skips the API-key prompt;
Ctrl+C/Ctrl+D exit gracefully. The `blessed` dependency and the dead
`SPINNER_FRAMES`/`SEPARATOR_LINE` constants are gone.

Input is prompt_toolkit when interactive (Tab completion, persistent history,
live bottom toolbar) and plain `input()` otherwise. While the toolbar is
visible, the per-turn header is suppressed — `turnheaders on` brings it back
explicitly (`turn_headers_explicit`, persisted). All UX settings (theme,
verbosity, pace, clearscreen, turn headers, tutorial progress) persist in
saves, and verbosity also steers AI generation length
(`gemini_api.response_length_pref`).

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

## Tier 3C — Gameplay/design UX — DONE

Implemented: `map` (tree of known places, unvisited dimmed), `journal` as a
panel with category filters and automatic Progress entries on objective
advances, `actions` (numbered scene listing on demand), `clearscreen on|off`
(persisted; clears on move), paging for taller-than-screen help, the
trigger-based tutorial (steps keyed off actual player behavior, persisted in
saves, each hint offered at most twice), and generation-time verbosity (the
AI is asked for 1–2 sentences / one paragraph per the verbosity setting
instead of generating long and trimming). `tests/test_command_wiring.py`
guards COMMAND_SYNONYMS/dispatch agreement so unreachable commands like the
old `journal` bug can't recur.

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
