# Decisions Log

## 2025-11-03 – Fast Codex Implementation Path
- **Context:** `/sc:implement` required the full multi-persona stack even for low-risk edits, adding coordination overhead when the goal was a small diff. Product plan `fast-codex-execution-plan.md` targeted a streamlined flag that still honoured `requires_evidence`, telemetry, and MCP guardrails.
- **Decision:** Introduce a `--fast-codex` flag that routes the implement command through a dedicated `codex-implementer` persona, records execution-mode telemetry (`commands.fast_codex.*`), and falls back to the standard persona cohort when consensus or security flags are present.
- **Consequences:** Quick-edit workflows gain a lighter path while observability and evidence requirements remain intact. Tests cover flag parsing, mode toggling, and guardrail enforcement, and documentation now explains when to prefer the fast mode versus the canonical flow.

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

## 2025-10-28 – Consensus Calibration & Retrieval Grounding
- **Context:** Consensus enforcement and guardrail telemetry existed but defaulted to single-model heuristics without semantic validation or observable alerting. Agents operated without shared retrieval context, encouraging speculative plans.
- **Decision:** Introduced command-specific consensus policies with quorum rules, deterministic offline executors, and semantic validators that block unresolved imports or symbols. Added hallucination telemetry events, CI guard scripts, and repository retriever hooks feeding agents contextual snippets.
- **Consequences:** `/sc:` commands requiring evidence now fail when the ensemble cannot reach quorum, and plan-only spikes trigger monitoring events ready for CI gating. Agents automatically attach repo context before planning, reducing hallucination risk and providing auditable artifacts for reviewers.

## 2025-10-28 – Extended Persona Strategist Priorities
- **Context:** Agent usage telemetry in `.superclaude_metrics/agent_usage.json` shows two extended personas accounting for the overwhelming majority of executed extended flows (`security-engineer` 65 executions, `technical-writer` 14) while several others are frequently loaded but never executed. The strategist rollout path needs clear ordering for Workstream 2.
- **Decision:** Promote the following extended personas to the strategist track in this order: 1) `security-engineer`, 2) `technical-writer`, 3) `accessibility-tester`, 4) `angular-architect`, 5) `api-designer`. The first two convert immediately based on execution counts; the latter three enter a discovery sprint to validate demand before full promotion.
- **Consequences:** Future strategist implementations focus on the highest-impact extended personas, aligning test coverage and telemetry expectations. Documentation and test plans will reference this ordering, and subsequent ADRs will capture promotion criteria for each persona after the discovery sprints.
