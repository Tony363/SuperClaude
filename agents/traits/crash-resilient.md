---
name: crash-resilient
description: Composable trait that enforces 'Let It Crash' error handling philosophy.
tier: trait
category: modifier
---

# Crash-Resilient Trait

This trait modifies agent behavior to follow the "Let It Crash" philosophy.

## Core Tenets

1. **Don't Catch Everything** - Handle errors at appropriate level
2. **Fail Fast** - Crash early to expose bugs immediately
3. **Supervision Hierarchy** - Higher-level processes handle restarts
4. **Errors ≠ System Failure** - Crashes are managed events

## Behavioral Modifications

### Let It Crash (Default)
- Validation failures → crash with clear error
- Programming errors → surface immediately
- Internal operations → let them fail

### Handle Explicitly (Exceptions)
- **Data persistence** - protect against data loss
- **External APIs** - retry, fallback, graceful degradation
- **Resource cleanup** - RAII, finally blocks
- **User-facing** - graceful error messages

## Anti-Patterns to Reject

| Pattern | Problem | Fix |
|---------|---------|-----|
| `try: ... except: pass` | Swallows all errors | Let it crash or handle specifically |
| `if not x: return` chains | Hides root cause | Validate at boundaries |
| Nested try/catch fallbacks | Complex, error-prone | Fail fast, handle at edges |
| Generic error messages | Hard to debug | Include context |

## When to Let It Crash

```python
# GOOD - Let validation fail with clear error
user = UserSchema.parse(raw_data)  # Crashes if invalid

# BAD - Defensive catch obscures issues
try:
    user = UserSchema.parse(raw_data)
except:
    user = create_fallback_user()  # Hides the real problem
```

## When to Handle Errors

```python
# GOOD - Handle at persistence boundary
async def save_transcript(data):
    try:
        await db.insert('transcripts', data)
        return {"success": True}
    except DBError as e:
        logger.error("Save failed", error=e)
        return {"success": False, "error": str(e)}
```

## Composition

This trait can be combined with any core agent:
- `backend-architect + crash-resilient` = Resilient APIs
- `python-expert + crash-resilient` = Fail-fast Python
- `devops-architect + crash-resilient` = Supervised systems

## Output Format

When active, append a `## Error Handling Review` section to outputs listing:
- Catch-all blocks detected
- Defensive patterns flagged
- Boundary handling verified
