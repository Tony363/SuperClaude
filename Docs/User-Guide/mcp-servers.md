# MCP Server Integrations (Stub)

SuperClaude bundles three MCP integrations (Zen, Rube, and Browser) with configuration stored under `SuperClaude/MCP`.

Refer to the core assets for the current connection details:

- [MCP integration module](../../SuperClaude/MCP/__init__.py)
- [Core tooling reference](../../SuperClaude/Core/TOOLS.md)

## Getting Started

- Run `SuperClaude install --components mcp` to provision the recommended set.
- Export `SC_NETWORK_MODE=online` (or edit `SuperClaude/Config/mcp.yaml`) when you want Rube to execute live automation. Without network access it automatically returns dry-run payloads.
- Provide a Composio token via `SC_RUBE_API_KEY` or the `servers.rube.api_key` field to authorise requests.
- Use `SC_RUBE_MODE=dry-run` to force simulation even when the network is available.
- Enable Browser MCP by setting `SC_BROWSER_MODE=on` (or `--browser` flag on `/sc:test`); register the local Claude Browser server before running linked commands.

Each integration exposes helper utilities:
- `ZenIntegration` handles consensus orchestration and thinking modes.
- `RubeIntegration` bridges to Composio-backed automations with first-class dry-run telemetry.
- `BrowserIntegration` records console logs, snapshots, and lightweight accessibility checks when network policies permit.

This placeholder keeps the README link working while the full integration guide
is reconstructed.
