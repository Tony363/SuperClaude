---
name: sc-code-review
description: Multi-model consensus code review using PAL MCP. Reviews commits, staged changes, or branch diffs with prioritized findings across security, performance, quality, and architecture.
---

# Code Review Skill

Comprehensive code review using PAL MCP multi-model consensus. Reviews recent commits, staged changes, or branch comparisons with focus on security, quality, performance, and architecture.

## Quick Start

```bash
# Review last 5 commits (default)
/sc:code-review

# Review staged changes
/sc:code-review --staged

# Compare feature branch against main
/sc:code-review --branch main

# Security-focused review
/sc:code-review commits=3 --focus security

# Post review as PR comment
/sc:code-review --branch main --post-pr
```

## Behavioral Flow

1. **Parse** - Extract review mode, focus area, and commit range from arguments
2. **Validate** - Verify git state, branch existence, staged changes
3. **Discover** - List available models via `mcp__pal__listmodels`
4. **Gather** - Collect git diff, changed files, commit history
5. **Categorize** - Map changed files to review focus areas
6. **Review** - Run PAL MCP consensus with multi-model evaluation
7. **Format** - Present findings in GitHub PR comment style
8. **Post** - Optionally post to PR via `gh` CLI

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `commits` | int | 5 | Number of recent commits to review |
| `--staged` | bool | false | Review only staged changes |
| `--branch` | string | - | Compare current branch against target branch |
| `--focus` | string | full | Focus: security, performance, quality, architecture, full |
| `--post-pr` | bool | false | Post review as PR comment |
| `--models` | int | 2 | Number of models for consensus (2-5) |

## Review Modes

Modes are mutually exclusive:

| Mode | Trigger | Git Command |
|------|---------|-------------|
| Commits | Default or `commits=N` | `git diff -U10 HEAD~N..HEAD` |
| Staged | `--staged` | `git diff -U10 --cached` |
| Branch | `--branch <target>` | `git diff -U10 origin/<target>...HEAD` |

## Phase 1: Validate Git State

```bash
# Verify git repository
git rev-parse --is-inside-work-tree

# Get current branch
git branch --show-current
```

Mode-specific validation:

- **Commits**: Check `git rev-list --count HEAD` >= N
- **Staged**: Check `git diff --cached --name-only` is non-empty
- **Branch**: Check `git rev-parse --verify "origin/$TARGET"` exists

## Phase 2: Discover Models

Call `mcp__pal__listmodels` to get available models. Select top N by score, preferring different providers for diversity.

**Selection criteria:**
1. Sort by score descending
2. Pick from distinct providers when possible
3. Minimum 2 models for meaningful consensus

## Phase 3: Gather Git Context

Collect for the selected review mode:

| Data | Purpose |
|------|---------|
| `git diff -U10 ...` | Full diff with extended context |
| `git diff --stat ...` | Change statistics |
| `git log --oneline ...` | Commit summaries |
| Changed file list | File categorization |

## Phase 4: Categorize Changed Files

| Pattern | Category | Review Focus |
|---------|----------|--------------|
| `*.py`, `*.ts`, `*.go`, `*.rs` | Source Code | Security, SOLID, performance |
| `tests/**`, `*_test.*` | Test Code | Coverage, edge cases, assertions |
| `*.yml`, `*.yaml`, `*.toml` | Config | Security, correctness |
| `*requirements*`, `*package*` | Dependencies | Vulnerabilities, versions |
| `Dockerfile*`, `docker-compose*` | Infrastructure | Security, best practices |
| `*.md`, `*.rst` | Documentation | Accuracy, completeness |

Skip binary files (note them but exclude from diff review).

## Phase 5: Handle Large Diffs

If diff exceeds ~1000 lines:

1. **Group files by category** (source, tests, config, docs)
2. **Review each group separately** with PAL consensus
3. **Synthesize findings** into single report
4. **Deduplicate** overlapping issues

## Phase 6: Run PAL MCP Consensus

Use `mcp__pal__consensus` with discovered models.

**Consensus workflow:**
- `step 1`: Your initial analysis with the diff
- `step 2+`: Each model responds with findings
- `total_steps` = number of models + 1

**Review checklist by focus area:**

| Focus | Checks |
|-------|--------|
| security | Secrets, injection, auth, input validation, dependencies |
| performance | N+1 queries, complexity, caching, memory leaks |
| quality | SOLID, naming, error handling, types, dead code |
| architecture | Patterns, coupling, separation of concerns, testability |
| full | All of the above (default) |

**Fallback**: If consensus fails, use `mcp__pal__codereview` for single-model review.

## Phase 7: Format Output

```markdown
## Code Review: Multi-Model Consensus

**Review Mode**: [Commits (last N) | Staged Changes | Branch vs TARGET]
**Files Reviewed**: N files
**Lines Changed**: +X / -Y

---

### Executive Summary
[2-3 sentence overview]

---

### Critical Issues
> Must be addressed before merge

- [ ] **[FILE:LINE]** - [Issue description]
  - **Category**: Security/Performance/Bug Risk
  - **Severity**: Critical
  - **Recommendation**: [Specific fix]

### High Priority
> Should be addressed

- [ ] **[FILE:LINE]** - [Issue description]
  - **Category**: [Category]
  - **Recommendation**: [Specific fix]

### Medium Priority
> Recommended improvements

- [ ] **[FILE:LINE]** - [Issue description]
  - **Recommendation**: [Suggestion]

### Low Priority / Suggestions
> Nice to have

- [ ] [Suggestion]

---

### Positive Observations
- [Good pattern observed]

---

### Review Summary

| Category | Rating | Notes |
|----------|--------|-------|
| Security | X/5 | [Brief note] |
| Code Quality | X/5 | [Brief note] |
| Performance | X/5 | [Brief note] |
| Architecture | X/5 | [Brief note] |
| Test Coverage | X/5 | [Brief note] |

**Overall Assessment**: [APPROVE / REQUEST CHANGES / NEEDS DISCUSSION]

---

### Model Consensus

| Model | Key Findings |
|-------|--------------|
| [Model 1] | [Summary] |
| [Model 2] | [Summary] |

**Agreement Areas**: [Where models agreed]
**Divergent Views**: [Where models differed]
```

## Phase 8: Post to PR (Optional)

If `--post-pr` and in PR context:

```bash
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null)
gh pr comment $PR_NUMBER --body "<review output>"
```

## MCP Integration

### PAL MCP (Primary)

| Tool | When | Purpose |
|------|------|---------|
| `mcp__pal__listmodels` | Always | Discover available models |
| `mcp__pal__consensus` | Default | Multi-model code review consensus |
| `mcp__pal__codereview` | Fallback | Single-model code review |
| `mcp__pal__challenge` | Critical findings | Validate severity of critical issues |

### Rube MCP (Optional)

| Tool | When | Purpose |
|------|------|---------|
| `mcp__rube__RUBE_SEARCH_TOOLS` | `--notify` | Find notification tools |
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | `--notify` | Send review to Slack/Jira |

## Error Handling

| Scenario | Action |
|----------|--------|
| Not a git repo | Exit with error |
| No commits in range | Adjust N to available commits |
| No staged changes | Error with hint to `git add` |
| Branch not found | Error with available branches |
| PAL MCP unavailable | Fall back to `mcp__pal__codereview` |
| No models available | Error — PAL MCP not configured |

## Tool Coordination

- **Bash** - Git operations, PR posting
- **Read** - Source file inspection for context
- **Grep** - Pattern search in changed files
- **PAL MCP** - Multi-model consensus review
- **Rube MCP** - External notifications
