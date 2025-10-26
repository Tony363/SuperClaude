# Rube MCP Server

The Rube MCP server connects SuperClaude to Composio's automation hub, enabling access to hundreds of SaaS integrations from a single endpoint.

## Capabilities

- **Workflow dispatch** – create tickets, update sprints, or trigger CI/CD pipelines.
- **Notification fan-out** – post release notes or QA status updates across collaboration tools.
- **Data sync** – coordinate artefacts (docs, dashboards, sheets) with orchestrated changes.

## Configuration

- Endpoint: `https://rube.app/mcp` (default)
- Credentials: set `SC_RUBE_API_KEY` with your Composio OAuth token.
- Network: export `SC_NETWORK_MODE=online` to allow outbound calls. When missing, the integration runs in dry-run mode and only logs payloads.
- Dry-run: force simulation even when online with `SC_RUBE_MODE=dry-run`.

## Safety Notes

- The connector fails fast with descriptive errors if credentials are missing or the endpoint is unreachable.
- Dry-run mode is recommended for CI and local development because it never touches external services.
- Future releases will add secure secret storage and granular scope controls.
