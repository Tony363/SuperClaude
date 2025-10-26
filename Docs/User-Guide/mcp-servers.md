# MCP Server Integrations (Stub)

SuperClaude bundles three MCP integrations (Zen, Deepwiki, Rube) with configuration stored under `SuperClaude/MCP`.

Refer to the core assets for the current connection details:

- [MCP integration module](../../SuperClaude/MCP/__init__.py)
- [Core tooling reference](../../SuperClaude/Core/TOOLS.md)

## Getting Started

- Run `SuperClaude install --components mcp` to provision the recommended set.
- Export `SC_NETWORK_MODE=online` (or edit `SuperClaude/Config/mcp.yaml`) when you want Rube to execute live automation. Without network access it automatically returns dry-run payloads.
- Provide a Composio token via `SC_RUBE_API_KEY` or the `servers.rube.api_key` field to authorise requests.
- Use `SC_RUBE_MODE=dry-run` to force simulation even when the network is available.

This placeholder keeps the README link working while the full integration guide
is reconstructed.
