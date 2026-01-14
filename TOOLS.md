# SuperClaude Tool Reference

This document describes the tools and integrations available within SuperClaude.

## Native Claude Code Tools

These tools are built into Claude Code and always available:

### File Operations
| Tool | Purpose |
|------|---------|
| `Read` | Read file contents |
| `Write` | Create or overwrite files |
| `Edit` | Make precise edits to files |
| `Glob` | Find files by pattern |
| `Grep` | Search file contents |

### Execution
| Tool | Purpose |
|------|---------|
| `Bash` | Execute shell commands |
| `Task` | Launch subagent for complex tasks |

### Notebook
| Tool | Purpose |
|------|---------|
| `NotebookEdit` | Edit Jupyter notebook cells |

### Web
| Tool | Purpose |
|------|---------|
| `WebFetch` | Fetch and analyze web content |
| `WebSearch` | Search the web |

### Workflow
| Tool | Purpose |
|------|---------|
| `TodoWrite` | Manage task lists |
| `AskUserQuestion` | Get user input |

## MCP Server Tools

### PAL MCP (Meta-Prompting)

Multi-model consensus and analysis:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__pal__chat` | Collaborative thinking | General queries with specific model |
| `mcp__pal__thinkdeep` | Multi-stage investigation | Complex analysis, architecture |
| `mcp__pal__planner` | Sequential planning | Implementation planning |
| `mcp__pal__consensus` | Multi-model consensus | Critical decisions |
| `mcp__pal__codereview` | Systematic code review | PR reviews, security audits |
| `mcp__pal__precommit` | Git change validation | Pre-commit checks |
| `mcp__pal__debug` | Root cause analysis | Complex bugs |
| `mcp__pal__listmodels` | Show available models | Model selection |

**Usage Example (Consensus):**
```python
mcp__pal__consensus({
    "step": "Evaluate API design options",
    "models": [
        {"model": "gpt-5.2", "stance": "for"},
        {"model": "gemini-3-pro", "stance": "against"},
        {"model": "claude-opus", "stance": "neutral"}
    ]
})
```

### Rube MCP (App Integrations)

500+ app integrations for cross-application automation:

| Tool | Purpose |
|------|---------|
| `RUBE_SEARCH_TOOLS` | Discover available integrations |
| `RUBE_MULTI_EXECUTE_TOOL` | Execute up to 50 tools in parallel |
| `RUBE_CREATE_PLAN` | Create workflow execution plans |
| `RUBE_MANAGE_CONNECTIONS` | Manage OAuth/API connections |
| `RUBE_REMOTE_WORKBENCH` | Execute Python in sandbox |
| `RUBE_CREATE_UPDATE_RECIPE` | Create reusable automation |
| `RUBE_FIND_RECIPE` | Find recipes by description |
| `RUBE_EXECUTE_RECIPE` | Run a saved recipe |

**Supported Apps:** Slack, GitHub, Gmail, Google Sheets, Jira, Notion, Teams, and 500+ more.

### Web Search (via Rube MCP)

Web search is available through Rube MCP's LINKUP_SEARCH tool:

```python
RUBE_MULTI_EXECUTE_TOOL({
    "tools": [{
        "tool_slug": "LINKUP_SEARCH",
        "arguments": {
            "query": "latest Python 3.12 features",
            "depth": "deep",
            "output_type": "sourcedAnswer"
        }
    }]
})
```

## Validation Tools

### ToolRunner (Internal)

Real tool integration for validation stages:

| Method | Tool | Purpose |
|--------|------|---------|
| `run_pytest` | pytest | Run tests, collect coverage |
| `run_ruff_check` | ruff | Lint Python code |
| `run_mypy` | mypy | Type checking |
| `run_bandit` | bandit | Security scanning |
| `check_syntax` | py_compile | Syntax validation |

## Quality Pipeline Stages

Default validation stages:

| Stage | Tool | Fatal on Failure |
|-------|------|------------------|
| `syntax` | py_compile | Yes |
| `security` | bandit | Yes (critical/high) |
| `style` | ruff | No |
| `tests` | pytest | Yes |
| `type_check` | mypy | No |
| `performance` | metrics | No |

## Agent Tools

Each agent has access to appropriate tools based on their role:

### Common Agent Tools
- Read, Write, Edit (file operations)
- Grep, Glob (search)
- Bash (execution)
- TodoWrite (task management)

### Specialized Agent Tools
- Security agents: bandit, security scan
- Test agents: pytest, coverage tools
- DevOps agents: Docker, Kubernetes CLIs
- Data agents: SQL, pandas

## Tool Selection Guidelines

### When to Use Native Tools
- Simple file operations: Read, Write, Edit
- Pattern matching: Glob, Grep
- Shell commands: Bash
- Subagent tasks: Task

### When to Use PAL MCP
- Need multi-model consensus
- Complex debugging
- Architecture decisions
- Code review

### When to Use Rube MCP
- Cross-app automation
- External service integration
- Workflow recipes
- OAuth-protected APIs

### When to Use Web Search (LINKUP_SEARCH)
- Current information lookup
- Latest documentation
- Recent updates
- Real-time data

## Tool Limitations

### Rate Limits
- API tools have provider limits
- Batch operations when possible
- Cache results where applicable

### Timeouts
- Default timeout: 300s
- Long operations may need adjustment
- Use async for slow tools

### Availability
- Some tools require API keys
- MCP servers must be connected
- Fallback gracefully when unavailable
