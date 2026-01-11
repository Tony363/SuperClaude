# Deprecated Agent Skills

This directory contains archived agent skill wrappers from the previous SuperClaude architecture (v6.x).

## What Are These?

These are `.claude/skills/` wrappers that provided Claude Code discoverability for the 115 extended agents. After consolidation to the tiered architecture, most of these wrappers are no longer needed.

## Active Skills

The following agent skills remain active in `.claude/skills/`:

| Skill | Maps To |
|-------|---------|
| `agent-data-engineer` | `extensions/data-engineer.md` |
| `agent-fullstack-developer` | `core/fullstack-developer.md` |
| `agent-kubernetes-specialist` | `extensions/kubernetes-specialist.md` |
| `agent-ml-engineer` | `extensions/ml-engineer.md` |
| `agent-performance-engineer` | `core/performance-engineer.md` |
| `agent-react-specialist` | `extensions/react-specialist.md` |
| `agent-security-engineer` | `core/security-engineer.md` |
| `agent-technical-writer` | `core/technical-writer.md` |

## Why Deprecate?

1. **Source of truth** - Agent definitions now live in `agents/core|traits|extensions/` with validated frontmatter
2. **Duplicate content** - Skill wrappers duplicated agent persona info
3. **Maintenance burden** - 114 wrappers required updates whenever agents changed

## Using Active Agents

Claude Code can load agents directly from `agents/` directory. The remaining skill wrappers provide backward compatibility for explicit `@agent-*` invocations.

---

*Archived as part of SuperClaude v7.0.0 tiered architecture migration*
