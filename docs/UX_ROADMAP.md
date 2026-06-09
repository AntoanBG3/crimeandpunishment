# UX Roadmap — Leftover Tasks

Tier 1 (foundation) and Tier 2 (Rich presentation layer) of the UX overhaul are
implemented. This document captures what remains: the ambitious Tier 3 paths and
smaller items discovered during implementation.

## Where things stand

All game output now flows through `game_engine/terminal.py`, which uses Rich to
word-wrap at `min(terminal width, 88)`, parse the ANSI codes embedded by the
`Colors` class, and honor `NO_COLOR` / dumb terminals / piped output. The final
emit goes through `builtins.print`, so tests keep patching the same seam.
Status, objectives, inventory, and the `saves` listing render as Rich
panels/tables via `_print_renderable`; the AI spinner is `console.status`;
dreams go through `write_narrative` (paragraph pacing, toggled with `pace on`).

## Tier 3A — prompt_toolkit input layer (recommended next, ~1–2 weeks)

- Replace `input()` in `terminal.read_line` with `prompt_toolkit.PromptSession`.
- Persistent up-arrow command history (gitignored history file), complementing `!!`.
- Tab completion fed by `CommandHandler._build_intent_context()`:
  commands from `COMMAND_SYNONYMS`, then NPC names after `talk to`, items after
  `take`/`look at`/`use`, exits after `move to`. Biggest discoverability win available.
- Bottom toolbar showing Day/Period/Location/state, freeing the turn header entirely.
- Coexists with Rich (input vs output ownership); PyInstaller-clean.

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

## Discovered during implementation

- **Interactive save/load picker.** `saves` lists slots in a table, but `load`
  still takes a typed slot name. A numbered picker reusing
  `numbered_actions_context` would close the loop.
- **Hanging indent for dialogue.** NPC lines wrap to column 0; a hanging indent
  under the speaker name would read better. Needs per-line indent support in
  `terminal.write_line` (Rich `Padding` or `Text` with `pad`).
- **Conversation history sub-command (`history` inside `talk to`) still uses
  `--- … ---` headers**; restyle with a dim Rich panel for consistency.
- **`display_help` is still a flat aligned list** (65-char column). A Rich
  table grouped by category would scan better, and the column width overflows
  at narrow terminal widths.
- **Endings/scripted events don't use `write_narrative`** yet — only dreams do.
  Worth routing major `event_manager` narration through `_print_narrative`.
- **`pace` is not persisted** in save files (theme/verbosity are). Add it to
  `save_game`/`load_game` if it should survive restarts.
- **`SPINNER_FRAMES` and `SEPARATOR_LINE` in `game_config.py` are now unused**
  (the spinner is Rich's, separators are width-aware via `terminal.separator()`).
  Remove once nothing external references them.
- **`blessed` is still in `requirements.txt`** but unused in production code
  (only two standalone test scripts import it). Drop it and the two scripts.
- **API-key prompt loop**: with piped/EOF input the interactive key prompt
  re-asks until EOFError. Should detect non-TTY stdin and fall back to skip.
- **`look at [item]` numbered entries**: scene items map to `select_item`
  (prompting "what to do with…"); a dedicated examine number was removed in the
  compact listing. Consider `N. item` = examine, with take/use via words.
