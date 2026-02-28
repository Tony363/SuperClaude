---
name: pr-fix
description: "Create PR and iteratively fix CI failures with interactive confirmation"
category: workflow
complexity: standard
mcp-servers: [pal]
personas: [devops-architect, quality-engineer]
requires_evidence: true
aliases: [prfix, cifix, fix-pr]
flags:
  - name: branch
    description: New branch name (auto-generates if not specified)
    type: string
  - name: base
    description: Target branch for PR (default: main)
    type: string
    default: main
  - name: title
    description: PR title (defaults to commit message)
    type: string
  - name: body
    description: PR description body
    type: string
  - name: dry-run
    description: Preview operations without executing
    type: boolean
    default: false
  - name: auto-fix
    description: Auto-apply low-risk fixes, prompt only for high-risk
    type: boolean
    default: false
  - name: max-fix-attempts
    description: Max CI fix iterations (hard cap: 5)
    type: integer
    default: 3
  - name: poll-interval
    description: Seconds between CI status checks
    type: integer
    default: 30
  - name: no-push
    description: Create branch and commit but do not push/PR
    type: boolean
    default: false
---

# /sc:pr-fix - PR Creation & CI Fix Loop

Create a pull request and iteratively fix CI failures until all checks pass.

## Triggers
- Creating PRs with automatic CI monitoring
- Fixing failing CI checks on existing PRs
- Requests like "create PR and fix CI", "fix the failing checks"

## Usage
```
/sc:pr-fix [--branch=NAME] [--base=BRANCH] [--title=TITLE] [--dry-run] [--auto-fix] [--max-fix-attempts=N]
```

## Behavioral Flow

1. **Stage**: Identify changes to commit (staged + unstaged)
2. **Branch**: Create a new branch (or use specified `--branch`)
3. **Commit**: Create commit with descriptive message
4. **Push**: Push branch to remote with tracking
5. **PR**: Create pull request via `gh pr create`
6. **Monitor**: Poll CI status at `--poll-interval` intervals
7. **Diagnose**: On failure, parse check logs to identify root cause
8. **Fix**: Apply fixes based on failure type and risk level
9. **Iterate**: Re-push and re-monitor (up to `--max-fix-attempts`)
10. **Report**: Summarize outcome with all actions taken

## Safety Mechanisms

- **Hard cap**: Maximum 5 fix iterations regardless of `--max-fix-attempts`
- **Stagnation detection**: Stops if the same checks keep failing
- **Risk assessment**: High-risk fixes require user confirmation unless `--auto-fix`
- **Interactive prompts**: User confirms each fix iteration by default

## Tool Coordination
- **Bash**: Git operations, `gh` CLI for PR creation and status checks
- **Read/Edit**: Apply code fixes for failing checks
- **PAL debug**: Root cause analysis for complex CI failures
- **PAL codereview**: Validate fixes before pushing

## Scripts
- `scripts/check_pr_status.py` - Poll and parse PR check status
- `scripts/parse_check_failures.py` - Classify failure types and risk levels
- `scripts/fix_orchestrator.py` - Coordinate iterative fix loop

## Examples

### Create PR with Auto-Fix
```
/sc:pr-fix --auto-fix
```

### Dry Run Preview
```
/sc:pr-fix --dry-run --title "Add user auth"
```

### Custom Branch and Base
```
/sc:pr-fix --branch feat/auth --base develop --max-fix-attempts 5
```

## Boundaries

**Will:**
- Create branches, commits, and PRs
- Monitor CI status and diagnose failures
- Apply fixes for lint, type, test, and build failures
- Respect iteration limits and risk thresholds

**Will Not:**
- Force-push or rewrite history
- Skip CI checks or bypass required reviews
- Apply high-risk fixes without user confirmation (unless `--auto-fix`)
- Exceed hard cap of 5 fix iterations
