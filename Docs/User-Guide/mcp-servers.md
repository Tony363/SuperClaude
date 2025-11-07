# MCP Server Integrations

SuperClaude ships with three Model Context Protocol (MCP) servers. This guide
explains how to configure each one and how they behave now that mock fallbacks
have been removed.

## 1. Configuration Overview

- Edit `SuperClaude/Config/mcp.yaml` to enable/disable servers or to override
  endpoints.
- The CLI honours `SC_NETWORK_MODE`. Set it to `offline` to skip network calls,
  `online` for full access, or `debug` to log request payloads.
- Server-specific environment variables:
  - `SC_ZEN_OFFLINE=1` to force Zen into offline mode (requires manual executor
    registration).
  - `SC_RUBE_API_KEY` for Rube automation calls.
  - `SC_BROWSER_MODE=on` to collect snapshots from the Browser MCP.

## 2. Zen Integration (Consensus)

- The Zen adapter now uses `ModelRouterFacade.run_consensus`, which means it
  requires the same provider executors as the rest of the framework.
- When no executors are available the integration raises `RuntimeError` and the
  command fails fast—there is no heuristic fallback.
- Provide API keys or register in-memory executors during tests:

  ```python
  from SuperClaude.ModelRouter import ModelRouterFacade

  facade = ModelRouterFacade(offline=True)
  facade.consensus.register_executor('gpt-4o', my_executor)
  ```

## 3. Rube Integration (Automation)

- Enable by setting `servers.rube.enabled: true` in `mcp.yaml` and exporting
  `SC_RUBE_API_KEY`.
- Use `SC_RUBE_MODE=dry-run` to simulate responses without hitting the network.
- Errors bubble up with actionable messages (e.g., missing token, HTTP failure)
  so automation scripts can abort cleanly.

## 4. Browser Integration

- Provide `SC_BROWSER_MODE=on` (or pass `--browser` to relevant commands) to
  collect console logs and snapshots.
- When network policies disallow browser access the integration reports a
  skipped snapshot rather than returning placeholder data.

## 5. Troubleshooting

- Check `.superclaude_metrics/mcp.log` for detailed request/response traces.
- Use `python -m SuperClaude.MCP --list` to confirm available integrations, or
  `python -m SuperClaude.MCP --describe rube --json` for structured metadata.
- Run `python benchmarks/run_benchmarks.py --suite integration` after changing
  MCP settings; the suite exercises Rube and Browser paths alongside the main
  workflow tests.
