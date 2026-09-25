"""Remind Codex to checkpoint completed features without blindly staging files."""

import json
import subprocess
import sys


COMMIT_POLICY = (
    "Follow AGENTS.md: after each completed feature or independent fix, run the "
    "relevant checks, review the diff, and commit only that feature's files or hunks "
    "before starting the next feature. Keep tests with their implementation. "
    "Preserve unrelated and pre-existing user edits. Do not commit unfinished or "
    "failing work. Honor explicit instructions not to commit. When pushing is "
    "authorized, use small feature batches; do not push without authorization."
)


def response_for(event):
    """Return hook feedback; never mutate the index, worktree, or remote."""
    if event.get("permission_mode") == "plan":
        return {}
    event_name = event.get("hook_event_name")
    if event_name == "SessionStart":
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": COMMIT_POLICY,
            }
        }
    if event_name != "Stop" or event.get("stop_hook_active"):
        return {}

    cwd = event.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        return {"systemMessage": "Feature commit check skipped: missing working directory."}
    try:
        status = subprocess.run(
            ["git", "--no-optional-locks", "status", "--porcelain", "--untracked-files=normal"],
            cwd=cwd, capture_output=True, check=False, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"systemMessage": "Feature commit check could not inspect Git status."}
    if status.returncode:
        return {"systemMessage": "Feature commit check skipped: Git status failed."}
    if not status.stdout:
        return {}
    return {
        "decision": "block",
        "reason": (
            "Uncommitted changes remain. Before finishing, review whether this task "
            "has completed, verified work that should be committed. " + COMMIT_POLICY +
            " If only unrelated user changes remain, the work is incomplete, checks "
            "fail, committing is blocked, or the user requested no commit, leave the "
            "files intact and report that instead. This is a single review checkpoint; "
            "do not manufacture a commit or bypass permissions to make the tree clean."
        ),
    }


def main():
    """Read one lifecycle event from stdin and return valid JSON on stdout."""
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("Expected an event object")
    except (ValueError, UnicodeError):
        print(json.dumps({"systemMessage": "Feature commit check received invalid JSON."}))
        return
    print(json.dumps(response_for(event)))


if __name__ == "__main__":
    main()
