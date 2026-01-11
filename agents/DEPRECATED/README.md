# Deprecated Agents

This directory contains archived agents from the previous SuperClaude architecture (v6.x).

## Why Were These Deprecated?

After a [multi-model consensus review](../../.claude/plans/), it was determined that:

1. **131 agents was excessive bloat** - All three reviewing models (GPT-5.2, Gemini-3-Pro, DeepSeek-V3.2) agreed the count created maintenance debt without proportional value
2. **Consolidation to 25 agents** - The new tiered architecture provides better coverage with:
   - 16 core agents
   - 8 composable traits
   - 7 domain extensions
3. **Trait composition replaces specialization** - Instead of 115 specialized agents, composable traits let you combine behaviors (e.g., `python-expert + security-first`)

## Replacement Table

| Old Agent Category | Replacement |
|-------------------|-------------|
| Core Development | `backend-architect`, `frontend-architect`, `fullstack-developer` |
| Language Specialists | `python-expert` (core), extensions for TS/Go/Rust |
| Infrastructure | `devops-architect` + `cloud-native` trait |
| Quality/Security | `quality-engineer`, `security-engineer` + traits |
| Data/AI | `data-engineer`, `ml-engineer` extensions |
| Developer Experience | `technical-writer`, various traits |
| Specialized Domains | Domain extensions |
| Meta/Orchestration | `general-purpose` agent |

## Can I Still Use These?

These agents are archived but still readable. However:
- They lack the `tier` field required by the new validator
- They may contain outdated patterns
- They won't be maintained going forward

For best results, use the active agents in `core/`, `traits/`, and `extensions/`.

## Migration

To migrate a custom workflow that relied on a deprecated agent:

1. Identify the closest core agent
2. Apply relevant traits for specialized behavior
3. Use domain extensions if needed

Example:
- Old: `security-auditor` agent
- New: `security-engineer` + `security-first` trait

---

*Archived as part of SuperClaude v7.0.0 tiered architecture migration*
