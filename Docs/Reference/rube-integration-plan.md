# Rube MCP Integration Roadmap

- **Author:** Codex
- **Date:** 2025-10-26
- **Goal:** Promote Rube MCP from opt-in stub to a first-class automation layer within SuperClaude.

## Milestones

- [x] **M1 — Default Enablement & Connector Upgrade**
  - Enable `rube` by default in `SuperClaude/Config/mcp.yaml` and remove the opt-in env toggle.
  - Update `_activate_mcp_servers` so Rube behaves like other servers (only skip when `enabled: false` or network disallowed).
  - Replace `RubeProxyIntegration` with a real HTTP client wrapper that can execute basic MCP requests (with a dry-run fallback when offline).
  - Expand unit tests in `tests/test_mcp_servers.py` to cover success, failure, and dry-run paths.

- [x] **M2 — Command & Persona Wiring**
  - Add `rube` to the MCP requirements of automation-ready commands (`task`, `workflow`, `spawn`, `improve`, `business-panel`, etc.).
  - Provide a shared dispatcher (e.g., `CommandExecutor._dispatch_rube_actions`) that translates command context into Rube tool invocations when available.
  - Update key persona playbooks (DevOps, QA, Technical Writer) with guidance on using Rube for external workflows.
  - Ensure command results record Rube operations inside `executed_operations` and surface user-facing feedback on success or failure.

- [x] **M3 — Documentation, Telemetry, and Developer Tooling**
  - Document credential setup, dry-run mode, and supported integrations in README + user guide.
  - Emit telemetry counters such as `commands.rube.success`, `commands.rube.failure`, and `commands.rube.dry_run` via `PerformanceMonitor`.
  - Add integration tests exercising at least one command path with Rube mocked out.
  - Update installer/uninstaller scripts to treat Rube as a core server and warn when credentials are absent.

## Notes

- Treat `SC_NETWORK_MODE` as the primary offline guard; introduce `SC_RUBE_MODE=dry-run` for safe testing.
- Credentials should be read from configuration for now, but code should expose hooks for plugging in a secure vault later.
- All external calls must raise clear, actionable errors when credentials are missing or Rube is unreachable.
