# Behavioral Flags (Stub)

SuperClaude commands honour a rich flag set for tailoring behaviour. Detailed
descriptions, precedence, and examples live in the core assets:

- [Flag reference](../../SuperClaude/Core/FLAGS.md)
- [Rules and priorities](../../SuperClaude/Core/RULES.md)
- [Critical safeguards](../../SuperClaude/Core/RULES_CRITICAL.md)

## Quick Tips

- Combine `--delegate`, `--loop`, and `--consensus` to activate multi-agent
  orchestration.
- The `SuperClaude/Core/CLAUDE_CORE.md` profile shows which flag bundles load by
  default.
- Use `--fast-codex` with `/sc:implement` for quick, Codex-style diffs—telemetry captures the
  execution mode and guardrails automatically revert to the standard persona stack when risk flags (e.g.,
  `--safe`, forced consensus) are present.

This page will grow into the full flag matrix while providing immediate access
to the current specification.
