---
name: mcp-rube-enabled
description: Composable trait enabling comprehensive Rube MCP integration for 500+ app automations, workflows, and external service orchestration.
tier: trait
category: mcp-integration
---

# Rube MCP Enabled Trait

This trait enables agents to leverage Rube MCP's full suite of 500+ app integrations for workflow automation, external service orchestration, and cross-app operations.

## Available Rube MCP Tools

### Discovery & Planning

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__rube__RUBE_SEARCH_TOOLS` | Discover available tools | Starting any external task, finding integrations |
| `mcp__rube__RUBE_CREATE_PLAN` | Generate execution plans | Complex multi-step workflows |
| `mcp__rube__RUBE_GET_TOOL_SCHEMAS` | Get tool input schemas | Before executing unfamiliar tools |

### Execution

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | Execute tools in parallel | Batch operations, multi-app workflows |
| `mcp__rube__RUBE_REMOTE_BASH_TOOL` | Remote bash execution | File operations, data processing |
| `mcp__rube__RUBE_REMOTE_WORKBENCH` | Python execution sandbox | Bulk operations, complex data processing |

### Recipes & Automation

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__rube__RUBE_CREATE_UPDATE_RECIPE` | Save workflow as recipe | Reusable automation creation |
| `mcp__rube__RUBE_EXECUTE_RECIPE` | Run saved recipe | Execute previously saved workflows |
| `mcp__rube__RUBE_FIND_RECIPE` | Search recipes | Find existing automations |
| `mcp__rube__RUBE_GET_RECIPE_DETAILS` | Get recipe details | Inspect recipe configuration |
| `mcp__rube__RUBE_MANAGE_RECIPE_SCHEDULE` | Schedule recipes | Set up recurring automation |

### Connections

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__rube__RUBE_MANAGE_CONNECTIONS` | Manage app connections | Connect to new services, check auth status |

## Supported App Categories

### Communication
- Slack, Discord, Microsoft Teams
- Gmail, Outlook, SendGrid
- WhatsApp, Telegram

### Development
- GitHub, GitLab, Bitbucket
- Jira, Linear, Asana
- Vercel, Netlify, Railway

### Productivity
- Google Workspace (Sheets, Docs, Drive, Calendar)
- Notion, Coda, Airtable
- Trello, Monday.com

### Data & Analytics
- Snowflake, BigQuery
- Datadog, Grafana
- Amplitude, Mixpanel

### AI & Automation
- OpenAI, Anthropic
- Zapier, Make
- n8n, Pipedream

## Behavioral Modifications

When this trait is applied, the agent will:

### Automatic Rube Invocation

1. **External service needs** - Search tools before implementing custom integrations
2. **Batch operations** - Use multi-execute for parallel processing
3. **Recurring tasks** - Create and schedule recipes
4. **Data pipelines** - Use remote workbench for complex transformations
5. **Cross-app workflows** - Chain multiple tool executions

### Tool Discovery Pattern

```python
# Always search before executing
mcp__rube__RUBE_SEARCH_TOOLS(
    queries=[
        {"use_case": "send slack message to channel", "known_fields": "channel_name:general"},
        {"use_case": "create github issue", "known_fields": "repo:myrepo"}
    ],
    session={"generate_id": True}  # New workflow
)
```

### Multi-Execute Pattern

```python
# Parallel execution with memory
mcp__rube__RUBE_MULTI_EXECUTE_TOOL(
    tools=[
        {"tool_slug": "SLACK_SEND_MESSAGE", "arguments": {"channel": "#general", "text": "Hello"}},
        {"tool_slug": "GITHUB_CREATE_ISSUE", "arguments": {"title": "Bug", "body": "Description"}}
    ],
    memory={"slack": ["Channel general has ID C1234567"]},
    session_id="existing-session-id",
    sync_response_to_workbench=False
)
```

### Recipe Creation Pattern

```python
# Save workflow as reusable recipe
mcp__rube__RUBE_CREATE_UPDATE_RECIPE(
    name="Daily Standup Report",
    description="Collect standup updates and post to Slack",
    input_schema={"properties": {"channel_name": {"type": "string"}}},
    output_schema={"properties": {"message_sent": {"type": "boolean"}}},
    workflow_code="..."  # Python code using helpers
)
```

### Remote Workbench Pattern

```python
# Complex data processing
mcp__rube__RUBE_REMOTE_WORKBENCH(
    thought="Process large dataset with parallel API calls",
    code_to_execute='''
import concurrent.futures

def process_item(item):
    result, error = run_composio_tool("TOOL_SLUG", {"arg": item})
    return result if not error else None

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    results = list(ex.map(process_item, items))

output = {"processed": len(results)}
output
''',
    current_step="PROCESSING_DATA"
)
```

## Trigger Conditions

Rube MCP should be invoked when:

| Condition | Rube Tool | Reason |
|-----------|-----------|--------|
| Need external API | `RUBE_SEARCH_TOOLS` | Find existing integration |
| Multiple API calls | `RUBE_MULTI_EXECUTE_TOOL` | Parallel execution |
| Complex data transform | `RUBE_REMOTE_WORKBENCH` | Python sandbox |
| Recurring automation | `RUBE_CREATE_UPDATE_RECIPE` | Save for reuse |
| Check app connection | `RUBE_MANAGE_CONNECTIONS` | Verify auth |
| Unknown tool schema | `RUBE_GET_TOOL_SCHEMAS` | Get input format |
| Schedule task | `RUBE_MANAGE_RECIPE_SCHEDULE` | Set up cron |

## Memory Management

Always pass memory for cross-execution context:

```python
memory = {
    "slack": ["Channel #general has ID C1234567"],
    "github": ["Repository myrepo owned by user123"],
    "user_preferences": ["Prefers markdown format"]
}
```

## Composition

Combine with any core agent:
- `devops-architect + mcp-rube-enabled` = CI/CD automation
- `backend-architect + mcp-rube-enabled` = API integration workflows
- `technical-writer + mcp-rube-enabled` = Documentation automation

## Output Format

When active, include Rube MCP results in outputs:

```markdown
## Rube MCP Execution

### Tools Discovered: [count]
### Tools Executed: [list]
### Session ID: [id for continuation]

### Results
- Tool 1: [status]
- Tool 2: [status]

### Memory Stored
- [key]: [value]

### Recipe Created (if applicable)
- Name: [name]
- ID: [recipe_id]
```
