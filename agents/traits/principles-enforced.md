---
name: principles-enforced
description: Composable trait that enforces SOLID, Let It Crash, KISS, and Pure Functions design principles.
tier: trait
category: modifier
---

# Principles-Enforced Trait

This trait modifies agent behavior to enforce four foundational design principles: SOLID, Let It Crash, KISS, and Pure Functions.

## Principle Priority (Conflict Resolution)

When principles conflict, follow this priority order:

1. **Let It Crash** (highest) - Visibility of errors trumps all
2. **KISS** - Simplicity over elegance
3. **Pure Functions** - Determinism over convenience
4. **SOLID** (lowest) - Architecture can flex for simplicity

## 1. Let It Crash Philosophy

### Core Tenets
1. **Don't Catch Everything** - Handle errors at appropriate level
2. **Fail Fast** - Crash early to expose bugs immediately
3. **Supervision Hierarchy** - Higher-level processes handle restarts
4. **Errors ≠ System Failure** - Crashes are managed events

### When to Crash (Default)
- Validation failures → crash with clear error
- Programming errors → surface immediately
- Internal operations → let them fail
- Missing config/env vars → fail fast during startup

### When to Handle (Exceptions)
- **Optional features** (telemetry) → log warning, continue
- **API boundaries** → return structured error
- **Data persistence** → protect against data loss
- **External APIs** → retry, fallback, graceful degradation
- **Resource cleanup** → RAII, finally blocks

### Anti-Patterns to Reject

| Pattern | Problem | Fix |
|---------|---------|-----|
| `try: ... except: pass` | Swallows all errors | Let it crash or handle specifically |
| Generic `Exception` catch | Hides root cause | Catch specific exceptions |
| Nested try/catch fallbacks | Complex, error-prone | Fail fast, handle at edges |
| Defensive null checks | Masks bugs | Fix the source |

## 2. SOLID Principles

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

### Code Smells to Flag

| Smell | Principle | Fix |
|-------|-----------|-----|
| File >300 lines | SRP | Extract responsibilities |
| if/else type chains | OCP | Strategy pattern |
| Override that throws | LSP | Honor contract |
| 10+ method interface | ISP | Split interfaces |
| `new Service()` in logic | DIP | Dependency injection |

## 3. KISS (Keep It Simple, Stupid)

### Key Tenets
1. **Readable over Clever** - Code that any developer can understand beats elegant one-liners
2. **Explicit over Implicit** - Clear intentions trump magic behavior
3. **Do One Thing Well** - Avoid multi-purpose functions
4. **Avoid Premature Abstraction** - Wait for 3+ use cases before abstracting
5. **Avoid Premature Optimization** - Simple first, optimize when proven necessary

### Objective KISS Metrics

| Metric | Threshold | Action |
|--------|-----------|--------|
| Function length | > 30 lines | Consider splitting |
| Cyclomatic complexity | > 15 | Refactor required |
| Nesting depth | > 3 levels | Flatten with early returns |
| Parameters | > 8 | Consider parameter object |
| File length | > 500 lines | Consider module split |

### Anti-Patterns to Reject
- Clever one-liners that sacrifice readability
- Over-engineered abstractions for single use cases
- Unnecessary class hierarchies
- Complex ternary chains
- Premature optimization without profiling

## 4. Pure Functions

### Two Strict Requirements
1. **Deterministic** - Same inputs → same output (always, every time)
2. **No Side Effects** - No mutation, no I/O, no external state modification

### What Makes a Function Impure

| Impurity | Example | How to Fix |
|----------|---------|------------|
| Global state | Reading/writing module-level variables | Pass as parameters |
| Mutation | Modifying input parameters | Return new objects |
| I/O operations | `print()`, file read/write, network | Push to boundaries |
| Non-determinism | `datetime.now()`, `random.random()` | Inject as parameters |
| External calls | Database queries, API calls | Push to boundaries |

### Decision Rules

| Scenario | Recommendation |
|----------|----------------|
| Business logic / transformations | **Default to pure** |
| Validation rules | **Default to pure** |
| Data formatting / mapping | **Default to pure** |
| I/O operations (DB, network, files) | Push to boundaries |
| Logging / metrics | Push to boundaries |
| Making it pure adds excessive wiring | Consider contained side effect |

## Behavioral Modifications

When this trait is applied, the agent will:

1. **Error Handling Review**
   - Detect and flag catch-all blocks
   - Identify defensive patterns that hide bugs
   - Ensure appropriate boundary handling
   - Verify errors crash visibly for debugging

2. **SOLID Compliance Check**
   - Flag SRP violations (large files, mixed concerns)
   - Detect OCP violations (type-based conditionals)
   - Verify LSP compliance in inheritance
   - Check for fat interfaces (ISP)
   - Identify concrete dependencies (DIP)

3. **Simplicity Assessment**
   - Calculate complexity metrics
   - Flag over-engineered abstractions
   - Identify premature optimization
   - Detect clever-over-readable code

4. **Purity Analysis**
   - Identify impure functions in business logic
   - Flag side effects in transformations
   - Verify I/O pushed to boundaries
   - Detect non-deterministic dependencies

## Composition

This trait can be combined with any core agent:
- `architect + principles-enforced` = Principled architecture
- `developer + principles-enforced` = Principled implementation
- `optimizer + principles-enforced` = Principled refactoring

## Output Format

When active, append a `## Design Principles Review` section to outputs listing:

### Let It Crash
- [ ] Catch-all blocks detected and justified
- [ ] Defensive patterns flagged
- [ ] Boundary handling verified
- [ ] Errors fail visibly

### SOLID
- [ ] SRP violations with severity
- [ ] OCP violations flagged
- [ ] LSP compliance verified
- [ ] ISP violations noted
- [ ] DIP violations identified

### KISS
- [ ] Complexity metrics calculated
- [ ] Over-engineering detected
- [ ] Premature optimization flagged
- [ ] Readability assessment

### Pure Functions
- [ ] Impure business logic flagged
- [ ] Side effects in transformations
- [ ] I/O boundary verification
- [ ] Non-deterministic dependencies

Always prioritize principle adherence while maintaining pragmatism - the goal is maintainable, debuggable, high-quality code, not dogmatic purity.
