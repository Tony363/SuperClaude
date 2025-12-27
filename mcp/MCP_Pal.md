# PAL MCP Server (Native) - Formerly "Zen"

PAL MCP provides collaborative thinking, code review, and multi-model consensus through Claude Code's native MCP tools.

## Native MCP Tools

Use these tools directly via Claude Code's tool invocation:

| Tool | Description |
|------|-------------|
| `mcp__pal__chat` | General chat and collaborative thinking |
| `mcp__pal__thinkdeep` | Multi-stage investigation and reasoning |
| `mcp__pal__planner` | Interactive sequential planning with revision |
| `mcp__pal__consensus` | Multi-model consensus through structured debate |
| `mcp__pal__codereview` | Systematic code review with expert validation |
| `mcp__pal__precommit` | Git change validation before committing |
| `mcp__pal__debug` | Systematic debugging and root cause analysis |
| `mcp__pal__challenge` | Critical thinking when statements are challenged |
| `mcp__pal__apilookup` | Current API/SDK documentation lookup |
| `mcp__pal__listmodels` | List available AI models |
| `mcp__pal__clink` | Link to external AI CLIs (Gemini, Codex, etc.) |

## Capabilities

- **Multi-model consensus** - consult multiple models with different stances
- **Deep thinking** - systematic hypothesis testing and evidence gathering
- **Code review** - comprehensive analysis of quality, security, performance
- **Git validation** - pre-commit checks for staged/unstaged changes
- **Debugging** - structured root cause analysis for complex issues

## Usage Examples

### Code Review
```
Use mcp__pal__codereview with:
  step: "Review the authentication module for security issues"
  step_number: 1
  total_steps: 2
  next_step_required: true
  findings: "Initial security scan..."
  relevant_files: ["/path/to/auth.py"]
  model: "gpt-5.2"
```

### Multi-Model Consensus
```
Use mcp__pal__consensus with:
  step: "Evaluate: Should we use REST or GraphQL for the new API?"
  step_number: 1
  total_steps: 3
  next_step_required: true
  findings: "Analyzing tradeoffs..."
  models: [
    {"model": "gpt-5.2", "stance": "for"},
    {"model": "gemini-3-pro-preview", "stance": "against"}
  ]
```

### Deep Thinking
```
Use mcp__pal__thinkdeep with:
  step: "Investigate the performance bottleneck in the database layer"
  step_number: 1
  total_steps: 3
  next_step_required: true
  findings: "Initial profiling shows..."
  hypothesis: "The N+1 query pattern may be causing slowdowns"
  model: "gpt-5.2"
```

### Debugging
```
Use mcp__pal__debug with:
  step: "Analyze the intermittent test failures in CI"
  step_number: 1
  total_steps: 2
  next_step_required: true
  findings: "Test logs show timing-related failures..."
  hypothesis: "Race condition in async initialization"
  model: "gpt-5.2"
```

## Configuration

PAL MCP server configuration is handled by Claude Code settings.
No SuperClaude-specific environment variables are needed.

## Notes

- All tools are invoked directly via Claude Code's native tool system
- continuation_id allows multi-turn conversations across tool calls
- thinking_mode controls reasoning depth (minimal/low/medium/high/max)
- Models can be specified by name - use listmodels to see available options
