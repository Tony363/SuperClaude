# Decisions Log

## 2025-10-17 – MCP Coverage Guardrail
- **Context:** CLI commands and documentation referenced the `morphllm` MCP server, but no integration was registered. New CLI flags (`--think`, `--loop`, `--consensus`, `--delegate`) required end-to-end validation to prevent future regressions.
- **Decision:** Ship a deterministic `MorphLLMIntegration` stub with a packaged recipe catalog and register it in the MCP factory. Added a smoke test that instantiates every enabled MCP server and verifies MorphLLM planning output. Documented runtime requirements for the new flags in the README.
- **Consequences:** Commands that declare `morphllm` now activate without error in offline environments. CI enforces MCP coverage and quality loop/consensus guardrails via targeted pytest runs and the benchmark smoke harness (`python benchmarks/run_benchmarks.py --suite smoke`).

## 2025-10-25 – MCP Simplification & UnifiedStore
- **Context:** Maintaining six local MCP stubs created redundant documentation, extra configuration, and brittle command dependencies. Serena’s JSON persistence also diverged from the desired SQLite-backed storage.
- **Decision:** Retire Context7, Magic, MorphLLM, Playwright, and Serena MCP integrations. Introduce the `UnifiedStore` SQLite backend with a migration helper, and update commands/modes/docs to rely on Sequential, Zen, and Deepwiki only.
- **Consequences:** MCP registry, installer components, and command playbooks now reference a minimal, actively-supported toolset. Session persistence flows through UnifiedStore, and automated tests cover the new storage path (`tests/test_worktree_state.py`).

## 2025-10-25 – Auto-Stub Hygiene & Agent Telemetry
- **Context:** Auto-generated evidence stubs accumulated in `SuperClaude/Implementation/Auto/` with no lifecycle management, and the 131-agent catalog lacked data showing which personas actually execute.
- **Decision:** Add a TTL-based cleanup helper (`/sc:implement --cleanup`) that only removes untouched auto stubs, log safe-skipped files, and surface usage telemetry via `.superclaude_metrics/agent_usage.json` plus `scripts/report_agent_usage.py`.
- **Consequences:** Repositories stay free of stale evidence while preserving active work. The new markdown report highlights “active”, “observed”, and “planned” agents so product owners can prioritise future implementations without editing configuration files.

## 2025-10-26 – Requires-Evidence Guardrail Enforces Real Diffs
- **Context:** `/sc:implement` succeeded with only auto-generated stubs, letting hallucinated change plans satisfy the `requires_evidence` check while still demanding human follow-up.
- **Decision:** Treat auto stubs as plan-only evidence, suppress writing them to the repository, and fail the guardrail until genuine file modifications are applied.
- **Consequences:** Stub guidance still appears in the change plan, but commands now exit with actionable errors and quality failures until developers supply real diffs. Tests cover the new behaviour and README documents the stricter guardrail.
