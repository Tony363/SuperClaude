# Real Integrations Status (November 2025)

All items from the original roadmap have shipped. This document now serves as a
living status report plus ideas for future hardening. The sections capture the
current implementation, remaining risks, and optional follow-up experiments.

## CLI Setup Bootstrap (`SuperClaude/__main__.py`)
- **Current state:** the entry point attempts an editable install automatically
  and exits with explicit guidance when imports fail.
- **What to monitor next:** surface aggregated telemetry about bootstrap
  failures to spot flaky environments sooner.
- **Nice-to-have:** add a smoke test that runs the bootstrap flow inside the
  benchmark harness’s virtualenv job.

## Rube MCP (Native Tools)
- **Current state:** MCP functionality is now accessed via Claude Code's native
  tools (`mcp__rube__*`). No custom HTTP wrapper is needed.
- **What to monitor next:** usage patterns of native MCP tools in command flows.
- **Nice-to-have:** add command-level telemetry for MCP tool invocations.

## Token Accounting (`SuperClaude/Monitoring/performance_monitor.py`)
- **Current state:** every provider invocation updates cumulative counters and
  writes token events to registered sinks.
- **What to monitor next:** pipe the aggregate counters into the CLI summary so
  local operators can spot spikes without digging into JSONL files.
- **Nice-to-have:** expose Prometheus-friendly gauges when the daemon runs
  inside long-lived automation.

## Evidence & Stub Handling (`SuperClaude/Commands/executor.py`)
- **Current state:** the executor now differentiates between true stubs and
  actionable follow-ups, queuing `commands.followup` metrics when automation
  cannot produce evidence.
- **What to monitor next:** add dashboards for queued follow-ups versus
  auto-applied stubs to detect stale automation debt.
- **Nice-to-have:** expire follow-ups automatically once a human resolves the
  referenced plan.

## Plan-Only Agents (`SuperClaude/Agents/*`)
- **Current state:** plan-only responses are treated as failure modes; repeated
  occurrences raise telemetry and trigger follow-ups.
- **What to monitor next:** correlate plan-only rates with specific personas to
  decide where to invest in deeper implementations.
- **Nice-to-have:** allow command authors to register remediation scripts for
  frequent plan-only scenarios.

## Health Probes (`SuperClaude/Testing/integration_framework.py`)
- **Current state:** components default to “unknown” until real probes validate
  readiness; CI fails when expected probes are missing.
- **What to monitor next:** add synthetic probes for MCP servers so we can
  detect credential drift ahead of production incidents.
- **Nice-to-have:** push probe results to the same telemetry sink as token
  events to simplify dashboards.

## Cross-Cutting Practices
1. **Contract clarity:** keep behaviour documents close to the code to reduce
   drift; update them alongside interface changes.
2. **Progressive rollout:** continue using feature flags or staged env toggles
   when integrations expand.
3. **Observability first:** extend structured logging to new automation paths
   before rolling them out.
4. **Fail loud and early:** prefer surfaced errors over silent fallbacks so
   operators can triage quickly.
5. **Secrets hygiene:** centralise API key retrieval and ensure dry-run paths
   never log sensitive material.
6. **Testing strategy:** pair sandbox calls with deterministic contract tests
   to keep coverage without increasing flakiness.
