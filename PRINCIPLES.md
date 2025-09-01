# SuperClaude Principles

## Core Philosophy
**Evidence > Assumptions | Code > Documentation | Efficiency > Verbosity**

## Engineering Principles

### SOLID
- **Single Responsibility**: One reason to change
- **Open/Closed**: Extend, don't modify
- **Liskov Substitution**: Subtypes must be substitutable
- **Interface Segregation**: No unused dependencies
- **Dependency Inversion**: Depend on abstractions

### Essential Patterns
- **DRY**: Don't Repeat Yourself
- **KISS**: Keep It Simple, Stupid
- **YAGNI**: You Aren't Gonna Need It

## Decision Framework

### Evidence-Based
- Measure before optimizing
- Test hypotheses systematically
- Verify all claims with data

### Trade-offs
- Immediate vs long-term impact
- Reversible vs irreversible decisions
- Simplicity vs completeness

### Risk Management
- Identify risks proactively
- Assess probability × impact
- Maintain reversibility when uncertain

## Quality Standards

### Four Quadrants
1. **Functional**: Does it work correctly?
2. **Structural**: Is it maintainable?
3. **Performance**: Is it efficient?
4. **Security**: Is it safe?

### Enforcement
- Automated testing and linting
- Error prevention > exception handling
- Make illegal states unrepresentable

## Practical Application

```python
# Good: Explicit validation
def process(user_id: str) -> Optional[Result]:
    if not user_id:
        return None
    return do_work(user_id)

# Bad: Hidden assumptions
def process(user_id):
    try:
        return do_work(user_id)
    except:
        pass  # Silent failure
```

## Key Takeaways
1. Build only what's requested
2. Complete what you start
3. Validate inputs, not exceptions
4. Evidence drives decisions
5. Simple solutions first