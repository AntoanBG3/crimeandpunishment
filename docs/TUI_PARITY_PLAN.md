# TUI Parity Plan — making `--tui` the default

> **Status (2026-06-10): complete — the TUI is the default.** W1–W6 landed
> (Tab completion, shared persistent history, `main.choose_mode()` with the
> non-TTY gate, atomic saves, thread-joining exit, masked API key prompt,
> backend-protocol contract tests), and W7 flipped `DEFAULT_MODE` to
> `"tui"`. `--no-tui` / `CRIME_TUI=0` opt out; non-TTY streams always get
> the classic console. One external checklist item remains: PyInstaller
> builds now need `--collect-all textual` unconditionally.

Goal: bring the Textual TUI to feature parity with the classic console so the
default mode can flip from console to TUI without regressing anything the
README advertises. The flip itself is the last step and is gated on the exit
criteria at the bottom; until then the TUI stays opt-in.

This continues `TIER3_PLAN.md` § 3B, whose "deliberately deferred polish"
(completion in the Textual `Input`, command palette, richer sidebar) is
exactly the debt this plan pays down — plus the robustness gaps that only
matter once every player hits the TUI path first.

## Parity audit

What the console does today vs. what the TUI does, feature by feature.
"OK" means parity already holds or the TUI behavior is an acceptable,
documented equivalent.

| Feature | Console | TUI today | Verdict |
|---|---|---|---|
| Tab completion (commands + scene targets) | `GameCompleter` via `PromptSession` | none | **Gap — W1** |
| Command history, persistent across sessions | `FileHistory(~/.crimeandpunishment_history)`, ↑/↓ | none | **Gap — W2** |
| Free-form dialogue input (`completion=False`) | completer suppressed in conversation loop | flag never crosses the backend seam | **Gap — W1** |
| Non-TTY / piped operation | degrades to plain `print`/`input` | Textual cannot run without a TTY | **Gap — W3** (fallback in `main.py`) |
| Graceful quit (Ctrl+C / Ctrl+Q) | `KeyboardInterrupt` caught at loop level | `_QUIT` sentinel only unwinds a thread blocked in `read()`; daemon thread can die mid-autosave | **Gap — W4** |
| API key entry | echoed by `input()` (pre-existing wart) | echoed *and* preserved in the scrollable log | **Gap — W5** (fix both modes) |
| Live status line | prompt_toolkit bottom toolbar | status bar widget (same provider) | OK |
| AI "thinking" indicator | Rich spinner | status-bar message | OK |
| Turn-header suppression | `toolbar_active()` | `toolbar_active()` returns True with a backend | OK |
| Paging of tall renderables | system pager | pane scrolls (Textual owns the keyboard) | OK — document as intentional |
| `clearscreen on` | real terminal clear | dim `Rule` in the log | OK — scrollback is a TUI feature; document |
| `pace` paragraph reveal | sleeps between paragraphs | same (game thread sleeps; output crosses incrementally) | OK — verify under `run_test()` in W6 |
| `NO_COLOR` / dumb terminals | honored by `terminal.py` | Textual manages color itself | OK |

## W1 — Tab completion in the Textual `Input`

The completion *logic* is already UI-agnostic in spirit; only its packaging is
prompt_toolkit-shaped. Refactor, don't reimplement:

1. Extract the core of `GameCompleter.get_completions` into a pure function in
   `completion.py`, e.g. `completion_candidates(text_before_cursor, context)
   -> list[tuple[candidate, start_position]]`, with `_command_words()` and
   `_ARGUMENT_POOLS` unchanged. `GameCompleter` becomes a thin
   prompt_toolkit wrapper over it, so the existing
   `tests/test_completion.py` fixtures keep passing untouched.
2. In `tui_app.py`, bind Tab on the `Input` widget to a cycling completer:
   first Tab computes `completion_candidates(...)` using the same provider
   the console registers (`terminal._completer_provider` — expose it via a
   small `terminal.completer_context()` accessor rather than reaching into
   the module's privates), replaces the partial word with the first
   candidate, and subsequent Tabs cycle; any other key resets the cycle
   state. No new dependency, no dropdown widget needed for parity (the
   console completer is also a flat candidate list).
3. Carry the `completion` flag across the seam: `read_line(...,
   completion=False)` (the conversation loop) must disable Tab completion in
   the TUI too. Change the backend protocol to
   `read(prompt_text, completion=True)`; update `TextualBackend`, the fake
   backend in `tests/test_tui.py`, and the docstring contract in
   `terminal.py`. The protocol is internal, so no compatibility shim.

Optional, after parity (not gating): a Textual `Suggester` for inline ghost
text, and the command palette fed by `COMMAND_SYNONYMS` from the original
3B design. Nice-to-haves, explicitly out of scope here.

## W2 — Command history in the TUI

Share the console's persistent history rather than inventing a second store:

1. Move the history file path into a single constant (it already is:
   `terminal.HISTORY_FILE`) and add two tiny helpers in `terminal.py`:
   `load_history_lines()` and `append_history_line(line)`. Implement them to
   read/append the same plain-lines format `prompt_toolkit.FileHistory`
   uses (`FileHistory` stores `# timestamp` comment lines and `+`-prefixed
   entry lines — match it exactly so both modes share one file; add a unit
   test that round-trips a file written by `FileHistory` itself).
2. In `CrimeAndPunishmentApp`, keep an in-memory list seeded from
   `load_history_lines()` at mount. Bind ↑/↓ on the `Input` to walk it
   (preserving the partially typed line at the bottom of the walk, the way
   prompt_toolkit does); on `Input.Submitted`, append non-empty lines to the
   list and to the file via `append_history_line`.
3. Skip recording dialogue-mode lines if and only if the console skips them
   (it does not — `PromptSession` records everything; keep parity and record
   everything except empty lines).

## W3 — Mode decision and non-TTY fallback in `main.py`

The flip mechanics, built and tested *before* the default changes:

1. Replace `_tui_requested()` with a `_choose_mode() -> "tui" | "console"`
   that considers, in order: explicit `--no-tui` or `CRIME_TUI=0` → console;
   explicit `--tui` or `CRIME_TUI=1` → tui (with the existing warning +
   console fallback if `textual` is missing); otherwise the *default*,
   which stays `console` until the final flip commit changes one line.
2. Hard gate regardless of request: if `not (sys.stdin.isatty() and
   sys.stdout.isatty())`, always console. This preserves the piped/CI/script
   path that `terminal.py` already degrades for, and it means the eventual
   default flip cannot break `python main.py < commands.txt`.
3. Extract the decision into an importable function (module-level in
   `main.py` is fine) so `tests/` can unit-test the matrix: flags × env var ×
   TTY-ness × textual importability, with `unittest.mock.patch` on
   `sys.argv`, `os.environ`, `isatty`, and `importlib.util.find_spec`.

## W4 — Shutdown that cannot corrupt a save

Two independent fixes, both cheap:

1. **Atomic saves** (benefits both modes): in `Game.save_game`
   (`game_state.py:199`), write to `save_file + ".tmp"` and `os.replace()`
   onto the real path. A killed thread then leaves at worst a stale temp
   file, never a truncated `savegame_*.json`. Add a test that patches
   `json.dump` to raise mid-write and asserts the original save survives.
2. **Orderly TUI exit**: in `on_unmount` (and the Ctrl+Q action), after
   pushing `_QUIT`, `join` the game thread with a short timeout (~2s) before
   letting the app tear down. The sentinel wakes a thread blocked in
   `read()`; the join covers the thread being mid-turn (e.g. an AI call or
   an autosave). If the join times out, proceed with exit — with atomic
   saves in place the worst case is a lost turn, not a corrupted file.
   Test via `App.run_test()`: submit a command, trigger app exit while the
   fake game loop sleeps, assert the thread observed `EOFError`/join.

## W5 — Mask the API key prompt

1. Add `secret=False` to `terminal.read_line` and to the backend protocol
   (`read(prompt_text, completion=True, secret=False)`).
   - Console interactive path: pass `is_password=True` to
     `PromptSession.prompt`.
   - Console plain path: use `getpass.getpass` when stdin is a TTY but
     prompt_toolkit is unavailable; plain `input()` when piped (nothing to
     mask in a pipe).
   - TUI: set `Input.password = True` for that read, restore after; echo
     `> ********` to the log instead of the raw line.
2. Route the one call site — the manual-key prompt in
   `GeminiAPI.configure()` (`gemini_interactions.py:532`, via its injected
   `_input_color_func`) — through the new flag. `DisplayMixin._input_color`
   grows the same passthrough parameter.

## W6 — Conformance test pass

Beyond the per-workstream tests above, add a parity-focused sweep to
`tests/test_tui.py`:

- A backend-protocol contract test: one fake backend asserting the exact
  signatures `emit / read(prompt, completion, secret) / clear / status`, so
  the next protocol change fails loudly instead of via `TypeError` at
  runtime.
- `App.run_test()` flows for: Tab completion cycling (W1), ↑/↓ history
  including the seeded-from-file case (W2), password echo masking (W5), and
  a `pace`-style multi-paragraph emit to confirm incremental output renders.
- Confirm the suite still never installs a backend implicitly (the
  console-path invariant the whole test suite relies on).

## W7 — Packaging, docs, and the flip itself

Once W1–W6 are merged and a manual smoke pass on macOS + Windows Terminal +
a Linux terminal looks clean:

1. **Flip the default** in `_choose_mode()` (one line) — TUI when
   interactive and `textual` importable; console for `--no-tui`,
   `CRIME_TUI=0`, missing textual, or any non-TTY stream. Keep `--tui`
   accepted as a no-op-but-valid flag so existing instructions don't break.
2. **PyInstaller**: `--collect-all textual` becomes unconditional for all
   three platform builds. The build process lives outside this repo, so this
   is an external checklist item; note the binary-size growth (Textual ships
   CSS/data files) in the release notes.
3. **Docs**: update README (Quick Start, features, the Tab/history line now
   true in both modes), CLAUDE.md (the "classic console remains the
   default" statements in the terminal-seam and TUI sections, and `main.py`'s
   description), `UX_ROADMAP.md`, and the 3B section of `TIER3_PLAN.md` to
   point here.
4. **Release hygiene**: ship one opt-in release ("try the new default with
   `CRIME_TUI=1`") before the flip if there's any audience to speak of;
   otherwise flip directly and note `--no-tui` prominently in the release
   notes.

## Sequencing and exit criteria

Order: W4.1 (atomic saves — standalone, lowest risk) → W3 (mode decision,
default unchanged) → W1 → W2 → W5 → W4.2 → W6 → W7. Each workstream is a
separate commit/PR with its tests; nothing before W7 changes default
behavior, so every step is shippable.

The default flips only when all of these hold:

- Tab completion and ↑/↓ persistent history work in the TUI and share the
  console's history file (W1, W2).
- `python main.py` with piped stdin/stdout runs the console path end to end
  (W3), verified by a test.
- Saves are atomic and TUI exit joins the game thread (W4).
- The API key is masked in both modes (W5).
- `python -m unittest discover tests`, `flake8 .`, and `pylint game_engine`
  are clean; manual smoke pass done on the three desktop platforms.
