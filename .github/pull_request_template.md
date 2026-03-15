## Summary
<!-- Brief description of changes (1-3 sentences) -->

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Tests

---

## Design Principle Compliance

> Refer to CLAUDE.md Design Philosophy section for detailed guidance.

### Let It Crash (Primary Principle)
- [ ] No new `try/except` blocks added without justification
- [ ] No generic `except Exception` catches that swallow errors
- [ ] No `except: pass` patterns
- [ ] Pydantic ValidationErrors propagate (not caught)
- [ ] Any exception handling is for OPTIONAL features only (telemetry, logging)

### SOLID Principles
- [ ] **SRP**: Each new function/class has a single responsibility
- [ ] **OCP**: Changes extend behavior without modifying existing code (where possible)
- [ ] **LSP**: New implementations honor base type contracts
- [ ] **ISP**: Interfaces are focused and minimal
- [ ] **DIP**: Dependencies are injected, not hardcoded

### KISS Principle
- [ ] No premature abstractions (3+ use cases before abstracting)
- [ ] Functions are under 30 lines (or have justification)
- [ ] Nesting depth is 3 or fewer levels
- [ ] No "clever" one-liners that sacrifice readability
- [ ] Next engineer can predict behavior and modify safely

### Pure Functions
- [ ] Business logic functions are pure (same input -> same output)
- [ ] Side effects (I/O, logging, DB) are pushed to boundaries
- [ ] Non-deterministic dependencies (datetime, random) are injected
- [ ] No global state mutations

---

## Exceptions & Justifications
<!-- If any principle was intentionally violated, explain why here -->

| Principle | File:Line | Justification |
|-----------|-----------|---------------|
| _Example: Let It Crash_ | `scripts/foo.py:42` | _Optional telemetry feature_ |

---

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Reviewer Notes
<!-- Any specific areas to focus on during review -->
