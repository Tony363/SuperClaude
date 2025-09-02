# SuperClaude Essential Flags

## Core Behavioral Flags

**--brainstorm**
- Activate collaborative discovery for vague requirements
- Ask probing questions, guide requirement elicitation

**--task-manage**
- Enable TodoWrite tracking for multi-step operations (>3 steps)
- Orchestrate complex workflows with quality gates

**--token-efficient / --uc**
- Reduce tokens by 30-50% when context >75%
- Use symbols and compressed communication

## Analysis Depth

**--think [1-3]**
- 1: Quick analysis (2K tokens)
- 2: Standard analysis (4K tokens) + Sequential
- 3: Deep analysis (10K tokens) + all tools

## Tool Selection

**--delegate**
- Auto-select best Task agent for the job
- Enable quality-driven iteration (score < 70 = retry)

**--tools [name]**
- Enable specific MCP server: serena, morphllm, sequential, magic, deepwiki, playwright
- Use --no-mcp to disable all MCP servers

## Quality Control

**--loop [n]**
- Enable iterative improvement (default: 3 iterations)
- Auto-iterate when quality score < 70

**--safe-mode**
- Maximum validation for production environments
- Conservative execution with extra checks

## Simplified Triggers

| Situation | Use Flag |
|-----------|----------|
| Vague requirements | --brainstorm |
| Complex task (>3 steps) | --task-manage |
| High context usage | --uc |
| Need deep analysis | --think 3 |
| Unknown file locations | --delegate |
| Production code | --safe-mode |
| Need improvements | --loop |

## Auto-Activation Rules

These flags activate automatically when conditions are met:
- **--task-manage**: >3 steps or >2 directories
- **--delegate**: Unknown scope or >5 files
- **--uc**: Context usage >75%
- **--loop**: Quality score < 70