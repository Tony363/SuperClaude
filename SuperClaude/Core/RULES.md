# SuperClaude Core Rules

## Priority System
🔴 **CRITICAL**: Security, data safety - Never compromise  
🟡 **IMPORTANT**: Quality, maintainability - Strong preference  
🟢 **RECOMMENDED**: Best practices - Apply when practical

## Core Workflow
**Priority**: 🔴

1. **Understand** → Read requirements, analyze context
2. **Plan** → Identify parallelizable operations, use TodoWrite for >3 steps
3. **Execute** → Parallel operations by default, sequential only for dependencies
4. **Validate** → Quality score (0-100), auto-iterate if <70
5. **Complete** → Clean workspace, verify success

## Implementation Rules
**Priority**: 🟡

### Complete What You Start
- Deliver working code, not scaffolding
- No TODO comments for core functionality
- Quality < 70 = mandatory completion

### Build Only What's Asked
- MVP first, iterate based on feedback
- No speculative features (YAGNI)
- 1:1 ratio of requested vs delivered features

### Error Prevention > Exception Handling
```python
# ✅ Right: Validate first
if not user_id:
    return None
    
# ❌ Wrong: Catch later
try:
    process(user_id)
except:
    return None
```

## Safety Rules
**Priority**: 🔴

### Git Safety
- Always `git status` before starting
- Feature branches only, never main/master
- Meaningful commit messages

### File Operations
- Read before Write/Edit
- Use absolute paths
- Clean temporary files

### Quality Gates
- Run tests before marking complete
- Investigate failures, don't skip
- Document breaking changes

## Professional Standards
**Priority**: 🟡

### Code Organization
- Follow existing patterns
- Consistent naming conventions
- Logical directory structure

### Communication
- No marketing language ("blazingly fast", "100% secure")
- Evidence-based claims only
- Honest trade-off assessments

## Tool Selection
**Priority**: 🟢

Use the most powerful tool available:
- Unknown scope → Task(general-purpose)
- Multi-file edits → MultiEdit > sequential Edits
- Symbol operations → UnifiedStore > manual search
- Pattern edits → MultiEdit > individual changes
- Web content → Fetch > WebSearch
- Documentation → Repository knowledge base > web search

## Quick Reference

### Must Do
- ✅ TodoWrite for >3 steps
- ✅ Quality evaluation after tasks
- ✅ Parallel operations by default
- ✅ Feature branches only

### Never Do
- ❌ Work on main/master
- ❌ Leave TODO comments
- ❌ Skip failing tests
- ❌ Use marketing language

### Decision Flow
```
Task complexity?
├─ >3 steps → TodoWrite required
├─ Unknown scope → Use Task agent
├─ Quality <70 → Auto-iterate
└─ High risk → Enable --safe-mode
```
