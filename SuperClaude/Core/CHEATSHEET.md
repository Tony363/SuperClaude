# SuperClaude Cheatsheet

## Instant Decision Guide

| Situation | Command |
|-----------|---------|
| Don't know where to start | `--brainstorm` |
| Code is broken | `--think 2 --delegate` |
| Need web content | `--tools fetch` |
| Want to improve code | `--delegate --loop` |
| Complex task (>3 steps) | `--task-manage` |
| Production changes | `--safe-mode` |
| High context usage | `--uc` |

## Essential Flags (Only 8!)

| Flag | When to Use |
|------|------------|
| `--brainstorm` | Explore requirements |
| `--task-manage` | Track multi-step work |
| `--think [1-3]` | Analyze (1=quick, 3=deep) |
| `--delegate` | Auto-select best agent |
| `--loop` | Iterate until quality ≥70 |
| `--safe-mode` | Production safety |
| `--uc` | Save tokens |
| `--tools [name]` | Enable specific MCP |

## Task Agent Selection

```
Unknown scope → general-purpose
Debugging → root-cause-analyst
Refactoring → refactoring-expert
Documentation → technical-writer
Performance → performance-engineer
UI/UX → frontend-architect
Backend → backend-architect
Security → security-engineer
```

## MCP Tool Selection

```
Web content → fetch
File operations → filesystem
Bulk edits → MultiEdit
Browser testing → external Playwright/Cypress pipelines
```

## Power Combinations

```bash
# Deep debugging
--think 3 --delegate

# Safe refactoring
--delegate --safe-mode --loop

# Full feature development
--brainstorm --task-manage --test

# Efficient large operations
--task-manage --uc --delegate
```

## Quality Scoring

| Score | Action |
|-------|--------|
| 90-100 | ✅ Accept |
| 70-89 | ⚠️ Review |
| <70 | 🔄 Auto-retry |

## The Golden Rules

1. `git status` first, always
2. TodoWrite for >3 steps
3. Feature branches only
4. Quality <70 = iterate
5. No TODO comments
6. Build only what's asked

## Symbols for Efficiency

When using `--uc`:
- → leads to
- ✅ complete
- ❌ failed
- 🔄 in progress
- ⚠️ warning
- 🔍 analyze
- ⚡ performance
- 🛡️ security

## Quick Workflow

```
git status
↓
Choose flag(s)
↓
Execute with tools
↓
Quality check
↓
Iterate if <70
```
