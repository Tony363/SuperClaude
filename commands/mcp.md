---
name: mcp
description: "Comprehensive MCP orchestration integrating PAL and Rube for multi-model reasoning and app automation"
category: workflow
complexity: standard
mcp-servers: [pal, rube]
personas: [software-architect, general-purpose]
requires_evidence: false
aliases: [mcp-orchestrate, pal, rube]
flags:
  - name: pal
    description: "PAL tool to use: chat, thinkdeep, planner, consensus, codereview, precommit, debug, challenge, apilookup"
    type: string
  - name: rube
    description: Enable Rube MCP integration
    type: boolean
    default: false
  - name: apps
    description: Comma-separated apps for Rube (e.g., slack,github,jira)
    type: string
  - name: models
    description: Models for consensus (comma-separated)
    type: string
    default: auto
  - name: full-validation
    description: Run all PAL validators
    type: boolean
    default: false
---

# /sc:mcp - MCP Orchestration Hub

Central hub for all MCP-powered workflows integrating PAL (multi-model reasoning) and Rube (500+ app integrations).

## Triggers
- Multi-model consensus needed for decisions
- External app integrations (Slack, GitHub, Jira, etc.)
- Complex debugging requiring cross-model analysis
- Requests like "use PAL", "run consensus", "connect to Slack"

## Usage
```
/sc:mcp [task] --pal <tool> [--models "model1,model2"]
/sc:mcp [task] --rube --apps <app1,app2>
/sc:mcp [task] --pal <tool> --rube --full-validation
```

## PAL MCP Tools

| Tool | Invocation | Use Case |
|------|------------|----------|
| `chat` | `mcp__pal__chat` | Brainstorming, second opinions |
| `thinkdeep` | `mcp__pal__thinkdeep` | Multi-stage investigation |
| `planner` | `mcp__pal__planner` | Sequential planning |
| `consensus` | `mcp__pal__consensus` | Multi-model voting |
| `codereview` | `mcp__pal__codereview` | Systematic code review |
| `precommit` | `mcp__pal__precommit` | Git change validation |
| `debug` | `mcp__pal__debug` | Root cause analysis |
| `challenge` | `mcp__pal__challenge` | Question assumptions |
| `apilookup` | `mcp__pal__apilookup` | API documentation |

## Rube MCP Tools

| Tool | Invocation | Use Case |
|------|------------|----------|
| `SEARCH_TOOLS` | `mcp__rube__RUBE_SEARCH_TOOLS` | Discover integrations |
| `GET_TOOL_SCHEMAS` | `mcp__rube__RUBE_GET_TOOL_SCHEMAS` | Get input schemas |
| `MULTI_EXECUTE_TOOL` | `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | Parallel execution |
| `REMOTE_BASH_TOOL` | `mcp__rube__RUBE_REMOTE_BASH_TOOL` | Remote shell commands |
| `REMOTE_WORKBENCH` | `mcp__rube__RUBE_REMOTE_WORKBENCH` | Python sandbox |
| `CREATE_UPDATE_RECIPE` | `mcp__rube__RUBE_CREATE_UPDATE_RECIPE` | Save workflows |
| `EXECUTE_RECIPE` | `mcp__rube__RUBE_EXECUTE_RECIPE` | Run saved recipes |
| `FIND_RECIPE` | `mcp__rube__RUBE_FIND_RECIPE` | Search recipes |
| `GET_RECIPE_DETAILS` | `mcp__rube__RUBE_GET_RECIPE_DETAILS` | Inspect recipes |
| `MANAGE_CONNECTIONS` | `mcp__rube__RUBE_MANAGE_CONNECTIONS` | App authentication |
| `MANAGE_RECIPE_SCHEDULE` | `mcp__rube__RUBE_MANAGE_RECIPE_SCHEDULE` | Schedule recipes |

## Orchestration Patterns

### Research + Decide + Execute
```
1. PAL thinkdeep - Investigate problem
2. PAL consensus - Multi-model decision
3. Rube SEARCH_TOOLS - Find execution tools
4. Rube MULTI_EXECUTE - Implement decision
```

### Review + Validate + Notify
```
1. PAL codereview - Review changes
2. PAL precommit - Validate git changes
3. Rube MULTI_EXECUTE - Send notifications
4. Rube CREATE_UPDATE_RECIPE - Save for CI/CD
```

## Examples

### Multi-Model Consensus
```
/sc:mcp "evaluate auth strategy" --pal consensus --models "gpt-5,gemini-2.5-pro"
```

### External App Automation
```
/sc:mcp "notify team of deploy" --rube --apps slack,github
```

### Full Validation Pipeline
```
/sc:mcp "validate architecture" --pal thinkdeep --rube --full-validation
```

## Boundaries

**Will:**
- Invoke PAL tools for reasoning, review, and debugging
- Connect to external apps via Rube MCP
- Orchestrate multi-tool workflows
- Save reusable recipes for automation

**Will Not:**
- Execute destructive operations without confirmation
- Store credentials (delegated to Rube connection manager)
- Bypass PAL consensus quorum requirements
