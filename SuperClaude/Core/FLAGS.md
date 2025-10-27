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
- 1: Fast tier (5K tokens) - Quick analysis
- 2: Standard tier (15K tokens) - Moderate depth
- 3: Deep tier (50K tokens) - Maximum analysis with GPT-5 priority
- Default fallback: Claude Opus 4.1 for all tiers
- Plan mode auto-selects --think 3 with GPT-5

## Model Selection

**Model Routing**
- Selection based on mode and --think level via `models.yaml`
- Introspection/Planning: Auto-select GPT-5 (50K tokens)
- Consensus: Multi-model ensemble [GPT-5, Claude Opus 4.1, GPT-4.1]
- Override: --model <id> | --deny-model <id> | --tokens <n>

## Tool Selection

**--delegate**
- Auto-select best Task agent for the job
- Enable quality-driven iteration (score < 70 = retry)

**--tools [name]**
- Enable specific MCP server: zen, rube, browser
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
