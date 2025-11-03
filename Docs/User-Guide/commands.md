# Command Catalogue (Stub)

All `/sc:` commands advertised in the README resolve to the implementations in
`SuperClaude/Commands`. Until the full manual is restored, start here:

- [Operations Manual](../../SuperClaude/Core/OPERATIONS.md) — Priorities, rules,
  and execution guidance for each command group.
- [Command executor module](../../SuperClaude/Commands/executor.py) — Source of
  the CLI dispatcher.

## Using This Stub

- `SuperClaude --help` lists the live command set.
- Each subcommand module inside `SuperClaude/Commands` contains richly
  documented docstrings that mirror the v6 workflow.

### Fast Codex Shortcut
- `/sc:implement --fast-codex` loads the lean `codex-implementer` persona for small, high-confidence diffs.
- Guardrails remain active—if consensus is forced or `--safe` is present, the executor falls back to the
  standard multi-persona implementation path.
- Command results surface `execution_mode` and `fast_codex` payloads so telemetry and automation can
  distinguish fast-mode runs from the canonical workflow.

Future updates will expand this file with walkthroughs, examples, and advanced
scenarios without breaking existing links.
