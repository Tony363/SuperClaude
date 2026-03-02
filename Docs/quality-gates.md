# Quality Gates Documentation

SuperClaude enforces code quality through automated validation gates. This document explains the available quality gates, their thresholds, and how to use them.

## Overview

| Gate | Purpose | Trigger |
|------|---------|---------|
| **KISS Validator** | Complexity limits | `/sc:principles --kiss` |
| **Purity Validator** | I/O separation | `/sc:principles --purity` |
| **SOLID Validator** | Design principles | `/sc:principles --solid` |
| **Let It Crash Validator** | Error handling | `/sc:principles --crash` |
| **Agent Validator** | Schema compliance | `python scripts/validate_agents.py` |
| **Iterative Loop** | Quality threshold | `--loop` flag |

## KISS Validator

The KISS (Keep It Simple, Stupid) validator enforces complexity limits to ensure maintainable code.

### Thresholds

| Metric | Threshold | Severity | Description |
|--------|-----------|----------|-------------|
| Cyclomatic Complexity | > 10 | **Block** | Control flow paths through a function |
| Cognitive Complexity | > 15 | **Block** | Human-perceived complexity |
| Function Length | > 50 lines | **Block** | Lines of code per function |
| Nesting Depth | > 4 levels | **Block** | Nested control structures |
| Parameter Count | > 5 | Warning | Function parameters |
| Complexity | > 7 | Warning | Early warning threshold |

### Usage

```bash
# Validate a single file
python .claude/skills/sc-principles/scripts/validate_kiss.py path/to/file.py

# Validate with JSON output
python .claude/skills/sc-principles/scripts/validate_kiss.py path/to/file.py --json

# Via skill command
/sc:principles --kiss path/to/file.py
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Validation passed |
| 2 | KISS violations detected (blocked) |
| 3 | Validation error |

### Example Violations

```python
# VIOLATION: Cyclomatic complexity > 10
def process_data(data, mode, flag1, flag2, flag3, flag4):
    if mode == "a":
        if flag1:
            if flag2:
                # ... deeply nested logic
                pass
    elif mode == "b":
        # ... more branches
        pass
    # Too many decision points!

# FIX: Extract into smaller functions
def process_mode_a(data, flags):
    return _handle_flags(data, flags)

def process_mode_b(data):
    return _transform_b(data)

def process_data(data, mode, **flags):
    handlers = {"a": process_mode_a, "b": process_mode_b}
    return handlers[mode](data, flags)
```

### Recommendations

When KISS violations occur:

1. **High Complexity**: Break function into smaller, focused functions
2. **Deep Nesting**: Use early returns, extract helper functions
3. **Long Functions**: Apply single responsibility principle
4. **Many Parameters**: Use configuration objects or dataclasses

## Purity Validator

The Purity validator enforces the "Functional Core, Imperative Shell" pattern by detecting I/O operations mixed with business logic.

### Philosophy

```
┌─────────────────────────────────────────┐
│           Imperative Shell              │
│  (handlers, adapters, CLI, entry points)│
│         MAY have side effects           │
├─────────────────────────────────────────┤
│           Functional Core               │
│    (business logic, transformations)    │
│       MUST be pure (no I/O)             │
└─────────────────────────────────────────┘
```

### Detected Impurities

| Category | Examples |
|----------|----------|
| **File I/O** | `open()`, `read_text()`, `write_text()`, `mkdir()` |
| **Network** | `requests.get()`, `httpx.post()`, `socket.connect()` |
| **Database** | `execute()`, `query()`, `commit()`, `cursor()` |
| **Subprocess** | `subprocess.run()`, `os.system()`, `Popen()` |
| **Console** | `print()`, `input()`, `logging.*` |
| **Global State** | Global variable mutations |

### Shell Patterns (Allowed Impurity)

Functions matching these patterns may contain I/O:

- `*_handler`, `*_adapter`, `*_cli`
- `main`, `run`, `execute`
- `test_*`, `setup_*`, `teardown_*`
- `__init__`, `__enter__`, `__exit__`

### Core Patterns (Must Be Pure)

Functions matching these patterns must NOT contain I/O:

- `calculate_*`, `compute_*`, `transform_*`
- `validate_*`, `parse_*`, `format_*`
- `*_score`, `*_result`, `*_value`

### Usage

```bash
# Validate a file
python .claude/skills/sc-principles/scripts/validate_purity.py path/to/file.py

# Validate with JSON output
python .claude/skills/sc-principles/scripts/validate_purity.py path/to/file.py --json

# Via skill command
/sc:principles --purity path/to/file.py
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Validation passed |
| 2 | Purity violations detected (blocked) |
| 3 | Validation error |

### Example Violations

```python
# VIOLATION: I/O in business logic
def calculate_total_price(items):
    # BAD: File I/O in calculation function
    config = open("config.json").read()
    tax_rate = json.loads(config)["tax_rate"]

    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)

# FIX: Separate I/O from logic
def load_tax_rate():  # Shell - handles I/O
    with open("config.json") as f:
        return json.load(f)["tax_rate"]

def calculate_total_price(items, tax_rate):  # Core - pure
    subtotal = sum(item.price for item in items)
    return subtotal * (1 + tax_rate)

# Usage in shell
tax_rate = load_tax_rate()
total = calculate_total_price(items, tax_rate)
```

### Benefits of Purity

1. **Testability**: Pure functions are trivial to test (no mocks needed)
2. **Predictability**: Same inputs always produce same outputs
3. **Composability**: Pure functions combine easily
4. **Parallelization**: No shared state concerns

## SOLID Validator

Enforces SOLID design principles via AST analysis. Located at `.claude/skills/sc-principles/scripts/validate_solid.py`.

### Checks

| Principle | Check | Threshold | Severity |
|-----------|-------|-----------|----------|
| SRP (Single Responsibility) | File length | > 300 lines | error |
| SRP (Single Responsibility) | Class public methods | > 5 | error |
| OCP (Open/Closed) | isinstance cascades | > 2 chained | error |
| LSP (Liskov Substitution) | NotImplementedError in overrides | Any | error |
| ISP (Interface Segregation) | Fat interfaces/protocols | > 7 methods | error |
| DIP (Dependency Inversion) | Direct instantiation in business logic | Any | warning |

### Usage

```bash
# Validate a directory
python .claude/skills/sc-principles/scripts/validate_solid.py --scope-root . --json

# Via skill command
/sc:principles --solid path/to/file.py
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Validation passed |
| 2 | SOLID violations detected (blocked) |
| 3 | Validation error |

### Notes

- ABC and Protocol base classes are excluded from LSP checks (abstract methods are expected)
- Private methods (`_name`) are excluded from SRP method count
- Shell paths (adapters, API, CLI) have relaxed DIP enforcement
- Uses a single-pass `CombinedSOLIDVisitor` for all 5 principles

## Let It Crash Validator

Enforces the "Let It Crash" error handling philosophy by detecting anti-patterns. Located at `.claude/skills/sc-principles/scripts/validate_crash.py`.

### Anti-Patterns

| Anti-Pattern | Description | Severity |
|--------------|-------------|----------|
| Bare `except:` | Catches all exceptions without specificity | error |
| `except Exception` without re-raise | Swallows exceptions silently | error |
| `except: pass` | Silent failure hiding bugs | error |
| Nested try/except cascades | Deeply nested error handling (> 2 levels) | error |

### Usage

```bash
# Validate a directory
python .claude/skills/sc-principles/scripts/validate_crash.py --scope-root . --json

# Via skill command
/sc:principles --crash path/to/file.py
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Validation passed |
| 2 | Crash violations detected (blocked) |
| 3 | Validation error |

### Notes

- Shell paths (adapters, API, handlers) have relaxed enforcement
- `except Exception` with re-raise (`raise` or `raise e`) is allowed
- Specific exception types (e.g., `except ValueError`) are always allowed
- `try/finally` blocks without `except` are not flagged

## Agent Validator

Validates agent markdown files against the v7 schema.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier (lowercase, hyphens) |
| `description` | string | Brief description (max 200 chars) |
| `tier` | enum | `core`, `trait`, or `extension` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Functional category |
| `triggers` | array | Keywords for agent selection |
| `tools` | array | Claude Code tools used |
| `priority` | integer | Selection priority (1-3) |
| `traits` | array | Default traits to apply |

### Usage

```bash
# Python validator (primary)
python scripts/validate_agents.py --verbose
python scripts/validate_agents.py --strict  # Warnings as errors

# JSON Schema validator
python scripts/validate_schema.py --verbose
```

### Validation Rules

1. **Name Format**: `^[a-z][a-z0-9-]*[a-z0-9]$` or single letter
2. **Unique Names**: No duplicate agent names across tiers
3. **Tier-Specific**:
   - Traits should NOT have `triggers` or `priority`
   - Core/Extension agents should have `triggers`
4. **Tool Validation**: Warns on unknown tool names
5. **Trait References**: Referenced traits must exist

## Iterative Quality Loop

The `--loop` flag enables iterative improvement until quality threshold is met.

### How It Works

```
┌─────────────┐
│ Execute Task│
└──────┬──────┘
       │
       ▼
┌─────────────┐     Score < 70
│Assess Quality├──────────────┐
└──────┬──────┘               │
       │                      │
       │ Score >= 70          ▼
       │              ┌───────────────┐
       ▼              │ Identify Fixes│
┌─────────────┐       └───────┬───────┘
│   Complete  │               │
└─────────────┘               │
       ▲                      │
       │                      ▼
       │              ┌───────────────┐
       │              │ Re-execute    │
       │              │ (max 5 iter)  │
       └──────────────┴───────────────┘
```

### Quality Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Correctness | 25% | Does it work as intended? |
| Completeness | 20% | Are all requirements met? |
| Maintainability | 20% | Easy to understand/modify? |
| Security | 15% | Free of vulnerabilities? |
| Performance | 10% | Efficient execution? |
| Testability | 10% | Can it be tested? |

### Configuration

Quality thresholds can be configured in `config/quality.yaml`:

```yaml
quality:
  target_score: 70
  max_iterations: 5
  stagnation_threshold: 3  # Stop if no improvement for N iterations

  dimensions:
    correctness:
      weight: 0.25
      min_score: 60
    completeness:
      weight: 0.20
      min_score: 50
    # ... etc
```

## CI Integration

All quality gates run in CI via `.github/workflows/ci.yml`:

```yaml
- name: Validate agent frontmatter
  run: python scripts/validate_agents.py --strict

- name: Validate agent JSON Schema
  run: |
    pip install jsonschema -q
    python scripts/validate_schema.py
```

## Bypass Options

For exceptional cases, gates can be bypassed:

```bash
# Skip specific validators
--skip-kiss          # Skip KISS complexity check
--skip-purity        # Skip purity check

# Environment variable
SUPERCLAUDE_STRICT=false  # Warnings-only mode
```

**Note**: Bypasses are logged. Use sparingly and document the reason.

## Best Practices

1. **Run Early**: Validate during development, not just in CI
2. **Fix Incrementally**: Address one violation at a time
3. **Understand Why**: Read the violation message before bypassing
4. **Refactor First**: Often violations indicate design issues
5. **Test After**: Ensure refactoring doesn't break functionality
