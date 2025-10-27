# Browser MCP Server

Browser MCP exposes a local Chromium instance to Claude Desktop so automated browsing,
DOM inspection, and screenshot capture can be performed directly from SuperClaude slash
commands. The `/sc:test --browser` workflow routes requests through the Browser MCP
integration so the same APIs are available in both the CLI and Claude Desktop.

## Capabilities

- **Headless or headed Chromium sessions** for inspecting UI regressions.
- **DOM queries and mutations** to verify selectors before shipping UI automation.
- **Screenshot capture** to attach visual evidence to SuperClaude change plans.

## Setup (Claude Desktop)

1. Follow the official setup guide for Claude Desktop at  
   <https://docs.browsermcp.io/setup-server#claude-desktop>.
2. Install the Browser MCP server (Node 18+) by running the provided `npm` commands
   in the guide or by using the prebuilt binary for your platform.
3. Register the server with Claude Desktop via `claude mcp add browser ...`.
4. Restart Claude Desktop so the new server appears in the MCP list.

## Configuration

- The Browser MCP listens on `localhost` and requires a Chromium installation
  (Chrome, Edge, or Chromium).
- Export `BROWSER_MCP_CHROMIUM_PATH` if the bundled autodetection does not
  locate your browser binary.
- Set `BROWSER_MCP_TEMP_DIR` when running inside ephemeral environments (CI,
  devcontainers) to ensure artifacts persist for the duration of the run.

## Safety Notes

- Browser MCP only connects to Chromium instances on the local machine; no
  remote automation endpoints are touched unless you explicitly configure them.
- Always review recorded DOM actions before executing destructive flows (such as
  deleting resources) to avoid surprises during auditing.
- For CI usage, prefer headless mode and capture screenshots to the
  `.superclaude_metrics/` directory so reviewers can inspect the results.
