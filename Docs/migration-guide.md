# Migration Guide: v6 to v7

This guide covers migrating from SuperClaude v6.x to v7.0 (Tiered Agent Architecture).

## Overview of Changes

### What Changed

| v6.x | v7.0 |
|------|------|
| 131 agents in flat structure | 33 agents in tiered structure (16 core + 10 traits + 7 extensions) |
| `agents/core/` + `agents/extended/` | `agents/core/` + `agents/traits/` + `agents/extensions/` |
| Monolithic agent personas | Composable agent + trait system |
| No schema validation | JSON Schema + Python validation |
| Hardcoded agent lists | Frontmatter-driven discovery |

### Why the Change

The v6 architecture had 131 agents with significant overlap and maintenance burden. The v7 tiered architecture provides:

- **Maintainability**: 33 agents vs 131 (75% reduction)
- **Composability**: Combine any agent with any trait
- **Validation**: Schema enforcement prevents drift
- **Clarity**: Clear tier separation (core → traits → extensions)

## Migration Steps

### Step 1: Update Agent References

If you reference agents by path, update to the new locations:

```python
# v6.x paths
"agents/core/python-expert.md"
"agents/extended/security-auditor.md"

# v7.0 paths
"agents/core/python-expert.md"      # Core agents stay in core/
"agents/traits/security-first.md"   # Security is now a trait
"agents/extensions/rust-expert.md"  # Language specialists in extensions/
```

### Step 2: Replace Deprecated Agents

Many specialized agents are now combinations of core agent + trait:

| v6 Agent | v7 Replacement |
|----------|----------------|
| `security-auditor` | `security-engineer` or any agent + `security-first` trait |
| `performance-optimizer` | `performance-engineer` or any agent + `performance-first` trait |
| `tdd-practitioner` | Any agent + `test-driven` trait |
| `legacy-migration-expert` | Any agent + `legacy-friendly` trait |
| `cloud-architect` | `devops-architect` + `cloud-native` trait |
| `documentation-writer` | `technical-writer` |
| `python-pro` | `python-expert` |

### Step 3: Use Trait Composition

Instead of finding a specialized agent, compose behavior:

```bash
# v6.x - Find specific agent
--agent=secure-python-developer

# v7.0 - Compose agent + traits
--agent=python-expert --trait=security-first --trait=test-driven
```

### Step 4: Update Custom Agents

If you created custom agents, update frontmatter to v7 schema:

```yaml
# v6.x frontmatter
---
name: my-agent
description: My custom agent
triggers: [keyword1, keyword2]
---

# v7.0 frontmatter (add tier field)
---
name: my-agent
description: My custom agent
tier: extension          # Required: core, trait, or extension
category: custom         # Recommended
triggers: [keyword1, keyword2]
tools: [Read, Write, Edit, Bash]
---
```

### Step 5: Validate Your Agents

Run the validator to check your agent definitions:

```bash
# Python validator (primary)
python scripts/validate_agents.py --verbose

# JSON Schema validator (for external tooling)
python scripts/validate_schema.py --verbose
```

## API Changes

### AgentRegistry

```python
# v6.x
from SuperClaude.Agents import AgentRegistry
registry = AgentRegistry()
registry.discover_agents()
agents = registry.get_all_agents()  # Returns 131 agents

# v7.0
from SuperClaude.Agents.registry import AgentRegistry
registry = AgentRegistry()
registry.discover_agents()
agents = registry.get_all_agents()       # Returns 23 (excludes traits)
traits = registry.get_all_traits()       # Returns 10 traits
core = registry.get_agents_by_tier("core")  # Returns 16
```

### AgentSelector

```python
# v6.x
from SuperClaude.Agents import AgentSelector
selector = AgentSelector()
agent, score = selector.find_best_match("debug python error")

# v7.0 - Now supports traits
from SuperClaude.Agents.selector import AgentSelector
selector = AgentSelector()
result = selector.select_agent(
    "debug python error",
    traits=["security-first", "test-driven"]
)
print(result.agent_name)      # "python-expert" or "root-cause-analyst"
print(result.traits_applied)  # ["security-first", "test-driven"]
print(result.confidence)      # 0.0 - 1.0
```

### Trait Conflicts

v7 detects incompatible trait combinations:

```python
result = selector.select_agent(
    "build feature",
    traits=["minimal-changes", "rapid-prototype"]  # Conflict!
)
# Result includes:
# - trait_conflicts: [("minimal-changes", "rapid-prototype")]
# - conflict_warning: "Conflicting traits detected..."
```

## Directory Structure

```
v6.x                              v7.0
====                              ====
agents/                           agents/
├── core/          (16 agents)    ├── core/        (16 agents)
├── extended/      (115 agents)   ├── traits/      (10 traits)
└── index.yaml                    ├── extensions/  (7 agents)
                                  ├── DEPRECATED/  (106 archived)
                                  └── index.yaml   (auto-generated)
```

## Deprecated Agents

All 106 deprecated agents are preserved in `agents/DEPRECATED/` for reference. They are not loaded by the registry but remain accessible if needed.

To find a deprecated agent's replacement:

1. Check `agents/DEPRECATED/` for the old agent
2. Look at its triggers and category
3. Find the matching core agent + appropriate traits

## Troubleshooting

### "Agent not found" errors

The agent may have been consolidated. Check:
1. Is it now a core agent with a different name?
2. Is it replaced by a core agent + trait combination?
3. Is it in `agents/DEPRECATED/`?

### Validation errors on custom agents

Ensure your frontmatter includes:
- `name`: lowercase, alphanumeric with hyphens
- `description`: max 200 characters
- `tier`: one of `core`, `trait`, `extension`

### Trait conflicts

Some traits are mutually exclusive:
- `minimal-changes` conflicts with `rapid-prototype`
- `legacy-friendly` has tension with `cloud-native` (warning only)

Choose one or the other based on your use case.

## Getting Help

- Run `python scripts/validate_agents.py --verbose` for detailed validation
- Check `agents/DEPRECATED/` for old agent definitions
- Review `CLAUDE.md` for the current architecture documentation

## Version History

- **v7.0.0**: Tiered agent architecture (current)
- **v6.x**: Flat 131-agent structure (deprecated)
