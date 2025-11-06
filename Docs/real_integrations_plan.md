# Real Integrations Roadmap

## CLI Setup Fallbacks (`SuperClaude/__main__.py:53-64`)
- Replace print-only shims with a bootstrap check that installs required setup assets or exits with actionable instructions.
- **Best practices:** fail fast when dependencies are missing, add integration tests that bootstrap the CLI in a clean virtual environment, and ensure logging always flows through the standard logger stack.
- **Pros:** predictable logging, easier support.
- **Cons:** stricter startup can frustrate rapid prototyping unless you ship a one-command fixer.

## Rube MCP Dry-Run Responses (`SuperClaude/MCP/rube_integration.py:133-140`)
- Keep dry-run as an explicit test-only mode, but implement live HTTP calls with retries, structured error mapping, and telemetry.
- **Best practices:** feature flags, contract tests against a sandbox MCP server, exponential backoff, and request-level observability.
- **Pros:** unlocks real workflows, accurate telemetry.
- **Cons:** introduces network brittleness, demands secret management and rate limiting.

## Token Metrics Stub (`SuperClaude/Monitoring/performance_monitor.py:177-184`)
- Feed true usage data from token counters and model responses; persist running aggregates.
- **Best practices:** centralize token accounting, expose async hooks that increment counters, and backfill historical metrics to avoid graph discontinuities.
- **Pros:** trustworthy performance dashboards, better capacity planning.
- **Cons:** plumbing through every model path raises coupling and needs strong regression tests.

## Auto-Generated Implementation Stubs (`SuperClaude/Commands/executor.py:1724-2044`)
- Replace blanket stub emission with capability negotiation so artifacts only appear when the command genuinely cannot execute.
- **Best practices:** add a “requires_followup” queue, track stub aging, surface unresolved items in CI dashboards, and require owner acknowledgement before release.
- **Pros:** clearer signal on unfinished work, less placeholder drift.
- **Cons:** higher engineering overhead, slower perceived responsiveness when automation must pause.

## Plan-Only Agent Outputs (`SuperClaude/Agents/generic.py:45-125`, `SuperClaude/Agents/core/general_purpose.py:250-318`)
- Invest in minimal viable implementations or enforce delegation to specialists that can act; treat plan-only as an explicit failure mode.
- **Best practices:** calibrate capability scoring thresholds with telemetry, auto-escalate repeated plan-only responses, and write unit tests that demand concrete actions for common scenarios.
- **Pros:** richer automation, better user trust.
- **Cons:** increases agent complexity, risks partial actions without strong safeguards.

## Health Check Mock (`SuperClaude/Testing/integration_framework.py:503-519`)
- Require real probes, default to “unknown” rather than “healthy,” and document the contract each component must satisfy.
- **Best practices:** define a response schema, fail CI when a component lacks a probe, and add synthetic canaries to validate the probe pipeline.
- **Pros:** early fault detection, meaningful dashboards.
- **Cons:** component teams must author probes, more noisy failures during rollout.

## Cross-Cutting Best Practices
1. **Contract clarity:** document expected behavior (and error modes) before replacing mocks; run contract tests whenever the integration surface changes.
2. **Progressive rollout:** use feature flags or staged environments to catch regressions while real integrations harden.
3. **Observability first:** log structured events, emit metrics, and propagate trace IDs before shipping live integrations.
4. **Fail loud and early:** drop silent fallbacks; surface missing dependencies or live-call failures in telemetry and user-visible status.
5. **Security and secrets hygiene:** centralize API keys, rotate credentials, and ensure mocks never log secrets.
6. **Testing strategy:** pair live-integration tests (against sandboxes) with deterministic contract tests to maintain coverage without flakiness.
