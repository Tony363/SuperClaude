# Testing & Debugging (Stub)

Testing discipline is encoded directly in the core materials:

- [Operations manual](../../SuperClaude/Core/OPERATIONS.md) — quality gates and
  escalation paths.
- [Rules (critical)](../../SuperClaude/Core/RULES_CRITICAL.md) — non-negotiable
  safeguards.
- [Rules (recommended)](../../SuperClaude/Core/RULES_RECOMMENDED.md) — tooling
  advice and coverage expectations.

## Current Workflow

1. Run `pytest -q` or `python benchmarks/run_benchmarks.py --suite full`.
2. Capture debugging notes in spec tasks or ADRs.
3. For MCP-driven debugging, consult
   [`SuperClaude/Core/TOOLS.md`](../../SuperClaude/Core/TOOLS.md).

Expanded guides with debugger recipes, tracing instrumentation, and CI
integration notes will populate this page as documentation is regenerated.
