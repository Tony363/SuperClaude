---
name: sc-push
description: Multi-remote git push with selective content filtering. Push to multiple remotes with per-remote path exclusions, branch mapping, and force-push controls.
---

# Multi-Remote Push Skill

Push changes to multiple git remotes with per-remote configuration. Supports selective content filtering (exclude paths per remote), branch mapping, and force-push controls.

## Quick Start

```bash
# Push current branch to all remotes
/sc:push

# Push specific branch
/sc:push main

# Push with path exclusions for a remote
/sc:push --exclude efs:prompts/,secrets/

# Push to specific remotes only
/sc:push --remotes origin,staging

# Dry run to preview actions
/sc:push --dry-run
```

## Behavioral Flow

1. **Parse** - Extract branch, remote list, exclusions, flags
2. **Validate** - Check git state, uncommitted changes, remote existence
3. **Plan** - Build per-remote push plan with exclusions
4. **Confirm** - Show plan and get user confirmation for force pushes
5. **Execute** - Push to each remote sequentially
6. **Report** - Summarize push results per remote

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--remotes` | string | all | Comma-separated remotes to push to |
| `--exclude` | string | - | Per-remote exclusions: `remote:path1,path2` |
| `--dry-run` | bool | false | Preview push plan without executing |
| `--force` | bool | false | Force push to remotes with exclusions |
| `--no-verify` | bool | false | Skip pre-push hooks |

## Phase 1: Parse Arguments

- **Branch**: First positional arg, or current branch via `git rev-parse --abbrev-ref HEAD`
- **Remotes**: From `--remotes` flag, or all configured remotes via `git remote`
- **Exclusions**: Parse `--exclude remote:path1,path2;remote2:path3` format

## Phase 2: Validate Git State

```bash
# Verify git repository
git rev-parse --is-inside-work-tree

# Get current branch
git branch --show-current

# Check for uncommitted changes
git status --porcelain
```

If uncommitted changes exist:
- Warn the user
- Ask if they want to commit first or push existing commits only

Validate each target remote exists:
```bash
git remote -v
```

## Phase 3: Build Push Plan

For each remote, determine push strategy:

### Simple Push (no exclusions)

```bash
git push <remote> <branch>
```

### Filtered Push (with exclusions)

When paths must be excluded for a specific remote:

1. **Stash uncommitted changes** if present
2. **Create temporary branch**: `git checkout -b tmp-push-<remote>-$$ <branch>`
3. **Remove excluded paths from index**: `git rm -rf --cached <paths>` (ignore errors if paths don't exist)
4. **Commit removal**: `git commit -m "tmp: remove excluded paths for <remote> push" --allow-empty`
5. **Force push temp branch**: `git push <remote> tmp-push-<remote>-$$:<branch> --force`
6. **Return to original branch**: `git checkout <branch>`
7. **Delete temp branch**: `git branch -D tmp-push-<remote>-$$`
8. **Restore stash** if applicable

Present plan before executing:

```
Push Plan:
  Branch: <branch>

  Remote: origin
    Strategy: direct push
    Command: git push origin <branch>

  Remote: efs
    Strategy: filtered push (excluding: prompts/, secrets/)
    Steps: temp branch -> remove paths -> force push -> cleanup
```

## Phase 4: Confirm

For any remote requiring force push:
- **Always confirm with user** before executing
- Show exactly what will be force-pushed and why
- Never force push to main/master without explicit user confirmation

## Phase 5: Execute Push

Execute push plan sequentially per remote:

1. Push to each remote in order
2. Report success/failure for each
3. On failure: log error, continue with remaining remotes
4. Clean up any temporary branches

## Phase 6: Report Results

```markdown
## Push Summary

| Remote | URL | Strategy | Status |
|--------|-----|----------|--------|
| origin | github.com/user/repo | direct | Success |
| efs | github.com/org/repo | filtered | Success |

**Branch**: <branch>
**Excluded paths**: efs: prompts/, secrets/
```

## Error Handling

| Scenario | Action |
|----------|--------|
| Not a git repo | Exit with error |
| Remote not found | Error with available remotes |
| Uncommitted changes | Warn, ask to commit or proceed |
| Push rejected (non-fast-forward) | Suggest pull first, never auto-force |
| Force push to main/master | Require explicit confirmation |
| Temp branch cleanup fails | Warn user, provide cleanup command |
| Network failure | Report which remotes succeeded/failed |

## Guardrails

- **Never force push to main/master** without explicit user consent
- **Always show push plan** before executing
- **Clean up temp branches** even on failure
- **Restore stash** even on failure
- **Dry run by default** for filtered pushes on first use
- Temporary commits never appear in the source branch history

## Tool Coordination

- **Bash** - All git operations
- **Read** - Inspect `.git/config` for remote configuration
