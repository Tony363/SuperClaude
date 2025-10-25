# Session Management (Stub)

SuperClaude supports persistent workspaces through the UnifiedStore and the
worktree manager. While the comprehensive guide returns, rely on these assets:

- [Worktree manager module](../../SuperClaude/WorktreeManager/__init__.py)
- [UnifiedStore module](../../SuperClaude/Core/unified_store.py)
- [Core rules](../../SuperClaude/Core/OPERATIONS.md) — session save/load
  workflows.

## Quick Actions

- `/sc:save` — Persist the current session (see `SuperClaude/Commands`).
- `/sc:load <session>` — Restore a saved workspace.
- `SuperClaude/Core/CLAUDE_EXTENDED.md` — outlines session-aware behaviours.

Security hardening tips are covered in the main [Security policy](../../SECURITY.md).

### Migrating From Serena JSON

If legacy `~/.claude/serena_memory.json` files still exist, run:

```
python -m SuperClaude.Core.migrate_serena_data
```

The UnifiedStore emits a console warning when the JSON file remains but the
SQLite database is empty. Migration backs up the JSON file (adds
`serena_memory.json.backup`) so you can verify the new store before removing
Serena artifacts.
