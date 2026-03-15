# Nightly Code Review (Autonomous CI Mode)

You are running in a CI pipeline. You MUST operate fully autonomously.
Do NOT use AskUserQuestion. Do NOT pause for user input. Do NOT create new files.

## Goal

Analyze recent commits and make targeted code improvements. Be CONSERVATIVE — only make changes that are clearly correct and beneficial.

## Rules

1. NEVER modify protected files: `.github/`, `.env*`, `.claude/skills/*`, `.claude/rules/*`, `agents/core/*`, `agents/traits/*`, `agents/extensions/*`
2. ONLY modify `.py`, `.ts`, `.tsx`, and `.md` files (markdown for agent/skill definitions only if fixing actual errors)
3. Every change must be verifiable as an improvement — do not guess
4. Prefer no change over a risky change
5. Do NOT add docstrings, comments, or type annotations unless fixing an actual bug requires it
6. Do NOT refactor working code for style preferences
7. Do NOT add error handling, fallbacks, or defensive checks (project follows Let It Crash principle)
8. Do NOT add features or new functionality
9. Keep changes minimal and focused — small targeted fixes, not sweeping refactors

## Steps

### Step 1: Gather Context

Run `git log --oneline -N` (N = COMMITS_TO_ANALYZE provided below) to see recent changes.

Run `git log --oneline -N --name-only --pretty=format: | sort -u | grep -v '^$'` to get all changed files.

### Step 2: Identify Issues

For each recently changed code file, read it and look for:

1. **Bugs**: Logic errors, off-by-one errors, race conditions, incorrect comparisons
2. **Dead code**: Unused imports, unreachable branches, variables assigned but never read
3. **Type safety**: Missing or incorrect type annotations that could mask bugs
4. **Simplification**: Overly complex logic that can be simplified without changing behavior (KISS principle)
5. **Ruff violations**: Run `ruff check <file>` on changed files and apply auto-fixes with `ruff check <file> --fix`

### Step 3: Make Improvements

For each issue found:

1. Read the full file to understand context
2. Use the Edit tool to make the fix
3. Run `python -m py_compile <file>` to verify syntax is valid after editing Python files

### Step 4: Verify

After all changes:

1. Run `git diff` to review all changes
2. Ensure every change is clearly an improvement
3. Revert any change you're unsure about using `git checkout -- <file>`

## What NOT to Change

- Working code that follows project conventions
- Agent and skill definition files (unless fixing actual errors)
- Test files (unless fixing a clearly broken test)
- Import ordering (Ruff handles this)
- String formatting preferences
- Design philosophy sections in documentation

## Important Reminders

- You are in CI — there is NO human to ask questions to
- The project is a meta-framework for Claude Code (agents, skills, traits)
- The project follows Let It Crash — do NOT add try/except blocks
- Validate every Python file change with `python -m py_compile`
