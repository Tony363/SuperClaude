# Rube MCP Option A Implementation Plan *(legacy)*

- **Author:** Codex  
- **Date:** 2025-10-26  
- **Scope:** Adds an optional remote connector for the Composio Rube MCP server that remains disabled by default and only activates when operators opt in to online mode.

## Background

> **Note:** This document captured the initial opt-in spike for Rube MCP. The connector is now first-class; see `Docs/Reference/rube-integration-plan.md` for the active roadmap.

SuperClaude currently supports local-first MCP integrations (Zen). Rube MCP expands capabilities by brokering hundreds of SaaS tools via a hosted endpoint. Because the active Anti-Hallucination Guardrails spec keeps the framework offline by default, the integration must:

1. Stay opt-in and respect an explicit environment toggle.
2. Fail safely when network access is unavailable.
3. Surface documentation so operators understand prerequisites and risks.

## Dependencies

- Guardrail work (HALL-001/HALL-002) remains prioritized but does not block adding a disabled connector.
- Rube MCP endpoint (`https://rube.app/mcp`) and Composio OAuth flow; requires external network connectivity when enabled.
- Python HTTP client (`httpx`) already declared in dependencies (confirm before use) or fallback to standard libraries.

## Milestones

- [x] **M1 — Configuration Gate:** Add a `rube` entry to `SuperClaude/Config/mcp.yaml` with `enabled: false` and `requires_network: true`. Update executor logic to skip activation unless config enabled *and* environment variable `SC_MCP_RUBE_ENABLED=true` is set.
- [x] **M2 — Connector Implementation:** Create `SuperClaude/MCP/rube_proxy.py` exposing `RubeProxyIntegration`. Provide lazy session creation that validates the opt-in flag, builds the MCP request envelope, and currently stubs actual network calls with informative errors if invoked offline.
- [x] **M3 — Registry & Config Wiring:** Register the new integration in `SuperClaude/MCP/__init__.py`, expose it through `MCP_SERVERS`, and ensure configuration maps optional parameters (endpoint URL, OAuth token placeholder).
- [x] **M4 — Tests & Telemetry:** Add unit tests in `tests/test_mcp_servers.py` covering opt-in gating (enabled/disabled) and verify the executor logs a skip warning when disabled. Extend telemetry stub to count skip events via logging (no metric change yet).
- [x] **M5 — Documentation & Usage Notes:** Document the opt-in flow in this plan and append a short section to `README.md` describing how to enable the connector along with security cautions.

## Acceptance Criteria

- Default runs behave exactly as before (no new network calls, no config errors).
- Setting `SC_MCP_RUBE_ENABLED=true` and adding credentials allows the connector to initialize; when disabled, activation is skipped with a clear log message.
- Tests pass locally (`pytest tests/test_mcp_servers.py`).
- Documentation explains prerequisites, toggles, and fallback behaviour.

## Risks & Mitigations

- **Network sandbox**: If the runtime forbids network, the connector raises a descriptive error. Mitigation: guard by opt-in flag and explicit error messaging.
- **Credential handling**: Placeholder for OAuth tokens stored via existing secrets file until a dedicated vault is defined.
- **Scope creep**: Option A deliberately avoids full workflow changes; future phases will iterate once guardrails ship.

## Rollback Plan

Revert the configuration entry, remove the new integration file, and delete documentation references. No migrations or persistent state changes are introduced, so rollback is low risk.
