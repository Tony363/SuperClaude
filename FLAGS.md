# SuperClaude Framework Flags

Behavioral flags for Claude Code execution modes and tool selection.

## Mode Activation Flags

| Flag | Trigger | Behavior |
|------|---------|----------|
| `--brainstorm` | Vague requests, "maybe", "thinking about" | Collaborative discovery, probing questions |
| `--introspect` | Self-analysis, error recovery, meta-cognition | Expose thinking (🤔, 🎯, ⚡, 📊, 💡) |
| `--task-manage` | >3 steps OR >2 directories OR >3 files | Delegation, systematic organization |
| `--orchestrate` | Multi-tool ops, performance constraints | Optimize tool matrix, parallel execution |
| `--token-efficient` | Context >75%, large operations, --uc | Symbol communication, 30-50% reduction |

## MCP Server Flags

| Flag | Alias | Purpose | When to Use |
|------|-------|---------|-------------|
| `--deepwiki` | `--dw` | Documentation retrieval | Library imports, framework questions |
| `--sequential` | `--seq` | Multi-step reasoning | Complex debugging, system design |
| `--magic` | - | UI generation (21st.dev) | /ui, /21, design systems |
| `--morphllm` | `--morph` | Pattern-based edits | Bulk transformations, style enforcement |
| `--serena` | - | Symbol operations | Project memory, large codebases |
| `--playwright` | `--play` | Browser automation | E2E testing, visual validation |
| `--all-mcp` | - | Enable all servers | Maximum complexity scenarios |
| `--no-mcp` | - | Disable all servers | Native-only execution |

## Testing & Quality Flags

| Flag | Trigger | Action |
|------|---------|--------|
| `--test` | After code changes | Run test suites, validate changes |
| `--review` | Before commits | Code quality analysis, suggestions |
| `--fix` | Linting/format errors | Auto-fix issues where possible |

## Analysis Depth Flags

| Flag | Complexity | Token Usage | MCP Servers |
|------|------------|-------------|-------------|
| `--think` | Moderate | ~4K | Sequential |
| `--think-hard` | System-wide | ~10K | Sequential + Deepwiki |
| `--ultrathink` | Critical redesign | ~32K | All servers |

## Error Handling Flags

| Flag | Purpose | Approach |
|------|---------|----------|
| `--no-exceptions` | Defensive coding | Validation-first, minimize try/catch |

## Execution Control Flags

| Flag | Parameters | Trigger | Effect |
|------|------------|---------|--------|
| `--delegate` | auto/files/folders | >7 dirs OR >50 files | Sub-agent parallel processing |
| `--concurrency` | 1-15 | Resource optimization | Limit parallel operations |
| `--loop` | - | Polish/refine/enhance | Iterative improvement cycles |
| `--iterations` | 1-10 | Specific cycles | Set improvement count |
| `--validate` | - | Risk >0.7, prod env | Pre-execution risk assessment |
| `--safe-mode` | - | Resource >85%, critical | Maximum validation, auto --uc |

**Formulas**: Complexity = `(files × directories × dependencies) / 100` | Risk = `(impact × probability × irreversibility) / 10`

## Task Delegation Flags

| Flag | Delegates To | Use Case |
|------|--------------|----------|
| `--delegate-search` | general-purpose | Unknown scope exploration |
| `--delegate-debug` | root-cause-analyst | Error investigation, debugging |
| `--delegate-refactor` | refactoring-expert | Code improvement, tech debt |
| `--delegate-docs` | technical-writer | Multi-file documentation |
| `--delegate-test` | quality-engineer | Test coverage, quality assessment |

## Output Optimization Flags

| Flag | Parameters | Purpose |
|------|------------|---------|  
| `--uc` / `--ultracompressed` | - | Symbol communication, 30-50% reduction |
| `--scope` | file/module/project/system | Define analysis boundaries |
| `--focus` | performance/security/quality/etc | Target specific domain |

## Flag Priority Rules

**Safety First**: --safe-mode > --validate > optimization flags
**Explicit Override**: User flags > auto-detection
**Depth Hierarchy**: --ultrathink > --think-hard > --think  
**MCP Control**: --no-mcp overrides all individual MCP flags
**Scope Precedence**: system > project > module > file