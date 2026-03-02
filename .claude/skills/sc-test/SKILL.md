---
name: sc-test
description: Execute tests with coverage analysis, gap identification, test generation, and automated quality reporting. Use when running tests, analyzing coverage, generating missing tests, or debugging test failures.
---

# Testing & QA Skill

Test execution with coverage analysis, gap identification, test generation, and quality reporting.

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

## Behavioral Flow

1. **Discover** - Categorize tests using runner patterns
2. **Configure** - Set up test environment and parameters
3. **Execute** - Run tests with real-time progress tracking
4. **Analyze** - Generate coverage reports and diagnostics
5. **Gap Analysis** - Identify untested code when `--gap-analysis` or `--generate`
6. **Generate** - Write missing tests when `--generate`
7. **Report** - Provide recommendations and quality metrics

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

# Update Jira with test status
mcp__rube__RUBE_MULTI_EXECUTE_TOOL(tools=[
    {"tool_slug": "JIRA_ADD_COMMENT", "arguments": {
        "issue_key": "PROJ-123",
        "body": "All tests passing. Ready for review."
    }}
])

## Evidence Requirements

This skill requires evidence. You MUST:
- Show test execution output and pass/fail counts
- Reference coverage metrics when `--coverage` used
- Provide actual error messages for failures

## Test Types

### Unit Tests (`--type unit`)
- Isolated component testing
- Mock dependencies
- Fast execution

### Integration Tests (`--type integration`)
- Component interaction testing
- Database/API integration
- Service dependencies

### E2E Tests (`--type e2e`)
- Full user flow testing
- Browser automation guidance
- Cross-platform validation

## Coverage Analysis

When `--coverage` is enabled:
- Line coverage metrics
- Branch coverage metrics
- Uncovered code identification
- Coverage trend comparison

## Coverage Gap Analysis

When `--gap-analysis` or `--generate` is used, perform deep coverage gap identification.

### Phase 1: Coverage Baseline

Run current coverage and parse the report:

```bash
# Python (pytest)
pytest --cov=src --cov-report=term-missing --cov-report=json:coverage.json -q --tb=no

# JavaScript (jest/vitest)
npx jest --coverage --coverageReporters=json-summary

# Go
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
```

### Phase 2: Build Gap Report

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

**Priority Ranking:**
- CRITICAL: 0% coverage (no tests at all)
- HIGH: < 30% coverage
- MEDIUM: 30-60% coverage
- LOW: > 60% but below target

### Phase 3: Analyze Test Patterns

Before writing tests, study existing conventions:

1. **Read test infrastructure** - `conftest.py`, test fixtures, helpers
2. **Find pattern examples** - Use closest existing test as template
3. **Identify fixtures** - Map available fixtures to their use cases
4. **Classify functions** - Determine test type per function:

| Function Characteristic | Test Type |
|------------------------|-----------|
| Pure function (no I/O) | Unit test |
| Uses validation only | Unit test |
| Calls database/ORM | Integration test (needs DB fixture) |
| Calls external API | Unit test with mock |
| HTTP endpoint handler | Integration test |
| Full pipeline execution | E2E test |

### Phase 4: Generate Tests

Process gaps in priority order. For each file:

1. **Read the source module** - Identify public functions, signatures, dependencies
2. **Determine test type** - Unit, integration, or E2E
3. **Write tests following project conventions**:
   - Use AAA pattern (Arrange/Act/Assert)
   - Group tests in `class Test*` per function
   - Mock only external dependencies
   - Test happy path, edge cases, and error conditions
   - Let errors propagate (Let It Crash principle)
4. **Run new tests** - Verify they pass
5. **Lint test files** - Ensure clean formatting

### Phase 5: Coverage Verification

After generating tests:

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

### Test Generation Anti-Patterns

DO NOT:
- Test private/internal methods directly (test via public API)
- Duplicate existing test coverage
- Require real API keys to pass
- Depend on test execution order
- Catch exceptions that should propagate (Let It Crash)
- Modify source code to make it "more testable"
- Create test utility frameworks (KISS)

## Examples

### Targeted Unit Tests
```
/sc:test src/utils --type unit --coverage
```

### Continuous Development
```
/sc:test --watch --fix
# Real-time feedback during development
```

### Integration Suite
```
/sc:test --type integration --coverage
```

### Coverage Gap Analysis
```
/sc:test --gap-analysis --target 80
# Shows gap report without generating tests
```

### Generate Missing Tests
```
/sc:test --generate --target 80 --module src/services
# Generates tests to reach 80% coverage for services module
```

### Fix Then Generate
```
/sc:test --fix-first --generate --target 75
# Fix existing failures, then generate tests to reach 75%
```

### Web Research
```
/sc:test --linkup --query "vitest react testing library patterns"
```

## Tool Coordination

- **Bash** - Test runner execution
- **Glob** - Test file discovery
- **Grep** - Result parsing, failure analysis
- **Write** - Coverage reports, test summaries
