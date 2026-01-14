# Rube MCP Server (Native)

Rube MCP connects SuperClaude to Composio's automation hub, enabling access to 500+ SaaS integrations through Claude Code's native MCP tools.

## Native MCP Tools

Use these tools directly via Claude Code's tool invocation:

| Tool | Description |
|------|-------------|
| `mcp__rube__RUBE_SEARCH_TOOLS` | Discover available tools and integrations |
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | Execute tools in parallel (up to 20) |
| `mcp__rube__RUBE_CREATE_PLAN` | Create execution plans for workflows |
| `mcp__rube__RUBE_MANAGE_CONNECTIONS` | Create/manage app connections |
| `mcp__rube__RUBE_REMOTE_WORKBENCH` | Execute Python in remote sandbox |
| `mcp__rube__RUBE_REMOTE_BASH_TOOL` | Execute bash in remote sandbox |
| `mcp__rube__RUBE_FIND_RECIPE` | Find recipes by natural language |
| `mcp__rube__RUBE_EXECUTE_RECIPE` | Execute saved recipes |
| `mcp__rube__RUBE_GET_RECIPE_DETAILS` | Get recipe details |
| `mcp__rube__RUBE_MANAGE_RECIPE_SCHEDULE` | Manage scheduled recipe runs |

## Capabilities

- **Workflow dispatch** - create tickets, update sprints, trigger CI/CD pipelines
- **Notification fan-out** - post release notes or QA status updates across tools
- **Data sync** - coordinate artifacts (docs, dashboards, sheets) with changes
- **Web search** - LINKUP_SEARCH tool for sourced answers and citations

## Usage Examples

### Search for Tools
```
Use mcp__rube__RUBE_SEARCH_TOOLS with:
  queries: [{"use_case": "send a message to slack"}]
  session: {generate_id: true}
```

### Execute Tools
```
Use mcp__rube__RUBE_MULTI_EXECUTE_TOOL with:
  tools: [{"tool_slug": "SLACK_SEND_MESSAGE", "arguments": {...}}]
  session_id: "<from search>"
  memory: {}
  sync_response_to_workbench: false
```

### Web Search (LINKUP_SEARCH)

Rube MCP includes the LINKUP_SEARCH tool for deep web search with sourced answers, citations, and URLs.

#### Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `query` | string | The search query |
| `depth` | `"deep"`, `"standard"` | Search thoroughness (use "deep" for comprehensive results) |
| `output_type` | `"sourcedAnswer"`, `"searchResults"`, `"structured"` | Response format |

#### When to Use

- Current library/framework versions and documentation
- Latest API syntax and best practices
- Recent security updates and vulnerabilities
- Error messages and deprecation warnings
- External service status and configuration

#### Simple Search
```
Use mcp__rube__RUBE_MULTI_EXECUTE_TOOL with:
  tools: [{"tool_slug": "LINKUP_SEARCH", "arguments": {
    "query": "pytest asyncio best practices 2025",
    "depth": "deep",
    "output_type": "sourcedAnswer"
  }}]
  session_id: "<from RUBE_SEARCH_TOOLS>"
  memory: {}
  sync_response_to_workbench: false
```

#### Batch Searches
```
Use mcp__rube__RUBE_MULTI_EXECUTE_TOOL with:
  tools: [
    {"tool_slug": "LINKUP_SEARCH", "arguments": {"query": "React 19 new features", "depth": "deep", "output_type": "sourcedAnswer"}},
    {"tool_slug": "LINKUP_SEARCH", "arguments": {"query": "TypeScript 5.4 changes", "depth": "deep", "output_type": "sourcedAnswer"}}
  ]
  session_id: "<from RUBE_SEARCH_TOOLS>"
  memory: {}
```

## Configuration

MCP server configuration is handled by Claude Code settings, not SuperClaude.
No environment variables (like `SC_RUBE_API_KEY`) are needed - auth is managed by the MCP server.

## Notes

- All tools are invoked directly via Claude Code's native tool system
- No Python wrapper code is used - tools are called directly
- Session IDs are managed per workflow for context preservation
- Memory parameter helps track cross-call state
