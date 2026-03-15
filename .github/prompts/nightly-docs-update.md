# Nightly Documentation Update (Autonomous CI Mode)

You are running in a CI pipeline. You MUST operate fully autonomously.
Do NOT use AskUserQuestion. Do NOT pause for user input. Do NOT use Write to create new files.

## Rules

1. ONLY modify files listed in AFFECTED_DOCS (provided at the end of this prompt)
2. NEVER modify: .github/, .env*, *.py, *.rs, *.yml, *.yaml, CLAUDE.md
3. Be CONSERVATIVE — only update sections where code has demonstrably changed
4. Do NOT add new sections, restructure documents, or change formatting/style
5. Do NOT modify design principles, philosophy, or instructional content
6. Focus on: factual data (tables, file paths, agent names, skill counts, command lists)
7. When cross-doc inconsistency found: code is the source of truth — update the doc to match code
8. When ambiguous: SKIP the change entirely (do not guess)
9. Preserve all existing markdown formatting, heading levels, and whitespace conventions
10. Do NOT remove content unless it references files/features that no longer exist in the codebase

## Steps

### Step 1: Gather Context

Run `git log --oneline -N` (N = COMMITS_TO_ANALYZE) to see recent changes and understand what was modified.

Run `git log --oneline -N --name-only --pretty=format: | sort -u | grep -v '^$'` to get the full list of changed files.

### Step 2: For Each File in AFFECTED_DOCS

For each documentation file listed in AFFECTED_DOCS:

1. **Read the documentation file** using the Read tool
2. **Read the relevant source-of-truth code files** (see mapping below)
3. **Compare**: identify sections that are factually outdated (wrong file paths, missing agents, incorrect counts, stale tables)
4. **Use Edit tool** to update ONLY the outdated sections — make minimal, targeted edits
5. Move on to the next file

### Step 3: Verify Changes

After all updates, run `git diff` to verify:
- Changes are minimal and correct
- No unintended modifications
- Formatting is preserved

## Source-of-Truth Mapping

Use this mapping to determine which code files to read when validating each documentation file.

### README.md

| Doc Section | Source of Truth |
|-------------|----------------|
| Agent count / list | `agents/core/*.md`, `agents/traits/*.md`, `agents/extensions/*.md` |
| Skill / command counts | `.claude/skills/*/SKILL.md` |
| Workflow inventory | `.github/workflows/*.yml` (name field) |
| Script inventory | `scripts/*.py` |
| Architecture overview | `CLAUDE.md` (Quick Reference section) |
| Badge counts | Agent/skill/command totals from above sources |

### AGENTS.md

| Doc Section | Source of Truth |
|-------------|----------------|
| Core agents table | `agents/core/*.md` (frontmatter: name, description, triggers) |
| Traits table | `agents/traits/*.md` (frontmatter: name, effect) |
| Extensions table | `agents/extensions/*.md` (frontmatter: name, domain) |
| Agent selection rules | `CLAUDE.md` (Agent Selection section) |

### TOOLS.md

| Doc Section | Source of Truth |
|-------------|----------------|
| Script descriptions | `scripts/*.py` (module docstrings) |
| Script CLI args | `scripts/*.py` (argparse/sys.argv usage) |
| Workflow descriptions | `.github/workflows/*.yml` (top-level comments, name field) |

## Per-Document Validation Rules

### README.md
- Agent, skill, and command counts must match actual file counts
- Workflow table must list all `.github/workflows/*.yml` files
- Do NOT modify the project description, badges format, or contribution guidelines
- Do NOT modify the Quick Start or installation instructions unless paths changed

### AGENTS.md
- All agent markdown files in `agents/` must be listed
- Frontmatter fields (name, description, triggers) must be accurate
- Do NOT modify usage examples or conceptual explanations

### TOOLS.md
- All scripts in `scripts/` must be documented
- All workflows in `.github/workflows/` must be listed
- Do NOT modify MCP integration descriptions unless tool names changed

## Important Reminders

- You are in CI — there is NO human to ask questions to
- If a documentation file in AFFECTED_DOCS does not exist, skip it silently
- Every edit must be verifiable against actual source code — do not infer or hallucinate
- Prefer no change over a wrong change
- CLAUDE.md is NEVER in the affected docs list — it is manually maintained only
