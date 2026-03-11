# Test Coverage Skill Import from Ocelot

**Date**: 2026-03-10
**Source**: `~/Desktop/Ocelot/.claude/commands/test-coverage.md`
**Target**: `.claude/skills/sc-test/SKILL.md` (enriched, not replaced)

## Import Summary

Enriched the existing `sc-test` skill with Ocelot's comprehensive test-coverage workflow. This was a merge, not a replacement -- SuperClaude's MCP integration and multi-language support were preserved while Ocelot's interactive workflow and detailed conventions were integrated.

## What Was Added from Ocelot

### 1. Interactive "Ask Early, Ask Often" Philosophy
- Philosophy section explaining liberal use of `AskUserQuestion`
- Decision points before writing tests, when gaps are large, and after coverage runs

### 2. Phase 1.4: Confirm Coverage Priorities
- AskUserQuestion checkpoint after gap report
- Options: highest-impact first, quick wins, specific module, dry run only
- Default file exclusions (protocols, migrations, init files, generated code)

### 3. Phase 2: Analyze Existing Test Patterns (new)
- Read test infrastructure files (conftest, jest.config, etc.)
- Find pattern examples for each gap file
- Identify available fixtures/helpers
- Classify functions by test type (unit/integration/E2E)

### 4. Phase 3: Detailed Test Writing Templates
- Full AAA pattern examples for Python, TypeScript, and Go
- Rules for all languages (mock only externals, Let It Crash in tests)
- Integration and E2E test writing guidance

### 5. Phase 4: Validate Tests (new)
- Run new tests only first
- Fix failures with source-vs-test classification
- Run full suite for regression check
- Lint test files (ruff, eslint, gofmt)

### 6. Phase 5.3: Iterative Coverage Loop
- AskUserQuestion to continue/stop/raise target/switch focus
- Maximum 5 iterations per --loop convention
- Re-run gap analysis between iterations

### 7. Phase 6: Summary Report Template
- Before/after coverage delta
- New/modified test files with counts
- Coverage by category
- Remaining gaps with reasons
- Verification commands

### 8. Enhanced Anti-Patterns
- Comprehensive DO NOT lists for test writing
- Explicit prohibition on modifying source code for testability
- KISS principle: no test utility frameworks for simple cases

## What Was Preserved from sc-test

- MCP integration (PAL + Rube) with usage patterns
- Multi-language coverage commands (Python, JS, Go, Rust)
- Flags system (all original flags preserved)
- Quick Start section
- Personas section
- Evidence requirements
- Web search via Rube MCP (--linkup flag)
- Tool coordination section

## What Was Generalized

| Ocelot-Specific | Generalized To |
|-----------------|----------------|
| `.venv/bin/python -m pytest` | `pytest` (framework-detected) |
| Ocelot module-to-test mapping table | Generic guidance to find closest test |
| Ocelot-specific fixture names | Framework-agnostic fixture discovery |
| `pyproject.toml` pytest config | Multi-framework config detection table |
| Ocelot file exclusions | Generic exclusion patterns |
| Python-only test templates | Python + TypeScript + Go templates |

## What Was Not Imported

- Ocelot-specific module-to-test mapping table (too project-specific)
- Ocelot-specific fixture documentation (project-specific)
- `pyproject.toml` `fail_under` references (project-specific)
- Hardcoded `.venv` paths (environment-specific)
