---
name: sc-pr-check
description: Run all local CI checks before creating a PR with interactive failure remediation. Use when validating code quality before pull requests, running pre-flight checks, or fixing CI failures locally.
---

# Pre-PR Check Skill

Run comprehensive local CI checks before PR creation. Auto-detects project tooling, runs all checks, and offers interactive fixes on failure.

## Quick Start

```bash
# Run all detected checks
/sc:pr-check

# Run specific check categories
/sc:pr-check --only lint,test

# Quick mode - skip slow checks (e2e, security)
/sc:pr-check --quick

# Fix mode - auto-fix what's possible
/sc:pr-check --fix

# Dry run - show what would be checked
/sc:pr-check --dry-run
```

## Behavioral Flow

1. **Detect** - Identify project tooling (language, linter, formatter, test runner, security scanner)
2. **Plan** - Build check sequence based on detected tools
3. **Execute** - Run checks sequentially, streaming output
4. **Remediate** - On failure, offer interactive fixes per check type
5. **Re-run** - After fixes, re-run all checks until green or user stops
6. **Report** - Summary of results and fixes applied

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--only` | string | all | Comma-separated: `lint`, `format`, `test`, `security`, `types`, `e2e`, `build` |
| `--quick` | bool | false | Skip slow checks (e2e, security scan) |
| `--fix` | bool | false | Auto-fix fixable issues without prompting |
| `--dry-run` | bool | false | Show detected checks without running |
| `--strict` | bool | false | Treat warnings as errors |

## Phase 1: Project Tooling Detection

Auto-detect the project's tooling by examining config files and package manifests.

### Detection Matrix

| Check Type | Python | JavaScript/TypeScript | Go | Rust |
|------------|--------|----------------------|-----|------|
| **Linter** | ruff, flake8, pylint | eslint, biome | golangci-lint | clippy |
| **Formatter** | ruff format, black | prettier, biome | gofmt | rustfmt |
| **Types** | mypy, pyright | tsc | (built-in) | (built-in) |
| **Tests** | pytest, unittest | jest, vitest, mocha | go test | cargo test |
| **Security** | bandit, pip-audit | npm audit, snyk | govulncheck | cargo audit |
| **Build** | - | tsc, vite build | go build | cargo build |
| **E2E** | - | playwright, cypress | - | - |

### Detection Strategy

```bash
# Python detection
[ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]

# JavaScript/TypeScript detection
[ -f "package.json" ] || [ -f "tsconfig.json" ]

# Go detection
[ -f "go.mod" ]

# Rust detection
[ -f "Cargo.toml" ]

# Check for specific tools in config files
grep -q "ruff" pyproject.toml 2>/dev/null      # Ruff
[ -f ".eslintrc*" ] || grep -q "eslint" package.json 2>/dev/null  # ESLint
```

### Detection Output

```
## Project Tooling Detected

| Category | Tool | Config | Status |
|----------|------|--------|--------|
| Language | Python 3.12 | pyproject.toml | OK |
| Linter | Ruff | pyproject.toml [tool.ruff] | OK |
| Formatter | Ruff Format | pyproject.toml [tool.ruff] | OK |
| Type Check | mypy | pyproject.toml [tool.mypy] | OK |
| Tests | pytest | pyproject.toml [tool.pytest] | OK |
| Security | bandit | .bandit | OK |
| E2E | playwright | playwright.config.ts | OK |

Running 7 checks...
```

## Phase 2: Check Execution

Run checks in dependency order:

| Step | Check | Rationale |
|------|-------|-----------|
| 1 | Linter | Catch syntax/style errors first (fastest) |
| 2 | Formatter | Ensure consistent formatting |
| 3 | Type checker | Catch type errors before runtime |
| 4 | Unit/Integration tests | Verify correctness |
| 5 | Security scan | Catch vulnerabilities |
| 6 | Build | Verify compilation |
| 7 | E2E tests | Full integration (slowest, skipped with --quick) |

### Execution Pattern

For each check:
1. Display step number and check name: `[1/7] Running Ruff linter...`
2. Execute the command with timeout
3. Capture exit code and output
4. On success: show green checkmark, move to next
5. On failure: enter remediation flow

## Phase 3: Interactive Remediation

When a check fails, identify the failure type and offer targeted fixes.

### Lint Failures

```
[1/7] Ruff linter... FAILED (3 errors)

  src/api/routes.py:15:1 F401 unused import
  src/models/user.py:8:5 E712 comparison to True
  src/utils/helpers.py:22:80 E501 line too long

Actions:
  [f] Auto-fix with `ruff check . --fix` (fixes 2 of 3)
  [m] Manually fix remaining issues
  [s] Skip and continue
  [q] Quit
```

### Test Failures

```
[4/7] Tests... FAILED (2 failures)

  FAILED tests/test_api.py::test_create_user - AssertionError
  FAILED tests/test_auth.py::test_login_expired - TimeoutError

Actions:
  [a] Analyze and fix failing tests
  [r] Re-run failed tests only
  [s] Skip and continue
  [q] Quit
```

### Security Failures

```
[5/7] Security scan... FOUND 2 issues

  HIGH: SQL injection risk in src/api/users.py:45 (B608)
  LOW:  Assert used in production code src/utils/debug.py:12 (B101)

Actions:
  [a] Analyze and remediate issues
  [i] Show details for each finding
  [s] Skip and continue
  [q] Quit
```

### Fix Type Reference

| Check | Auto-fixable | Manual Fix Needed |
|-------|-------------|-------------------|
| Lint | Most style issues | Logic errors, unused code decisions |
| Format | All formatting | None |
| Types | None | Type annotations, casts |
| Tests | Some assertion fixes | Logic bugs, mock updates |
| Security | Some patterns | Architecture changes |
| Build | Dependency installs | Code errors |
| E2E | Selector updates | Flow changes |

## Phase 4: Re-run After Fixes

After applying any fix:
1. Re-run **all** checks (not just the failed one)
2. Continue the fix loop until all pass or user quits
3. Track all fixes applied during the session

## Phase 5: Results Report

```
## PR Check Results

**Status**: ALL PASSED | X FAILED
**Duration**: Ns

### Check Results

| Step | Check | Status | Duration |
|------|-------|--------|----------|
| 1/7 | Ruff linter | PASSED | 1.2s |
| 2/7 | Ruff formatter | PASSED | 0.8s |
| 3/7 | Type check | PASSED | 3.4s |
| 4/7 | Tests (48 passed) | PASSED | 12.1s |
| 5/7 | Security scan | PASSED | 2.3s |
| 6/7 | Build | PASSED | 5.6s |
| 7/7 | E2E tests | SKIPPED | --quick |

### Fixes Applied (if any)
- Auto-fixed 3 lint errors (ruff --fix)
- Fixed test assertion in test_create_user
- Remediated B608 SQL injection in users.py

### Next Steps
- Run `/sc:git commit` to commit changes
- Run `/sc:readme` to update documentation
- Create PR with `gh pr create`
```

## MCP Integration

### PAL MCP

| Tool | When to Use | Purpose |
|------|-------------|---------|
| `mcp__pal__debug` | Test failures | Root cause analysis for failing tests |
| `mcp__pal__codereview` | Security findings | Validate security remediation |
| `mcp__pal__precommit` | Final validation | Multi-model pre-commit check |

### PAL Usage Patterns

```bash
# Pre-commit validation after all checks pass
mcp__pal__precommit(
    path="/path/to/repo",
    step="Validating all changes before PR",
    findings="Lint, test, security, type check results",
    confidence="high"
)

# Debug complex test failure
mcp__pal__debug(
    step="Investigating intermittent test failure in test_auth",
    hypothesis="Race condition in async test setup",
    confidence="medium"
)
```

### Rube MCP

| Tool | When to Use | Purpose |
|------|-------------|---------|
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | Notifications | Post results to Slack, update Jira |

## Tool Coordination

- **Bash** - Execute linters, formatters, test runners, security scanners
- **Glob** - Detect config files for tooling identification
- **Grep** - Parse failure output, find config patterns
- **Read** - Read failing test files, security findings
- **Edit** - Apply auto-fixes

## Related Skills

- `/sc:test` - Detailed test execution and coverage
- `/sc:log-fix` - Debug from log analysis
- `/sc:git` - Git workflow operations
- `/sc:analyze` - Deeper code quality analysis
