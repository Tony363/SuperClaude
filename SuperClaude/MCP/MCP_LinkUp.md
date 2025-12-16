# LinkUp Web Search (via Rube MCP)

LinkUp provides deep web search capabilities with sourced answers, citations, and URLs through the native Rube MCP tools.

## How to Use

LinkUp searches are executed via `mcp__rube__RUBE_MULTI_EXECUTE_TOOL`:

```
Use mcp__rube__RUBE_MULTI_EXECUTE_TOOL with:
  tools: [{
    "tool_slug": "LINKUP_SEARCH",
    "arguments": {
      "query": "your search query here",
      "depth": "deep",
      "output_type": "sourcedAnswer"
    }
  }]
  session_id: "<from RUBE_SEARCH_TOOLS>"
  memory: {}
  sync_response_to_workbench: false
  thought: "Searching for [topic]"
  current_step: "SEARCHING"
  next_step: "COMPLETE"
```

## Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `query` | string | The search query |
| `depth` | `"deep"`, `"standard"` | Search thoroughness (use "deep" for comprehensive results) |
| `output_type` | `"sourcedAnswer"`, `"searchResults"`, `"structured"` | Response format |

## Capabilities

- **Deep search with citations** - summarized answers with source lists and follow-up links
- **Multiple queries** - batch multiple searches in a single tool call
- **Sourced answers** - responses include citations and URLs for verification

## Example Usage

### Simple Search
```
Use mcp__rube__RUBE_MULTI_EXECUTE_TOOL with:
  tools: [{
    "tool_slug": "LINKUP_SEARCH",
    "arguments": {
      "query": "pytest asyncio best practices 2025",
      "depth": "deep",
      "output_type": "sourcedAnswer"
    }
  }]
```

### Batch Searches
```
Use mcp__rube__RUBE_MULTI_EXECUTE_TOOL with:
  tools: [
    {"tool_slug": "LINKUP_SEARCH", "arguments": {"query": "React 19 new features", "depth": "deep", "output_type": "sourcedAnswer"}},
    {"tool_slug": "LINKUP_SEARCH", "arguments": {"query": "TypeScript 5.4 changes", "depth": "deep", "output_type": "sourcedAnswer"}}
  ]
```

## When to Use

Use LinkUp for:
- Current library/framework versions and documentation
- Latest API syntax and best practices
- Recent security updates and vulnerabilities
- Error messages and deprecation warnings
- External service status and configuration

## Notes

- LinkUp is accessed through the Rube MCP server's LINKUP_SEARCH tool
- No separate configuration needed - uses the same Rube MCP connection
- Session IDs from RUBE_SEARCH_TOOLS should be reused for context preservation
- Results include citations - include source links in responses
