# Session Management

SuperClaude can persist work-in-progress so long-running tasks survive CLI or
editor restarts.

## 1. Saving a Session

```bash
python -m SuperClaude /sc:save --name weekly-refactor
```

- The command snapshots the git worktree, change plans, and metrics into the
  UnifiedStore (SQLite at `~/.superclaude/session.db`).
- Use `--notes` to attach a short summary for later.
- Artefacts older than seven days are cleaned up by the `/sc:cleanup` command.

## 2. Listing Sessions

```bash
python -m SuperClaude /sc:load --list
```

The output includes creation timestamps, associated git branches, and whether
the session contains pending change-plan artefacts.

## 3. Restoring a Session

```bash
python -m SuperClaude /sc:load weekly-refactor --cwd ~/projects/my-repo
```

- The executor replays saved artefacts into the target repository and rehydrates
  `.superclaude_metrics/` so quality checks can continue where you left off.
- If the target repository has diverged, the command aborts with instructions to
  resolve conflicts before reloading.

## 4. Automation Tips

- Use `--json` on `/sc:save` to capture session metadata and feed it into CI or
  other tooling.
- Sessions are versioned; re-saving with the same name increments a counter so
  history is preserved.
- The storage backend is pluggable. See `SuperClaude/Core/unified_store.py` for
  extension points.

Keeping sessions tidy ensures telemetry remains useful and prevents accidental
reuse of stale plans.
