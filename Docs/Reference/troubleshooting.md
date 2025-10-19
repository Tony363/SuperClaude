# Troubleshooting (Stub)

Quick resources while the full troubleshooting matrix is rebuilt:

- [Critical rules and safeguards](../../SuperClaude/Core/RULES_CRITICAL.md)
- [Operations guide](../../SuperClaude/Core/OPERATIONS.md) — includes common
  failure modes.
- [Updater utilities](../../setup/utils/updater.py) — diagnose installation and
  upgrade problems.

## Rapid Checks

1. `SuperClaude doctor` — run the CLI health check (see `SuperClaude/Commands`).
2. `pytest -q` — run the bundled smoke tests.
3. Consult the [Quality Scorer](../../SuperClaude/Core/RULES_RECOMMENDED.md) to
   interpret automated feedback.

Community contributed fixes and FAQs will surface here as documentation
re-populates.
