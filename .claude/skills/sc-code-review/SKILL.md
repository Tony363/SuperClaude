---
name: sc-code-review
description: Interactive multi-model consensus code review using PAL MCP. Reviews commits, staged changes, or branch diffs with user-directed scope and interactive decision points.
allowed-tools: AskUserQuestion, Bash, Read, Edit, Glob, Grep, mcp__pal__consensus, mcp__pal__codereview, mcp__pal__listmodels, mcp__pal__challenge
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

## Philosophy: Ask Early, Ask Often

**This skill liberally uses `AskUserQuestion` at every decision point.** Code review is subjective — what matters depends on context, and assumptions about reviewer priorities are frequently wrong. The cost of asking is low; the cost of reviewing the wrong scope or missing what the user cares about is high.

**Interactive checkpoints:**
- **Before** reviewing — confirm the review scope and what the user cares about
- **When** the diff is large — let the user choose what to focus on first
- **When** categorization is ambiguous — ask about severity levels
- **When** models disagree — let the user break the tie on issue severity
- **After** findings — ask what to do next (fix, re-review, post to PR)
- **When** tradeoffs exist — present them explicitly instead of picking silently
- **For** critical/high findings — validate severity with user before finalizing

The user should feel like they're directing the review, not receiving a fire-and-forget report.

## Behavioral Flow

1. **Parse** - Extract review mode, focus area, and commit range from arguments
2. **Validate** - Verify git state, branch existence, staged changes
3. **Confirm Scope** - Interactive scope confirmation with user
4. **Discover** - List available models via `mcp__pal__listmodels`
5. **Gather** - Collect git diff, changed files, commit history
6. **Categorize** - Map changed files to review focus areas
7. **Handle Large Diffs** - Interactive chunking strategy for large changes
8. **Review** - Run PAL MCP consensus with multi-model evaluation
9. **Resolve Disagreements** - User adjudicates model conflicts
10. **Validate Findings** - User confirms critical/high severity items
11. **Format** - Present findings in GitHub PR comment style
12. **Follow-up** - Ask user what to do next (fix, deep-dive, post to PR)
13. **Post** - Optionally post to PR via `gh` CLI

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

## Phase 1b: Confirm Review Scope

After gathering git context, present a summary and let the user confirm or adjust:

```
AskUserQuestion:
  question: "Here's what I'll be reviewing. Does this scope look right?"
  header: "Scope"
  multiSelect: false
  options:
    - label: "Looks good — proceed"
      description: "<N files changed, +X/-Y lines, commits/staged/branch summary>"
    - label: "Too much — narrow scope"
      description: "I only want to review a subset of these changes"
    - label: "Too little — expand scope"
      description: "Include more commits or compare against a different branch"
    - label: "Different focus"
      description: "I want to focus on a specific area (security, performance, etc.)"
```

**If "Too much — narrow scope"**: Ask which files or directories to focus on:

```
AskUserQuestion:
  question: "Which areas should I focus the review on?"
  header: "Focus"
  multiSelect: true
  options:
    - label: "Backend (app/)"
      description: "<N files, +X/-Y lines in app/>"
    - label: "Frontend (frontend/)"
      description: "<N files, +X/-Y lines in frontend/>"
    - label: "Tests"
      description: "<N files, +X/-Y lines in tests/>"
    - label: "Config/Infra"
      description: "<N files in Docker, CI, config>"
```

**If "Too little — expand scope"**: Ask how to expand (more commits, different branch).

**If "Different focus"**: Ask which review focus area to use, overriding the `--focus` flag.

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

If diff exceeds ~1000 lines, ask user how to handle:

```
AskUserQuestion:
  question: "The diff is large (~<N> lines across <M> files). How should I handle it?"
  header: "Large diff"
  multiSelect: false
  options:
    - label: "Review in chunks by category (Recommended)"
      description: "Group files by type (backend, frontend, tests, config) and review each separately"
    - label: "Focus on highest-risk files only"
      description: "Skip low-risk changes (docs, tests, config) and focus on production code"
    - label: "Review everything in one pass"
      description: "Send the full diff to models — may lose detail on individual files"
    - label: "Let me pick specific files"
      description: "I'll tell you exactly which files to review"
```

**If "Let me pick specific files"**:
- List all changed files with their stats
- Ask user to select which files to review
- Scope the diff down accordingly

**If "Review in chunks by category"**:
1. Group files by category (source, tests, config, docs)
2. Review each group separately with PAL consensus
3. Synthesize findings into single report
4. Deduplicate overlapping issues

**If "Focus on highest-risk files only"**:
- Filter out documentation, configuration, and test files
- Focus consensus on production source code only

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

## Phase 6a: Present Model Disagreements

If models disagree on the severity or existence of an issue, **do NOT resolve the disagreement yourself**. Present each significant disagreement:

```
AskUserQuestion:
  question: "Models disagreed on <specific issue>. How should this be classified?"
  header: "Severity"
  multiSelect: false
  options:
    - label: "<Model A's severity> (e.g., Critical)"
      description: "<Model A> flagged this as <severity> because: <reasoning>"
    - label: "<Model B's severity> (e.g., Low)"
      description: "<Model B> considers this <severity> because: <reasoning>"
    - label: "Dismiss this finding"
      description: "This isn't actually an issue — it's intentional or acceptable"
```

Repeat for each significant disagreement (up to 4 per `AskUserQuestion` call). Skip for minor differences that don't change the severity tier.

## Phase 6b: Validate Critical/High Findings

If any findings are classified as **Critical** or **High**, present them to the user for confirmation before including in the final report. False positives at these severity levels erode trust:

```
AskUserQuestion:
  question: "I found <N> critical/high issues. Do these look like real problems, or should I reclassify any?"
  header: "Validate"
  multiSelect: true
  options:
    - label: "<Issue 1 summary>"
      description: "[FILE:LINE] — <brief description>. Classified as <severity>"
    - label: "<Issue 2 summary>"
      description: "[FILE:LINE] — <brief description>. Classified as <severity>"
    - label: "<Issue 3 summary>"
      description: "[FILE:LINE] — <brief description>. Classified as <severity>"
    - label: "All look correct"
      description: "Keep all critical/high classifications as-is"
```

**Interpretation:**
- Selected items are confirmed as real issues — keep them at current severity
- Unselected critical/high items should be downgraded to Medium with a note
- If "All look correct" is selected, keep everything as-is

**Skip this question** if there are no Critical or High findings.

**Use `mcp__pal__challenge` for validation**:
- For each critical/high finding, run `mcp__pal__challenge` to validate the severity
- Present both the original finding and the challenge result
- Let the user make the final call on severity

Example challenge prompt:
```
"The code review identified this as a Critical security issue: <issue description>.
Challenge this finding: Is it actually critical? Could it be a false positive?
What's the real-world exploitability? What's the actual severity?"
```

This adds an adversarial validation layer to prevent false positives.

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

## Phase 8: Post-Review Follow-Up

Always ask the user what they want to do next after presenting the review:

```
AskUserQuestion:
  question: "Review complete (<overall assessment>). What would you like to do next?"
  header: "Next"
  multiSelect: false
  options:
    - label: "Auto-fix issues"
      description: "Attempt to fix all critical and high issues automatically"
    - label: "Review a specific file in detail"
      description: "Deep-dive into one file that needs closer inspection"
    - label: "Post to PR"
      description: "Post this review as a comment on the current PR"
    - label: "Re-review with different models"
      description: "Run the review again with different model consensus"
    - label: "Done"
      description: "Review is complete — no further action needed"
```

**If "Auto-fix issues"**: Ask which severity levels to fix:

```
AskUserQuestion:
  question: "Which issues should I attempt to fix?"
  header: "Fix scope"
  multiSelect: true
  options:
    - label: "Critical issues (<N>)"
      description: "Must-fix items that block merge"
    - label: "High priority (<N>)"
      description: "Should-fix items"
    - label: "Medium priority (<N>)"
      description: "Recommended improvements"
    - label: "All issues"
      description: "Fix everything that can be automated"
```

Then attempt fixes using `Edit` and report results. After each fix, ask if the user wants to continue or review the changes.

**If "Review a specific file in detail"**:
- Ask which file from the changed files list
- Re-run consensus on just that file's diff with maximum context (-U20)
- Present detailed findings for that file only

**If "Re-review with different models"**:
- Run `mcp__pal__listmodels` again
- Let user select different models
- Re-run the entire review with the new model set

## Phase 9: Post to PR (Optional)

If `--post-pr` flag is set AND in PR context:

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
- **Edit** - Auto-fix issues based on findings
- **Glob** - File discovery for large diffs
- **PAL MCP** - Multi-model consensus review
- **Rube MCP** - External notifications
- **AskUserQuestion** - Interactive decision points

## Notes

- Extended diff context (-U10) provides better code understanding for models
- Binary files are noted but excluded from diff review
- Python files get additional SOLID principles review per CLAUDE.md
- Review depth scales with diff size (larger diffs get chunked)
- Interactive validation prevents false positives on critical findings
- User directs the review flow — this is collaborative, not automated
