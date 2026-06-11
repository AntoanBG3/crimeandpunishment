---
name: run-crimeandpunishment
description: Run, play, smoke-test, or screenshot the Crime and Punishment terminal text adventure — scripted piped sessions, tmux captures of the classic console and the Textual TUI, test suite and lint commands.
---

# Run: Crime and Punishment

Terminal text adventure (Python, `rich` + `prompt_toolkit` + optional
`textual` TUI). Gemini-powered at runtime but **fully playable with no API
key**: piped stdin puts it in deterministic LOW-AI placeholder mode, which is
exactly what an agent wants. All paths below are relative to the repo root.

The driver is `.claude/skills/run-crimeandpunishment/driver.sh`. It is the
primary agent path — use it before reaching for `python main.py` directly.

## Prerequisites

- Python venv at `.venv` (Python 3.13) with deps installed:
  `.venv/bin/pip install -r requirements.txt`
  (driver falls back to `python3` if `.venv` is missing).
- `tmux` for the interactive/TUI captures (`/opt/homebrew/bin/tmux` here).

There is no build step.

## Run (agent path)

```bash
# End-to-end scripted run, asserts key markers, exit code 0/1:
.claude/skills/run-crimeandpunishment/driver.sh smoke

# Play your own commands (new game as Raskolnikov, LOW-AI, quits cleanly):
.claude/skills/run-crimeandpunishment/driver.sh play "look" "move to stairwell" "talk to nastasya" "hello" "goodbye"

# Text "screenshots" of the real interactive surfaces (via tmux):
.claude/skills/run-crimeandpunishment/driver.sh console-shot   # prompt_toolkit console -> /tmp/cp_console.txt
.claude/skills/run-crimeandpunishment/driver.sh tui-shot       # Textual TUI -> /tmp/cp_tui.txt
```

`smoke` pipes a full session (character select → look → objectives → move →
conversation → quit) and greps for markers like "Choose Your Character" and
"Exiting game. Goodbye.". `play` prints the whole transcript; inside a
`talk to` conversation, lines are free-form dialogue until `goodbye`/`leave`.

The `*-shot` modes launch the game in a 100x30 tmux pane, decline the API
key, pick Raskolnikov, run `look`, and `capture-pane` to a file. Verify the
capture shows the scene listing and the status line
(`Day 1, Morning · Raskolnikov's Garret · … · LOW-AI`), not an error.

## Run (human path)

```bash
.venv/bin/python main.py           # Textual TUI (the default in a TTY)
.venv/bin/python main.py --no-tui  # classic console
```

Interactive: prompts for a Gemini API key on first run (type `skip` for the
static-fallback mode), then character selection. Useless when piped — use the
driver for that.

## Test / lint

```bash
.venv/bin/python -m unittest discover tests   # canonical; ~325 tests, ~5s
.venv/bin/flake8 . && .venv/bin/pylint game_engine  # both kept at clean/10.00
```

## Gotchas

- **TTY changes behavior.** Piped stdin: API-key prompt auto-skips to
  placeholder mode, plain `input()`. Real TTY (tmux): the key prompt is
  interactive and loops until you type `skip`, and input goes through
  prompt_toolkit. The driver handles both; remember the difference if you
  drive it by hand.
- **Don't set `GEMINI_API_KEY`** for deterministic runs — it triggers a live
  network probe at startup and switches the game to AI mode.
- **`talk to` enters a dialogue sub-loop.** Game commands typed there are
  spoken to the NPC, not executed. Exit with `goodbye`, `leave`, or two empty
  lines.
- **`quit` asks "Save before quitting? (y/N)"** — scripted sessions must
  answer it (the driver sends `n`).
- **Character picker accepts only 1–3** (Raskolnikov / Sonya / Porfiry).
  Invalid lines just re-prompt; a script that mis-counts its input lines
  burns the rest of stdin in that loop and the game exits on EOF.
- Runs write `savegame_autosave.json` (and `savegame.json` if you save) into
  the repo root; both are gitignored.

## Troubleshooting

- **"No API key entered. Please provide a key or type 'skip'."** looping in
  tmux — you sent an empty line to the interactive key prompt. Send `skip`.
- **"Invalid input. Please enter a number." repeating** in a piped run — your
  scripted lines are misaligned with the prompts; the picker is eating game
  commands. Recount: first line blank (skip load), then `1`, then commands.
- **tmux capture is blank or mid-boot** — the fixed `sleep`s in the driver
  (3s boot, ~1–2s per step) are tuned for this machine; bump them on slower
  ones.
