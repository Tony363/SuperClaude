---
name: sc-principles
description: Enforce KISS and Pure Function principles through mandatory validation gates. Detects complexity violations, impure functions in business logic, and I/O mixed with logic.
---

# /sc:principles - Code Principles Validator

Mandatory validation skill enforcing two fundamental software engineering principles:

1. **KISS (Keep It Simple, Stupid)** - Code should be as simple as possible
2. **Functional Core, Imperative Shell** - Business logic must be pure; I/O belongs at edges

## Quick Start

```bash
# Full validation (KISS + Purity)
/sc:principles src/

# KISS only validation
/sc:principles src/ --kiss-only

# Purity only validation
/sc:principles src/ --purity-only

# Strict mode (warnings become errors)
/sc:principles src/ --strict

# Generate detailed report
/sc:principles src/ --report
```

## Behavioral Flow

```
1. INITIALIZE
   ├── Detect scope root
   ├── Find changed Python files (git diff)
   └── Determine file contexts (core vs shell)

2. ANALYZE
   ├── Parse AST for each file
   ├── Calculate complexity metrics (KISS)
   └── Detect I/O patterns (Purity)

3. VALIDATE
   ├── Compare against thresholds
   ├── Classify violations (error vs warning)
   └── Apply context rules (core stricter than shell)

4. REPORT/BLOCK
   ├── Output violations with locations
   ├── Generate actionable recommendations
   └── Exit 0 (pass) or 2 (blocked)
```

## Validation Rules

### KISS Gate

| Metric | Threshold | Severity | Description |
|--------|-----------|----------|-------------|
| Cyclomatic Complexity | > 10 | error | Number of independent paths through code |
| Cyclomatic Complexity | > 7 | warning | Early warning for growing complexity |
| Cognitive Complexity | > 15 | error | Weighted complexity (nested structures count more) |
| Function Length | > 50 lines | error | Lines of code per function (inclusive count) |
| Nesting Depth | > 4 levels | error | If/for/while/with/try nesting |
| Parameter Count | > 5 | warning | Function parameters |

**Cognitive vs Cyclomatic Complexity:**
- Cyclomatic counts decision points (branches)
- Cognitive weights nested structures more heavily: `1 + nesting_depth` per control structure
- Example: `if (if (if ...))` has low cyclomatic but high cognitive (hard to read)

### Purity Gate

The "Functional Core, Imperative Shell" pattern:

| Layer | Path Patterns | I/O Allowed | Severity |
|-------|---------------|-------------|----------|
| Core | `*/domain/*`, `*/logic/*`, `*/services/*`, `*/utils/*`, `*/core/*` | NO | error |
| Shell | `*/handlers/*`, `*/adapters/*`, `*/api/*`, `*/cli/*`, `*/scripts/*`, `*/tests/*` | YES | warning |

**Note:** Files in `*/archive/*`, `*/examples/*`, `*/benchmarks/*`, `conftest.py`, `setup.py`, and `*__main__.py` are treated as shell (I/O allowed).

**Detected I/O Patterns:**

| Category | Examples |
|----------|----------|
| File I/O | `open()`, `read()`, `write()`, `Path.read_text()` |
| Network | `requests.get()`, `httpx`, `urllib`, `socket` |
| Database | `execute()`, `query()`, `session.add()`, `cursor` |
| Subprocess | `subprocess.run()`, `os.system()`, `Popen` |
| Global State | `global`, `nonlocal` keywords |
| Side Effects | `print()`, `logging.*`, `logger.*` |
| Async I/O | `async def`, `await`, `async for`, `async with` |

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--kiss-only` | bool | false | Run only KISS validation |
| `--purity-only` | bool | false | Run only purity validation |
| `--threshold` | int | 10 | Max cyclomatic complexity |
| `--max-cognitive` | int | 15 | Max cognitive complexity |
| `--max-lines` | int | 50 | Max function line count |
| `--max-depth` | int | 4 | Max nesting depth |
| `--max-params` | int | 5 | Max parameter count |
| `--strict` | bool | false | Treat all warnings as errors |
| `--core-only` | bool | false | Only validate core layer files |
| `--all` | bool | false | Analyze all files, not just changed |
| `--report` | bool | false | Generate detailed JSON report |

## Integration Flags

For use by other skills and pre-commit hooks:

| Flag | Description |
|------|-------------|
| `--pre-commit` | Run as pre-commit hook (blocks commit on failure) |
| `--inline` | Real-time validation during implementation |
| `--json` | Output JSON format for programmatic use |

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Validation passed | Proceed |
| 2 | Violations detected | Blocked - refactor required |
| 3 | Validation error | Manual intervention needed |

## Personas Activated

- **code-warden** - Primary reviewer for principles enforcement
- **refactoring-expert** - For complex refactoring guidance
- **quality-engineer** - For metrics integration

## Validator Scripts

Located in `scripts/` directory:

### validate_kiss.py

```bash
python .claude/skills/sc-principles/scripts/validate_kiss.py \
  --scope-root . \
  --threshold 10 \
  --max-lines 50 \
  --json
```

### validate_purity.py

```bash
python .claude/skills/sc-principles/scripts/validate_purity.py \
  --scope-root . \
  --core-only \
  --json
```

## Pre-commit Integration

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: kiss-check
        name: KISS Validation
        entry: python .claude/skills/sc-principles/scripts/validate_kiss.py --scope-root . --json
        language: python
        types: [python]
        pass_filenames: false

      - id: purity-check
        name: Purity Validation
        entry: python .claude/skills/sc-principles/scripts/validate_purity.py --scope-root . --json
        language: python
        types: [python]
        pass_filenames: false
```

## Refactoring Guidance

When violations are detected, apply these patterns:

### For Complexity Violations

1. **Extract Method** - Split large functions into smaller, named pieces
2. **Guard Clauses** - Replace nested if/else with early returns
3. **Strategy Pattern** - Replace complex switch/if-else with polymorphism
4. **Decompose Conditional** - Name complex conditions as explaining variables

**Before:**
```python
def process(data, config, user):
    if data:
        if config.enabled:
            if user.has_permission:
                for item in data:
                    if item.valid:
                        # deep logic here
```

**After:**
```python
def process(data, config, user):
    if not can_process(data, config, user):
        return None
    return process_items(data)

def can_process(data, config, user):
    return data and config.enabled and user.has_permission

def process_items(data):
    return [process_item(item) for item in data if item.valid]
```

### For Purity Violations

1. **Dependency Injection** - Pass dependencies as arguments
2. **Repository Pattern** - Isolate database operations
3. **Adapter Pattern** - Wrap external APIs
4. **Return Don't Print** - Return values, let callers handle output

**Before:**
```python
# In domain/calculator.py (CORE - should be pure)
def calculate_discount(user_id):
    user = db.query(User).get(user_id)  # I/O in core!
    print(f"Calculating for {user.name}")  # Side effect!
    return 0.2 if user.is_premium else 0.1
```

**After:**
```python
# In domain/calculator.py (CORE - now pure)
def calculate_discount(user: User) -> float:
    """Pure function - no I/O, just logic."""
    return 0.2 if user.is_premium else 0.1

# In adapters/discount_service.py (SHELL - I/O allowed)
def get_user_discount(user_id: int) -> float:
    user = user_repository.get(user_id)
    discount = calculate_discount(user)
    logger.info(f"Discount for {user.name}: {discount}")
    return discount
```

## Examples

### Example 1: Full Validation

```bash
$ /sc:principles src/ --report

KISS Validation: BLOCKED
Files analyzed: 12
Errors: 3, Warnings: 5

Violations:
  [ERROR] src/services/order.py:45 process_order: complexity = 15 (max: 10)
  [ERROR] src/utils/parser.py:12 parse_data: length = 78 (max: 50)
  [WARNING] src/domain/calc.py:8 calculate: parameters = 7 (max: 5)

Purity Validation: BLOCKED
Core violations: 2, Shell warnings: 1

Violations:
  [ERROR] src/domain/user.py:23 get_status: database - db.query (context: core)
  [ERROR] src/services/report.py:56 generate: file_io - open (context: core)

Recommendations:
  - COMPLEXITY: Extract helper functions, use early returns
  - DATABASE: Use repository pattern. Business logic receives data, not queries
  - FILE I/O: Move file operations to adapter layer
```

### Example 2: KISS Only

```bash
$ /sc:principles src/ --kiss-only --threshold 8

KISS Validation: PASSED
Files analyzed: 12
Errors: 0, Warnings: 2
```

### Example 3: Strict Mode

```bash
$ /sc:principles src/ --strict

# All warnings become errors
# Any warning will block
```

## Quality Integration

This skill integrates with SuperClaude quality gates:

- Contributes to `simplicity` dimension (weight: 0.08)
- Contributes to `purity` dimension (weight: 0.02)
- Triggers `simplification` strategy when simplicity < 70
- Triggers `purification` strategy when purity < 70

## Related Skills

- `/sc:improve --type principles` - Auto-refactor for principles compliance
- `/sc:implement` - Includes principles validation by default
- `/sc:analyze` - Code analysis includes principles metrics

---

## Test Coverage

The validators have comprehensive test coverage (27 tests):

**Purity Validator Tests:**
- Async function detection (`async def`)
- Await expression detection
- Async for loop detection
- Async with context manager detection
- Shell vs core severity differentiation
- Edge cases (syntax errors, unicode, empty files)

**KISS Validator Tests:**
- Function length (inclusive count)
- Cyclomatic complexity
- Cognitive complexity
- Nesting depth
- Parameter count
- Edge cases (syntax errors, unicode, empty files)

Run tests:
```bash
python -m pytest .claude/skills/sc-principles/tests/ -v
```

---

**Version**: 1.1.0
**Validators**: `validate_kiss.py`, `validate_purity.py`
**Agent**: `code-warden`
**Tests**: 27 passing
