# Session Management

SuperClaude persists work-in-progress via automatic artefacts and the top-level
installer CLI. The legacy `/sc:save` and `/sc:load` commands are archived.

## 1. Capture a Snapshot

```bash
SuperClaude backup --create --output ~/backups/superclaude-$(date +%Y%m%d).tar.gz
```

- The helper packages up the workspace plus `.superclaude_metrics/` into a
  tarball. By default it also copies the UnifiedStore database located at
  `~/.claude/unified_store.db`.

## 2. Restore a Snapshot

```bash
SuperClaude backup --restore ~/backups/superclaude-20251026.tar.gz --cwd ~/projects/my-repo
```

- Restores the saved artefacts, change plans, and metrics into the specified
  repository. The command refuses to proceed if the target worktree contains
  uncommitted changes to prevent data loss.

## 3. Automate Checkpoints

- Schedule `SuperClaude backup --create` via cron or a CI pipeline after major
  sessions.
- Store artefacts in a shared location if multiple operators collaborate on the
  same repository.
- Rotate old archives manually or with your storage tooling—fresh runs replace
  the timestamped tarball, but the command will not delete older backups.

## 4. Manual Recovery Tips

- If you only need a metrics rewind, extract `.superclaude_metrics/` from the
  backup tarball and copy it into the workspace.
- To inspect saved sessions without a full restore, use `tar -tf` to list the
  artefacts before extracting.
- Review `SuperClaude/Core/unified_store.py` if you need to redirect the
  UnifiedStore to a different location (network drives, encrypted volumes, and
  so on).

Keeping snapshots tidy ensures telemetry remains useful and prevents accidental
reuse of stale plans.
