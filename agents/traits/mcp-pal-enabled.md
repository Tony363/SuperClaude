---
name: mcp-pal-enabled
description: Composable trait enabling comprehensive PAL MCP integration for multi-model reasoning, debugging, and code review.
tier: trait
category: mcp-integration
---

# PAL MCP Enabled Trait

This trait enables agents to leverage PAL MCP's full suite of collaborative AI tools for reasoning, debugging, code review, and multi-model consensus.

## Available PAL MCP Tools

### Core Reasoning Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__pal__chat` | General collaborative thinking | Brainstorming, second opinions, idea validation |
| `mcp__pal__thinkdeep` | Multi-stage investigation | Complex problems, architecture decisions, security analysis |
| `mcp__pal__planner` | Sequential planning with branching | Project planning, migration strategies, system design |
| `mcp__pal__consensus` | Multi-model voting | Critical decisions, architectural choices, technology evaluations |

### Code Quality Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__pal__codereview` | Systematic code review | Quality, security, performance, architecture analysis |
| `mcp__pal__precommit` | Git change validation | Before commits, multi-repo validation, security review |
| `mcp__pal__debug` | Root cause analysis | Complex bugs, performance issues, race conditions, memory leaks |

### Utility Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__pal__challenge` | Force critical thinking | When statements are questioned, validate assumptions |
| `mcp__pal__apilookup` | API/SDK documentation | Current docs, version info, breaking changes, migrations |
| `mcp__pal__listmodels` | Available models | Check available AI models for consensus/review |
| `mcp__pal__clink` | External CLI integration | Link to Gemini CLI, Qwen CLI, other AI CLIs |

## Behavioral Modifications

When this trait is applied, the agent will:

### Automatic PAL Invocation

1. **Before major decisions** - Use `consensus` with 2-3 models for architectural/security choices
2. **During debugging** - Use `debug` for systematic root cause analysis
3. **Before commits** - Use `precommit` to validate changes
4. **For code review** - Use `codereview` covering quality, security, performance, architecture
5. **When uncertain** - Use `thinkdeep` for multi-stage investigation
6. **For planning** - Use `planner` for complex task decomposition

### Consensus Patterns

```python
# Architectural decisions - 3 model consensus
mcp__pal__consensus(models=[
    {"model": "gpt-5.2", "stance": "for"},
    {"model": "gemini-3-pro-preview", "stance": "against"},
    {"model": "deepseek-v3.2:cloud", "stance": "neutral"}
])

# Quick validation - 2 model consensus
mcp__pal__consensus(models=[
    {"model": "gpt-5.2", "stance": "neutral"},
    {"model": "gemini-3-pro-preview", "stance": "neutral"}
])
```

### Debug Workflow

```python
# Systematic debugging with PAL
mcp__pal__debug(
    step="Investigation step description",
    step_number=1,
    total_steps=3,
    hypothesis="Current theory about root cause",
    findings="Evidence collected so far",
    confidence="exploring|low|medium|high|very_high|certain",
    relevant_files=["/path/to/file.py"],
    use_assistant_model=True  # Enable expert validation
)
```

### Code Review Workflow

```python
# Comprehensive code review
mcp__pal__codereview(
    step="Review narrative and findings",
    step_number=1,
    total_steps=2,
    review_type="full|security|performance|quick",
    findings="Quality, security, performance, architecture notes",
    relevant_files=["/path/to/file.py"],
    issues_found=[{"severity": "high", "description": "..."}],
    confidence="medium"
)
```

## Trigger Conditions

PAL MCP should be invoked when:

| Condition | PAL Tool | Reason |
|-----------|----------|--------|
| High-stakes code change | `consensus` | Multiple perspectives reduce risk |
| Security-related code | `codereview` + `consensus` | Critical requires validation |
| Performance optimization | `thinkdeep` | Complex analysis needed |
| Bug investigation | `debug` | Systematic methodology |
| Before git push | `precommit` | Catch issues early |
| Architectural decision | `planner` + `consensus` | Plan then validate |
| Uncertain approach | `chat` | Get second opinion |
| Conflicting requirements | `challenge` | Force critical thinking |

## Composition

Combine with any core agent:
- `root-cause-analyst + mcp-pal-enabled` = PAL-powered debugging
- `security-engineer + mcp-pal-enabled` = Multi-model security validation
- `system-architect + mcp-pal-enabled` = Consensus-driven architecture

## Output Format

When active, include PAL MCP results in outputs:

```markdown
## PAL MCP Analysis

### Tool Used: [tool_name]
### Models Consulted: [list of models]
### Confidence: [high/medium/low]

### Key Findings
- Finding 1
- Finding 2

### Recommendations
- Recommendation 1
- Recommendation 2
```
