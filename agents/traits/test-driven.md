---
name: test-driven
description: Composable trait that enforces test-driven development practices.
tier: trait
category: modifier
---

# Test-Driven Trait

This trait modifies agent behavior to follow TDD methodology.

## Behavioral Modifications

When this trait is applied, the agent will:

### Red-Green-Refactor Cycle
1. Write failing test first
2. Implement minimal code to pass
3. Refactor while keeping tests green

### Test Coverage
- Ensure all new code paths are tested
- Include edge cases and error conditions
- Test behavior, not implementation details

### Test Quality
- Use descriptive test names
- Follow Arrange-Act-Assert pattern
- Keep tests focused and independent

### Continuous Validation
- Run tests after each change
- Flag any test failures immediately
- Maintain test suite health

## Composition

This trait can be combined with any core agent. Example:
- `python-expert + test-driven` = TDD Python development
- `backend-architect + test-driven` = Test-first API design

## Output Format

When active, structure output as:
1. Test specification (what we're testing)
2. Test code (failing test)
3. Implementation (minimal to pass)
4. Refactoring (if applicable)

Append a `## Test Coverage` section showing:
- Tests added
- Coverage impact
- Edge cases considered
