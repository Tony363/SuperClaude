# SuperClaude Command Flags Reference

This document catalogs all flags available for SuperClaude commands.

## Universal Flags

These flags work across all `/sc:` commands:

| Flag | Short | Description |
|------|-------|-------------|
| `--think <1-3>` | `-t` | Controls reasoning depth (1=fast, 2=balanced, 3=deep) |
| `--consensus` | `-c` | Force multi-model consensus voting |
| `--safe` | `-s` | Enable strict guardrails, disable risky modes |
| `--delegate <agent>` | `-d` | Pin execution to a specific agent |
| `--loop [n]` | `-l` | Enable iterative improvement (default n=3, max=5) |
| `--pal-review` | | Request PAL code review after changes |
| `--verbose` | `-v` | Enable detailed output |
| `--quiet` | `-q` | Minimize output |

## Implementation Flags (`/sc:implement`)

| Flag | Description |
|------|-------------|
| `--agent <name>` | Use specific agent (e.g., `--agent=backend-developer`) |
| `--persona <name>` | Alternative to --agent |
| `--orchestrate` | Enable multi-agent orchestration |
| `--strategy <type>` | Orchestration strategy: hierarchical, consensus, pipeline |
| `--with-tests` | Auto-generate tests for implementation |
| `--fast-codex` | Route through lean Codex persona (requires API keys) |

## Testing Flags (`/sc:test`)

| Flag | Description |
|------|-------------|
| `--coverage` | Enable coverage measurement |
| `--watch` | Watch mode for continuous testing |
| `--framework <name>` | Specify test framework (pytest, jest, etc.) |
| `--markers <expr>` | Pytest marker expression |
| `--fail-fast` | Stop on first failure |

## Analysis Flags (`/sc:analyze`)

| Flag | Description |
|------|-------------|
| `--deep` | Enable deep analysis mode |
| `--risk` | Focus on risk assessment |
| `--dependencies` | Analyze dependency graph |
| `--complexity` | Calculate complexity metrics |

## Design Flags (`/sc:design`)

| Flag | Description |
|------|-------------|
| `--diagram` | Generate architecture diagram |
| `--adr` | Create Architecture Decision Record |
| `--constraints` | Document system constraints |

## Documentation Flags (`/sc:document`)

| Flag | Description |
|------|-------------|
| `--api` | Generate API documentation |
| `--readme` | Generate/update README |
| `--inline` | Add inline code comments |
| `--format <type>` | Output format: markdown, mdx, rst |

## Workflow Flags (`/sc:workflow`)

| Flag | Description |
|------|-------------|
| `--steps` | Define workflow steps |
| `--parallel` | Enable parallel step execution |
| `--checkpoint` | Save workflow state at checkpoints |

## Build Flags (`/sc:build`)

| Flag | Description |
|------|-------------|
| `--target <name>` | Build target |
| `--optimize` | Enable optimizations |
| `--clean` | Clean build |

## Estimate Flags (`/sc:estimate`)

| Flag | Description |
|------|-------------|
| `--breakdown` | Provide detailed breakdown |
| `--risk` | Include risk assessment |
| `--confidence` | Show confidence intervals |

## Git Flags (`/sc:git`)

| Flag | Description |
|------|-------------|
| `--commit` | Create commit |
| `--pr` | Create pull request |
| `--branch <name>` | Specify branch |

## Token Efficiency Mode

When `--uc` (ultra-compressed) is active, output uses symbols:

```
Status:  ✅ Done  ❌ Failed  ⚠️ Warning  🔄 Progress  ⏳ Pending
Domain:  ⚡ Perf  🔍 Analysis  🛡️ Security  📦 Deploy  🏗️ Arch
Logic:   → Leads to  ⇒ Transforms  ∴ Therefore  » Sequence
```

## Flag Combinations

### High-Quality Implementation
```bash
/sc:implement --loop 5 --pal-review --with-tests "Add feature"
```

### Quick Analysis
```bash
/sc:analyze --deep --risk src/
```

### Consensus-Driven Design
```bash
/sc:design --consensus --diagram "API architecture"
```
