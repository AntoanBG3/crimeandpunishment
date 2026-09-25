# Feature commit checkpoints

Commit each completed, verified feature before beginning another. Keep each fix or
feature with its tests, review the staged diff, and write a descriptive message.
When pushing is authorized, publish small batches of completed features.

The repository's `.codex/hooks.json` configures two command hooks:

- `SessionStart` supplies the feature-commit policy, including after compaction.
- `Stop` checks Git status, including untracked files, and requests one continuation
  to review outstanding work for a commit. A repeated stop passes through so user
  changes, failed checks, or unavailable permissions cannot cause a loop.

The script only reads Git status. The agent decides which changes belong together,
runs appropriate checks, and creates the commits. It never blindly stages files or
automatically pushes. Plan mode skips the hooks' feedback. A dirty tree can include
pre-existing user work, so the checkpoint asks for review rather than requiring a
clean tree. This is a workflow reminder, not a Git size limit or a guarantee that
every feature boundary will be detected.

## Activation

Open a new Codex session in this repository and review/trust the two project hooks.
In the Codex CLI, use `/hooks`. Codex requires trust for the project configuration
and the current hook definitions before running them; changes may require review
again. Do not bypass hook trust. The configuration uses `python3` and Git, with no
third-party Python dependencies. Windows requires a shell supporting the configured
command (for example Git Bash or WSL).

See the [official hook documentation](https://learn.chatgpt.com/docs/hooks).

## Verification

```bash
.venv/bin/python -m unittest tests.test_feature_commit_hook
```

These tests use temporary Git repositories and exercise clean, modified, staged,
untracked, ignored, and repeated-stop states without touching project history.
