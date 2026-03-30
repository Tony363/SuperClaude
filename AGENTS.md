# Repository Guidelines

## ⚠️ CRITICAL INSTRUCTIONS - READ FIRST ⚠️

### 🧠 Intelligence Maximization Rules
- **Use parallel tool calls** - Read/search multiple files simultaneously for efficiency
- **Check dependencies first** - Understand what libraries are available before coding
- **Follow existing patterns** - Mimic the codebase's style and conventions exactly
- **Consider edge cases** - Think about error handling, null checks, race conditions
- **Write testable code** - Structure code to be easily unit tested
- **NEVER do quick fixes or overengineering** - Always ultrathink about the best clean, maintainable solution for the long term. Avoid band-aid fixes that accumulate technical debt. Avoid over-complicated solutions that add unnecessary complexity. Find the elegant middle ground that is simple, robust, and maintainable
- **NEVER create documentation files unless explicitly requested** - When done with tasks, just respond to the user directly

### 🚫 Command Safety Rules (MUST FOLLOW)
- **Never run destructive or bulk-reset commands** (`git checkout -- <path>`, `git reset --hard`, `git clean -fdx`, `rm -rf`, etc.) unless the user explicitly instructs you to do so for that exact path.
- **Never use `git checkout`, `git restore`, or similar commands to revert tracked files** unless the user explicitly requests it for that specific file. These commands can silently discard changes created by other agents.
- **Always consult `.claude/settings.json`** before running shell commands. Respect the `denyList`, `askList`, and any other guardrails defined there. If a command appears on the deny list, do not run it. If a command appears on the ask list (or you are unsure), ask the user for explicit approval first.
- **Treat uncertainties as denials.** When in doubt about whether a command is destructive or violates the settings, stop and ask the user.
- **Prefer targeted edits** (e.g., `sed -n`, `apply_patch`, file-specific changes) instead of repo-wide operations. Do not reset or roll back large sections of the codebase to “undo” mistakes.
- **Log every potentially mutating command in your reasoning** so it’s clear why it is safe and allowed.

### 📅 Current Context
- **Note**: Claude does not have real-time clock access; the current date is injected via system context

### Web Search Instructions - CRITICAL

**IMPORTANT: Built-in WebSearch is DISABLED. You MUST use Rube MCP's LINKUP_SEARCH tool for ALL web searches.**

**Simple Web Search Call:**
```
// mcp__rube__RUBE_MULTI_EXECUTE_TOOL
{
  "tools": [{
    "tool_slug": "LINKUP_SEARCH",
    "arguments": {
      "query": "your search query here",
      "depth": "deep",
      "output_type": "sourcedAnswer"
    }
  }],
  "session_id": "WEB-SESSION-001",
  "memory": {},
  "sync_response_to_workbench": false,
  "thought": "Searching for [topic]",
  "current_step": "SEARCHING",
  "current_step_metric": {"completed": 0, "total": 1, "unit": "searches"},
  "next_step": "COMPLETE"
}
```

**Key Parameters:**
- `depth`: Always use `"deep"` for comprehensive results
- `output_type`: Use `"sourcedAnswer"` (most common), `"searchResults"`, or `"structured"`

**Be Proactive - Search Frequently:**
- Current library/framework versions
- Latest API documentation and syntax
- Recent security updates and best practices
- Error messages and deprecation warnings
- External service status and configuration

**Remember**: Your training data is static. Rube MCP's LINKUP_SEARCH gives you CURRENT information. Use it liberally when information might have changed.

## Project Structure & Module Organization
- `SuperClaude/` contains the orchestrator: `Commands/` for `/sc:` playbooks, `ModelRouter/` for
  routing, `Quality/` for scoring, `Monitoring/` for telemetry, and `Implementation/Auto/` for
  generated evidence.
- Supporting assets live in `tests/` (pytest suites mirroring package paths), `setup/` (CLI
  installer), `scripts/` (reporting, builds, cleanup), `Docs/` (user references), and
  `.superclaude_metrics/` for run artifacts.

## Build, Test, and Development Commands
- Bootstrap with `python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`;
  run `SuperClaude --help` to confirm the CLI wiring.
- Core validation: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -m "not slow" tests/`; LinkUp flows add `-p pytest_asyncio`
  flows add `-p pytest_asyncio`. Smoke benchmarks run via
  `python benchmarks/run_benchmarks.py --suite smoke`.
- Release prep relies on `python -m build` (wheel/sdist), `scripts/build_and_upload.py` for
  automation, and `npm run lint` to keep the Node wrapper tidy.

## Coding Style & Naming Conventions
- Python targets 3.8+ with Black (88 cols), Flake8, and MyPy; use 4-space indents, snake_case
  modules, and PascalCase agent classes aligned with their persona names.
- JavaScript CLI shims under `bin/` follow ESLint defaults from `package.json`; keep filenames
  kebab-case and prefer CommonJS `module.exports`.
- Markdown guidance (README, Docs/, `.codex-os/`) uses ATX headings, wraps near 100 characters, and
  should link to decisions or specs when behavior changes.

## Testing Guidelines
- Mirror production paths when adding tests (`tests/<domain>/test_<module>.py`) and name functions
  `test_<behavior>`; mark slower journeys with `@pytest.mark.slow` or `integration` per
  `pyproject.toml`.
- Always export `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` before invoking pytest to avoid host plugin
  bleed; collect coverage for `SuperClaude` and `setup` packages.
- Include fixtures that validate `requires_evidence` guardrails and `.superclaude_metrics`
  outputs whenever agent workflows, telemetry, or auto-implementation logic changes.

## Commit & Pull Request Guidelines
- History favors concise, imperative subjects (`reduce context`, `cli clean flag`); keep messages
  tight but document reasoning and spec links in the body.
- Reference relevant ADRs (`.codex-os/product/decisions.md`) or specs, enumerate tests/benchmarks
  run, and attach evidence when touching guardrails or installer behavior.
- PRs should describe risk surface, highlight configuration changes (e.g., MCP updates), and note
  any follow-up tasks for consensus, telemetry, or cleanup tooling.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **SuperClaude** (8999 symbols, 21160 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/SuperClaude/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/SuperClaude/context` | Codebase overview, check index freshness |
| `gitnexus://repo/SuperClaude/clusters` | All functional areas |
| `gitnexus://repo/SuperClaude/processes` | All execution flows |
| `gitnexus://repo/SuperClaude/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
