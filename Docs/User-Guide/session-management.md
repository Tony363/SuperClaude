# Session Management (Stub)

SuperClaude supports persistent workspaces through Serena MCP and the
worktree manager. While the comprehensive guide returns, rely on these assets:

- [Worktree manager module](../../SuperClaude/WorktreeManager/__init__.py)
- [Serena integration](../../SuperClaude/MCP/__init__.py)
- [Core rules](../../SuperClaude/Core/OPERATIONS.md) — session save/load
  workflows.

## Quick Actions

- `/sc:save` — Persist the current session (see `SuperClaude/Commands`).
- `/sc:load <session>` — Restore a saved workspace.
- `SuperClaude/Core/CLAUDE_EXTENDED.md` — outlines session-aware behaviours.

Security hardening tips are covered in the main [Security policy](../../SECURITY.md).
