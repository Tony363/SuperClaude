# SuperClaude Quick Start

## Most Common Tasks

### "I need to build something new"
```
--brainstorm                # Explore requirements
--task-manage              # Plan implementation  
--delegate                 # Auto-select best tools
```

### "My code is broken"
```
--think 2                  # Analyze the issue
--delegate                 # Uses root-cause-analyst
--test                     # Verify fixes
```

### "I need a UI component"
```
--delegate                 # Picks the frontend specialist stack
--mcp browser              # Optional: launch local browser automation helpers
```

### "I want to improve code"
```
--delegate                 # Uses refactoring-expert
--loop                     # Iterate until quality ≥70
```

## Essential Commands

| What You Want | Use This |
|--------------|----------|
| Explore ideas | `--brainstorm` |
| Complex task (>3 steps) | `--task-manage` |
| Find unknown code | `--delegate` |
| Deep analysis | `--think 3` |
| External automation | `--mcp rube` |
| Production safety | `--safe-mode` |
| Save tokens | `--uc` |

## The 5-Step Workflow

1. **Check**: `git status` (always start here)
2. **Plan**: Use flags based on task type
3. **Execute**: Tools auto-selected or use `--delegate`
4. **Validate**: Quality score evaluated automatically
5. **Iterate**: Auto-retry if quality < 70

## Tool Quick Reference

### Task Agents (use with --delegate)
- **Unknown scope**: general-purpose
- **Debugging**: root-cause-analyst  
- **Refactoring**: refactoring-expert
- **Documentation**: technical-writer
- **Performance**: performance-engineer

### MCP Servers (use with --mcp)
- **Consensus & Analysis**: zen
- **Automation (opt-in)**: rube
- **Local Browser Automation**: browser
- **Persistence**: UnifiedStore (built-in, no --mcp flag)

## Power Combos

```bash
# Maximum analysis
--think 3 --delegate

# Safe production changes
--safe-mode --loop

# Efficient large operations
--task-manage --uc

# Complete feature development
--brainstorm --task-manage --test
```

## Rules to Remember

✅ **Always Do:**
- Start with `git status`
- Use TodoWrite for >3 steps
- Let quality scores guide iteration
- Work on feature branches

❌ **Never Do:**
- Work on main/master
- Skip failing tests
- Leave TODO comments
- Add features not requested

## Getting Unstuck

- **Lost?** → `--brainstorm`
- **Complex?** → `--task-manage`
- **Unknown files?** → `--delegate`
- **Need analysis?** → `--think 2`
- **High context?** → `--uc`

## Examples

### Add Authentication
```
--brainstorm               # Explore requirements
--task-manage             # Plan implementation
--delegate                # Find existing auth
--mcp rube                # Leverage automation hooks
--test                    # Validate everything
```

### Fix Performance Issue
```
--think 2                 # Analyze problem
--delegate                # Use performance-engineer
--loop                    # Iterate improvements
--test                    # Verify no regressions
```

### Refactor Legacy Code
```
--delegate                # Use refactoring-expert
--safe-mode              # Maximum safety
--loop 5                 # Multiple iterations
```

---
**Start now**: Type `--brainstorm` if unsure, or pick a command above!
