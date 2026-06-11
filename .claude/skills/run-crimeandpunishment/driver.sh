#!/bin/bash
# Driver for the Crime and Punishment text adventure.
# Usage:
#   driver.sh smoke                 — scripted end-to-end run (non-TTY path), asserts markers
#   driver.sh play "cmd1" "cmd2" …  — scripted run with your own commands, prints transcript
#   driver.sh tui-shot [outfile]    — launch the Textual TUI in tmux, capture a text "screenshot"
#   driver.sh console-shot [outfile]— same for the classic console (prompt_toolkit path)
set -u
cd "$(dirname "$0")/../../.." || exit 1
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3

_script_run() {
  # Args become game commands, one per line. Always starts a new game as
  # Raskolnikov (blank line skips load, "1" picks him) and answers the
  # quit-save prompt with n. Piped stdin -> LOW-AI placeholder mode, plain
  # input(): fully deterministic, no API key, no TTY needed.
  { printf '\n1\n'; printf '%s\n' "$@"; printf 'quit\nn\n'; } | "$PY" main.py 2>&1
}

case "${1:-smoke}" in
  smoke)
    out=$(_script_run "look" "objectives" "move to stairwell" "talk to nastasya" "hello" "goodbye" "journal")
    status=0
    for marker in "Choose Your Character" "Raskolnikov's Garret" "Your Objectives" \
                  "You approach Nastasya" "Exiting game. Goodbye."; do
      if ! grep -q "$marker" <<<"$out"; then
        echo "MISSING MARKER: $marker"
        status=1
      fi
    done
    if [ $status -eq 0 ]; then
      echo "SMOKE OK ($(wc -l <<<"$out" | tr -d ' ') lines of transcript)"
    else
      echo "--- transcript tail ---"; tail -40 <<<"$out"
    fi
    exit $status
    ;;
  play)
    shift
    _script_run "$@"
    ;;
  tui-shot|console-shot)
    mode=$1
    out=${2:-/tmp/cp_${mode%-shot}.txt}
    session=cp_drive_$$
    # TUI is the default in a TTY; the console capture must opt out.
    if [ "$mode" = tui-shot ]; then
      tmux new-session -d -s "$session" -x 100 -y 30 "$PY main.py --tui"
    else
      tmux new-session -d -s "$session" -x 100 -y 30 "$PY main.py --no-tui"
    fi
    sleep 3
    # In a real TTY the API-key prompt is interactive (no auto-skip): decline it.
    tmux send-keys -t "$session" "skip" Enter
    sleep 1
    tmux send-keys -t "$session" "" Enter   # skip load prompt
    sleep 1
    tmux send-keys -t "$session" "1" Enter  # pick Raskolnikov
    sleep 2
    tmux send-keys -t "$session" "look" Enter
    sleep 2
    tmux capture-pane -t "$session" -p > "$out"
    tmux kill-session -t "$session" 2>/dev/null
    echo "captured: $out"
    head -5 "$out"
    ;;
  *)
    echo "usage: driver.sh smoke | play <cmds…> | tui-shot [out] | console-shot [out]"; exit 2
    ;;
esac
