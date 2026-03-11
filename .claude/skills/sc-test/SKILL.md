---
name: sc-test
description: Execute tests with coverage analysis, gap identification, test generation, and automated quality reporting. Use when running tests, analyzing coverage, generating missing tests, or debugging test failures.
---

# Testing & Coverage Skill

Test execution with coverage analysis, interactive gap identification, test generation, and iterative coverage improvement.

## Quick Start

```bash
# Run all tests
/sc:test

# Unit tests with coverage
/sc:test src/components --type unit --coverage

# Coverage gap analysis - identify untested code
/sc:test --gap-analysis --target 80

# Generate missing tests to reach target coverage
/sc:test --generate --target 80 --module src/services

# Watch mode with auto-fix
/sc:test --watch --fix

# Fix existing failures before adding coverage
/sc:test --fix-first --generate --target 80

# Web search for testing guidance (uses Rube MCP's LINKUP_SEARCH)
/sc:test --linkup --query "pytest asyncio best practices"
```

## Philosophy: Ask Early, Ask Often

**This skill liberally uses `AskUserQuestion` at decision points.** Test coverage involves tradeoffs between speed and thoroughness. Validate priorities rather than guessing what the user wants covered.

- **Before** writing tests -- confirm which modules to prioritize
- **When** gaps are large -- ask where to focus effort first
- **When** source code looks buggy -- ask before fixing vs just testing
- **After** coverage run -- ask about iteration vs stopping

## Behavioral Flow

1. **Discover** - Categorize tests using runner patterns
2. **Configure** - Set up test environment and parameters
3. **Execute** - Run tests with real-time progress tracking
4. **Analyze** - Generate coverage reports and diagnostics
5. **Confirm Priorities** - Interactive checkpoint: ask user what to tackle
6. **Study Patterns** - Read test infrastructure and existing conventions
7. **Generate** - Write missing tests following project conventions
8. **Validate** - Run new tests, fix failures, lint
9. **Verify Coverage** - Re-run coverage and compare before/after
10. **Iterate** - Ask user: continue, stop, or change focus
11. **Report** - Provide recommendations and quality metrics

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | string | all | unit, integration, e2e, all |
| `--coverage` | bool | false | Generate coverage report |
| `--watch` | bool | false | Continuous watch mode |
| `--fix` | bool | false | Auto-fix simple failures |
| `--gap-analysis` | bool | false | Identify coverage gaps without generating tests |
| `--generate` | bool | false | Generate missing tests to reach target |
| `--target` | int | 80 | Coverage percentage target |
| `--module` | string | - | Restrict scope to a specific module |
| `--fix-first` | bool | false | Fix existing failures before generating new tests |
| `--dry-run` | bool | false | Show gap analysis and test plan without writing |
| `--linkup` | bool | false | Web search for guidance (via Rube MCP) |
| `--query` | string | - | Search query for LINKUP_SEARCH |

## Personas Activated

- **qa-specialist** - Test analysis and quality assessment

## MCP Integration

### PAL MCP (Quality & Debugging)

| Tool | When to Use | Purpose |
|------|-------------|---------|
| `mcp__pal__debug` | Test failures | Root cause analysis for failing tests |
| `mcp__pal__codereview` | Test quality | Review test coverage and quality |
| `mcp__pal__thinkdeep` | Complex failures | Multi-stage investigation of flaky tests |
| `mcp__pal__consensus` | Test strategy | Multi-model validation of testing approach |
| `mcp__pal__apilookup` | Framework docs | Get current testing framework documentation |

### PAL Usage Patterns

```bash
# Debug failing test
mcp__pal__debug(
    step="Investigating intermittent test failure",
    hypothesis="Race condition in async setup",
    confidence="medium",
    relevant_files=["/tests/test_api.py"]
)

# Review test quality
mcp__pal__codereview(
    review_type="full",
    findings="Test coverage, assertion quality, edge cases",
    focus_on="test isolation and mocking patterns"
)

# Validate testing strategy
mcp__pal__consensus(
    models=[{"model": "gpt-5.2", "stance": "neutral"}, {"model": "gemini-3-pro", "stance": "neutral"}],
    step="Evaluate: Is integration testing sufficient for this feature?"
)
```

### Rube MCP (Automation & Research)

| Tool | When to Use | Purpose |
|------|-------------|---------|
| `mcp__rube__RUBE_SEARCH_TOOLS` | CI/CD integration | Find test reporting tools |
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | Notifications | Post results to Slack, update tickets |
| `mcp__rube__RUBE_REMOTE_WORKBENCH` | Bulk processing | Analyze large test result sets |

### Rube Usage Patterns

```bash
# Search for testing best practices (--linkup flag uses LINKUP_SEARCH)
mcp__rube__RUBE_MULTI_EXECUTE_TOOL(tools=[
    {"tool_slug": "LINKUP_SEARCH", "arguments": {
        "query": "pytest fixtures best practices",
        "depth": "deep",
        "output_type": "sourcedAnswer"
    }}
])

# Post test results to Slack
mcp__rube__RUBE_MULTI_EXECUTE_TOOL(tools=[
    {"tool_slug": "SLACK_SEND_MESSAGE", "arguments": {
        "channel": "#ci-results",
        "text": "Test run complete: 95% pass rate, 87% coverage"
    }}
])
```

## Evidence Requirements

This skill requires evidence. You MUST:
- Show test execution output and pass/fail counts
- Reference coverage metrics when `--coverage` used
- Provide actual error messages for failures

## Test Type Definitions

| Type | What It Tests | Markers |
|------|---------------|---------|
| **Unit** | Single function/class in isolation, mocked dependencies | (none or framework default) |
| **Integration** | Multiple components together, real DB via fixtures | `@pytest.mark.integration`, `describe("integration")` |
| **E2E** | Full pipeline with real or mocked external APIs | `@pytest.mark.slow`, `@pytest.mark.e2e` |

---

## Phase 1: Coverage Baseline

### 1.1 Run Current Coverage Report

Detect the test framework and run coverage:

```bash
# Python (pytest)
pytest --cov=src --cov-report=term-missing --cov-report=json:coverage.json -q --tb=no

# JavaScript (jest/vitest)
npx jest --coverage --coverageReporters=json-summary
# or: npx vitest run --coverage

# Go
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out

# Rust
cargo tarpaulin --out json
```

### 1.2 Parse Coverage Gaps

Read the coverage report to extract:
- Per-file coverage percentage
- Uncovered line numbers per file
- Total project coverage

If `--module` is provided, filter coverage data to the specified module only.

### 1.3 Build Gap Report

Create a ranked list of files by coverage gap (lowest coverage first):

```
## Coverage Gap Report

**Current Coverage**: 52% | **Target**: 80% | **Gap**: 28%

| File | Coverage | Missing Lines | Priority |
|------|----------|---------------|----------|
| src/services/payment.py | 0% | 1-120 | CRITICAL |
| src/utils/validator.py | 15% | 12-45, 67-89 | HIGH |
| src/api/routes/users.py | 42% | 55-70, 88-102 | MEDIUM |
```

**Priority rules:**
- CRITICAL: 0% coverage (no tests at all)
- HIGH: < 30% coverage
- MEDIUM: 30-60% coverage
- LOW: > 60% but below target

### 1.4 Confirm Coverage Priorities with User

After building the gap report, ask the user what to prioritize:

```
AskUserQuestion:
  question: "Found <N> files below target. Which should I tackle first?"
  header: "Priority"
  multiSelect: false
  options:
    - label: "Highest-impact first (Recommended)"
      description: "<N CRITICAL + M HIGH priority files -- start with 0% coverage modules>"
    - label: "Quick wins first"
      description: "Start with files that need only 1-2 tests to reach target"
    - label: "Specific module"
      description: "I want to focus on a specific area of the codebase"
    - label: "Dry run only"
      description: "Just show me the gap report -- don't write any tests yet"
```

**If "Specific module"**: Ask which module to focus on.
**If "Dry run only"**: Present the gap report and stop.

**Skip these files** by default:
- Protocol/interface definitions with no logic
- Migration files
- `__init__.py` / `index.ts` with only re-exports
- Generated code (protobuf, OpenAPI clients)

---

## Phase 2: Analyze Existing Test Patterns

Before writing ANY tests, study the project's conventions.

### 2.1 Read Test Infrastructure

Discover and read test setup files:

| Framework | Files to Read |
|-----------|---------------|
| pytest | `conftest.py`, `pyproject.toml` `[tool.pytest]` |
| jest | `jest.config.*`, `setupTests.*`, `__mocks__/` |
| vitest | `vitest.config.*`, `setup.*` |
| Go | `*_test.go` helpers, `testdata/` |
| Rust | `tests/common/mod.rs` |

### 2.2 Find Pattern Examples

For each gap file, find the closest existing test as a template:
- Search for tests in the same directory/module
- Identify import patterns, fixture usage, assertion style
- Note any test base classes or shared helpers

### 2.3 Identify Available Fixtures/Helpers

Map available test fixtures to their use cases. Build a reference table:

```
| Fixture/Helper | Purpose | Used By |
|----------------|---------|---------|
| db_session | Database access | Integration tests |
| mock_api_client | Mock external API | Unit tests |
| ...            | ...     | ...     |
```

### 2.4 Classify Functions for Test Type

| Function Characteristic | Test Type |
|------------------------|-----------|
| Pure function (no I/O, no DB) | Unit test |
| Uses validation only | Unit test |
| Calls database/ORM | Integration test (needs DB fixture) |
| Calls external API | Unit test with mock |
| HTTP endpoint handler | Integration test |
| Full pipeline execution | E2E test |

---

## Phase 3: Generate Tests by Type

Process gaps in priority order (CRITICAL first). For each file:

### 3.1 Read the Source Module

Identify:
- All public functions and classes
- Their signatures, return types, and dependencies
- Which dependencies need mocking vs real fixtures
- Edge cases: empty inputs, None values, error conditions

### 3.2 Write Unit Tests

Follow the AAA pattern (Arrange/Act/Assert):

```python
# Python example
class TestFunctionName:
    """Tests for function_name."""

    # Happy path
    async def test_returns_expected_result(self):
        """function_name returns correct output for valid input."""
        # Arrange
        input_data = ...

        # Act
        result = await function_under_test(input_data)

        # Assert
        assert result.field == expected_value

    # Edge cases
    async def test_handles_empty_input(self):
        """function_name handles empty input correctly."""
        ...

    # Error conditions (Let It Crash - verify errors propagate)
    async def test_raises_on_invalid_input(self):
        """function_name raises ValueError for invalid input."""
        with pytest.raises(ValueError):
            await function_under_test(invalid_input)
```

```typescript
// TypeScript/Jest example
describe('functionName', () => {
  it('returns expected result for valid input', () => {
    // Arrange
    const input = { ... };

    // Act
    const result = functionName(input);

    // Assert
    expect(result.field).toBe(expectedValue);
  });

  it('throws on invalid input', () => {
    expect(() => functionName(invalidInput)).toThrow();
  });
});
```

```go
// Go example
func TestFunctionName(t *testing.T) {
    t.Run("returns expected result", func(t *testing.T) {
        // Arrange
        input := ...

        // Act
        result, err := FunctionName(input)

        // Assert
        if err != nil {
            t.Fatalf("unexpected error: %v", err)
        }
        if result.Field != expected {
            t.Errorf("got %v, want %v", result.Field, expected)
        }
    })
}
```

**Rules for all languages:**
- Use AAA pattern (Arrange/Act/Assert) with comments
- Docstrings/descriptions describe expected behavior, not implementation
- Mock only external dependencies (APIs, DB, network)
- Do NOT add try/except or try/catch in tests (Let It Crash principle)
- Do NOT modify source code to make tests pass (unless there's a genuine bug)

### 3.3 Write Integration Tests

For tests requiring database or multiple components:

- Mark with appropriate marker (`@pytest.mark.integration`, tagged describe blocks)
- Use real DB fixtures or test containers
- Test real component interactions, not mocked ones
- Clean up is automatic via fixture teardown

### 3.4 Write E2E Tests

For full pipeline or API flow tests:

- Mark with slow/e2e marker
- Use HTTP test clients (httpx AsyncClient, supertest, net/http/httptest)
- Mock external API responses via fixtures
- Test full request/response cycle including auth
- Verify response schema matches expected models

---

## Phase 4: Validate Tests

### 4.1 Run New Tests Only

```bash
# Run just the newly created/modified test file
pytest tests/test_<area>/test_<module>.py -v --tb=short
npx jest tests/<module>.test.ts --verbose
go test -v -run TestNewFunction ./pkg/...
```

### 4.2 Fix Failures

If tests fail:
1. Read the error output carefully
2. Determine if the failure is in the TEST or the SOURCE code
3. Fix the test if the source code behavior is correct
4. NEVER modify source code to make tests pass (unless there's a genuine bug)
5. If source code has a bug -- ask the user before fixing it vs just testing current behavior

### 4.3 Run Full Suite

After all new tests pass individually:

```bash
# Full test suite - ensure no regressions
pytest -v --tb=short
npx jest --verbose
go test ./...
```

### 4.4 Lint Test Files

```bash
# Python
ruff check tests/ --fix && ruff format tests/

# TypeScript/JavaScript
npx eslint tests/ --fix && npx prettier tests/ --write

# Go
gofmt -w *_test.go
```

---

## Phase 5: Coverage Verification

### 5.1 Re-run Coverage

Run the same coverage command from Phase 1 to get updated metrics.

### 5.2 Compare Before/After

Report coverage delta:

```
## Coverage Report

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Total Coverage | 52% | 78% | +26% |
| Files with 0% | 5 | 1 | -4 |

### Per-File Improvements

| File | Before | After | Tests Added |
|------|--------|-------|-------------|
| src/services/payment.py | 0% | 85% | 8 |
| src/utils/validator.py | 15% | 72% | 5 |
```

### 5.3 Ask Whether to Iterate

If coverage is still below target, ask the user rather than auto-iterating:

```
AskUserQuestion:
  question: "Coverage is at <M%> (target: <N%>). Want to continue adding tests?"
  header: "Iterate"
  multiSelect: false
  options:
    - label: "Continue -- add more tests"
      description: "<K files remaining below target -- next batch would cover <list>"
    - label: "Good enough -- stop here"
      description: "Accept current coverage and move on"
    - label: "Raise the target"
      description: "Current coverage exceeded expectations -- set a higher target"
    - label: "Switch focus"
      description: "Cover a different area instead of continuing the current batch"
```

If continuing:
1. Re-run Phase 1 to identify remaining gaps
2. Focus on files with the largest uncovered line counts
3. Repeat Phases 3-5 until target is reached or user stops

Maximum iterations: 5 (per `--loop` convention).

---

## Phase 6: Summary

Present final results:

```
## Test Coverage Update Summary

**Target**: N%
**Achieved**: M%
**Tests Added**: X unit, Y integration, Z e2e

### New Test Files Created
- tests/test_<area>/test_<module>.py (N tests)
- ...

### Modified Test Files
- tests/test_<area>/test_<module>.py (+N tests)
- ...

### Coverage by Category
| Category | Coverage | Status |
|----------|----------|--------|
| src/services/ | ??% | OK/NEEDS WORK |
| src/routers/ | ??% | OK/NEEDS WORK |
| src/models/ | ??% | OK/NEEDS WORK |

### Remaining Gaps (if any)
- src/services/transformer.py - Excluded (needs full pipeline data)
- ...

### Verification Commands
<framework-specific commands to re-run tests and coverage>
```

---

## Anti-Patterns to Avoid

### DO NOT write tests that:
- Test private/internal methods directly (test via public API)
- Duplicate existing test coverage (check first!)
- Require real API keys to pass (mock external services)
- Depend on test execution order
- Use `time.sleep()` for async synchronization
- Catch exceptions that should propagate (Let It Crash)
- Add defensive `if x is not None` checks (test the contract)

### DO NOT:
- Modify source code to make it "more testable" (test what exists)
- Add type stubs or docstrings to source files (only touch test files)
- Create test utility frameworks or base classes (KISS)
- Write parameterized tests for < 3 cases (just write separate tests)
- Add comments or docstrings to code you didn't change

---

## Coverage Analysis (standalone)

When only `--coverage` is enabled (without `--generate`):
- Line coverage metrics
- Branch coverage metrics
- Uncovered code identification
- Coverage trend comparison

---

## Tool Coordination

- **Bash** - Test runner execution
- **Glob** - Test file discovery
- **Grep** - Result parsing, failure analysis
- **Read** - Source and test file inspection
- **Write** - New test files, coverage reports
- **Edit** - Extending existing test files
- **AskUserQuestion** - Priority confirmation, iteration decisions
