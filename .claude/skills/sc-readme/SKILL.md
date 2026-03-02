---
name: sc-readme
description: Auto-update project documentation by analyzing git changes with cross-reference validation and staleness reporting. Supports single-file README updates or multi-document review. Use when synchronizing documentation with code changes.
---

# Documentation Auto-Update Skill

Intelligent documentation maintenance based on git changes with cross-reference validation, staleness reporting, and multi-model consensus for critical updates.

## Quick Start

```bash
# Update README based on current branch changes
/sc:readme

# Multi-document review and update (all project docs)
/sc:readme --scope all

# Target specific documentation
/sc:readme --scope api-docs

# Preview changes without writing
/sc:readme --preview

# Analyze N recent commits instead of branch diff
/sc:readme --commits 20

# Force PAL consensus for all updates
/sc:readme --consensus

# Compare against different base branch
/sc:readme --base develop

# Staleness report only (no changes)
/sc:readme --report-only
```

## Behavioral Flow

1. **DISCOVER** - Run `git diff` or `git log` to find changed files
2. **ANALYZE** - Read changed files, categorize by type (API, config, deps, features)
3. **MAP** - Match changed files to affected documentation using source-of-truth mapping
4. **VALIDATE** - Cross-reference consistency checks across all docs
5. **PLAN** - Identify sections needing updates, generate staleness report
6. **GENERATE** - Update documentation sections via Edit tool
7. **VERIFY** - Review final docs with PAL codereview

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--base` | string | `main` | Base branch to compare against |
| `--preview` | bool | false | Preview changes without writing |
| `--consensus` | bool | false | Force PAL consensus for all updates |
| `--scope` | string | readme | Target: `readme`, `all`, or custom doc paths |
| `--commits` | int | - | Analyze N recent commits instead of branch diff |
| `--report-only` | bool | false | Generate staleness report without changes |
| `--cross-ref` | bool | true | Enable cross-reference validation |

## Git Commands Used

```bash
# Branch diff mode (default)
git diff main...HEAD --name-status
git diff main...HEAD
git log main...HEAD --oneline

# Commit mode (--commits N)
git log --oneline -N --name-only --pretty=format: | sort -u | grep -v '^$'
git log --oneline -N
```

## Change Categories

| Category | File Patterns | Affected Docs |
|----------|---------------|---------------|
| API | `*.py`, `*.ts`, `*.js` with new exports | README, API docs |
| Dependencies | `package.json`, `requirements.txt`, `pyproject.toml` | README, Installation |
| Config | `.env*`, `*.config.*`, `settings.*` | README, Config docs |
| Features | New modules, significant additions | README, Feature docs |
| Database | `models/`, `migrations/` | Database docs, README |
| Frontend | `src/components/`, `src/pages/` | Frontend docs, README |
| Infrastructure | `docker-compose*`, `Dockerfile`, CI configs | DevOps docs, README |

## Multi-Document Mode (`--scope all`)

When `--scope all` is used, discover and validate all documentation files in the project.

### Document Discovery

Auto-detect documentation files:

```bash
# Find all markdown docs (excluding node_modules, .venv, etc.)
find . -name "*.md" -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/dist/*"
```

Common documentation patterns:

| Doc File | Purpose |
|----------|---------|
| `README.md` | Main project documentation |
| `CLAUDE.md` | Claude Code instructions |
| `CONTRIBUTING.md` | Contribution guidelines |
| `docs/*.md` | Extended documentation |
| `frontend/README.md` | Frontend-specific docs |
| `api/README.md` | API documentation |

### Source-of-Truth Mapping

Map code changes to affected documentation:

| Code Pattern | Affected Documentation |
|--------------|----------------------|
| `src/api/**`, `app/routers/**` | README, API docs |
| `src/models/**`, `app/models/**` | README, Database docs |
| `src/components/**`, `frontend/src/**` | README, Frontend docs |
| `migrations/**` | Database docs |
| `.env.example` | README, all docs with env references |
| `tests/**` | README (test structure section) |

### Cross-Reference Validation

When `--cross-ref` is enabled (default), verify consistency across docs:
- API routes mentioned in README match actual route handlers
- Environment variables match across all docs and `.env.example`
- File paths referenced in docs actually exist (via Glob)
- Component names are consistent across all documentation
- Documented commands are syntactically valid

### Staleness Report

```
## Documentation Staleness Report

**Commits Analyzed**: 20 | **Docs Scanned**: 6 | **Issues Found**: 3

### README.md
**Status**: STALE
**Affected by**: src/api/users.py, src/models/user.py

- [ ] API Routes table missing new `/users/bulk` endpoint
- [ ] Environment variables section missing `BULK_IMPORT_LIMIT`

### docs/DATABASE.md
**Status**: UP-TO-DATE
No changes needed.

### frontend/README.md
**Status**: STALE
**Affected by**: src/components/UserProfile.tsx

- [ ] Component list missing UserProfile
```

### Update Order

Process documents in dependency order:
1. README.md first (primary reference)
2. CLAUDE.md second (must stay consistent with README)
3. Other docs after (reference README as source of truth)

## MCP Integration

### PAL MCP

```bash
# Consensus for API/breaking changes
mcp__pal__consensus(
    models=[{"model": "gpt-5.2", "stance": "for"}, {"model": "gemini-3-pro", "stance": "against"}],
    step="Evaluate: Does this documentation update accurately reflect the code changes?",
    relevant_files=["/README.md", "/src/changed_file.py"]
)

# Review final documentation
mcp__pal__codereview(
    review_type="quick",
    step="Review documentation accuracy and cross-reference consistency",
    relevant_files=["/README.md", "/docs/API.md"]
)
```

## Tool Coordination

- **Bash** - Git commands (`git diff`, `git log`)
- **Read** - Documentation files, changed source files
- **Edit** - Update documentation sections in-place
- **Glob** - File path validation, doc discovery
- **Grep** - Cross-reference checks, pattern validation

## Examples

### Single README Update
```bash
/sc:readme
# 1. git diff main...HEAD --name-status
# 2. Read README.md + changed files
# 3. Identify sections needing updates
# 4. PAL consensus if API changes detected
# 5. Update README.md
```

### Multi-Document Review
```bash
/sc:readme --scope all --commits 20
# 1. git log --oneline -20 for change context
# 2. Discover all .md documentation files
# 3. Map changes to affected docs
# 4. Cross-reference validation
# 5. Generate staleness report
# 6. Update all affected docs
```

### Staleness Report Only
```bash
/sc:readme --report-only --scope all
# Generates report without making changes
```

### Preview Mode
```bash
/sc:readme --preview
# Same analysis, but output proposed changes instead of writing
```

## Guardrails

1. **Back up docs** before modifications
2. **Never remove sections** without user confirmation
3. **Require consensus** for breaking changes
4. **Preserve custom content** not related to code changes
5. **Process in order** - README first, then dependent docs
6. Only modify `.md` files in the documented scope
7. Git-based rollback always available via `git checkout`

## Related Skills

- `/sc:git` - Git operations
- `/sc:document` - General documentation generation
- `/sc:pr-check` - Pre-PR validation
