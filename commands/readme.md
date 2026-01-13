---
name: readme
description: "Auto-update README.md based on git diff with PAL consensus validation"
category: documentation
complexity: basic
mcp-servers: [pal]
personas: [technical-writer]
requires_evidence: false
---

# /sc:readme - README Auto-Update

Analyze git changes and update README.md accordingly.

## Triggers
- "update readme based on changes"
- "sync readme with code"
- "readme out of date"
- `/sc:readme`

## Usage

```bash
/sc:readme                    # Update README based on main branch diff
/sc:readme --preview          # Show what would change
/sc:readme --base develop     # Compare against develop branch
/sc:readme --consensus        # Force multi-model validation
```

## Behavioral Flow

1. **DISCOVER** - `git diff main...HEAD --name-status`
2. **ANALYZE** - Categorize changes (API, deps, config, features)
3. **PLAN** - Map changes to README sections
4. **VALIDATE** - PAL consensus for significant changes
5. **GENERATE** - Update README via Write tool
6. **VERIFY** - PAL codereview on result

## Tool Coordination

| Tool | Purpose |
|------|---------|
| Bash | Git diff and log commands |
| Read | README.md and changed files |
| Write | Update README.md |
| PAL | Consensus and review |

## Key Patterns

### Change Detection
```bash
git diff main...HEAD --name-status
git log main...HEAD --oneline
```

### Section Mapping
- API changes → API Reference, Usage Examples
- Dependency changes → Installation, Dependencies
- Config changes → Configuration
- New features → Features, Quick Start

## Examples

### Basic Update
```bash
/sc:readme
# Analyzes all changes since branching from main
# Updates relevant README sections
```

### Preview Only
```bash
/sc:readme --preview
# Shows proposed changes without writing
```

## Boundaries

- Does NOT create README from scratch (use `/sc:document` for that)
- Does NOT modify code, only documentation
- Requires PAL consensus for API/breaking changes
