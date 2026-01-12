---
name: solid-aligned
description: Composable trait that enforces SOLID design principles in all outputs.
tier: trait
category: modifier
---

# SOLID-Aligned Trait

This trait modifies agent behavior to enforce SOLID design principles.

## Behavioral Modifications

When this trait is applied, the agent will:

### Single Responsibility (SRP)
- Each component/function/struct does ONE thing well
- Flag files >300 lines as potential SRP violations
- Separate concerns: UI ≠ business logic ≠ data fetching

### Open-Closed (OCP)
- Add features WITHOUT changing existing code
- Use strategy/factory patterns instead of if/else chains
- Flag switch statements on type as OCP violations

### Liskov Substitution (LSP)
- Subtypes must honor base type contracts
- Flag overrides that throw or add preconditions
- Consumers shouldn't need to know specific subtypes

### Interface Segregation (ISP)
- Many focused interfaces > one fat interface
- Flag interfaces with >7 methods
- Props/dependencies should be minimal

### Dependency Inversion (DIP)
- Depend on abstractions, not concretions
- Flag `new ConcreteClass()` in business logic
- Inject dependencies for testability

## Code Smells to Flag

| Smell | Principle | Fix |
|-------|-----------|-----|
| File >300 lines | SRP | Extract responsibilities |
| if/else type chains | OCP | Strategy pattern |
| Override that throws | LSP | Honor contract |
| 10+ method interface | ISP | Split interfaces |
| `new Service()` in logic | DIP | Dependency injection |

## Composition

This trait can be combined with any core agent:
- `python-expert + solid-aligned` = SOLID Python
- `backend-architect + solid-aligned` = SOLID APIs
- `frontend-architect + solid-aligned` = SOLID React components

## Output Format

When active, append a `## SOLID Review` section to outputs listing:
- Violations detected with severity
- Refactoring recommendations
- Patterns applied
