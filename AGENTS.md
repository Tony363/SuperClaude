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
- **Current Time**: October 2025
- **Note**: Claude doesn't have real-time clock access but is aware we're in October 2025

### 🌐 Web Search Instructions - CRITICAL

**IMPORTANT: Built-in WebSearch is DISABLED. You MUST use LinkUp via Rube MCP for ALL web searches.**

**Simple LinkUp Call:**
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

**Remember**: Your training data is static. LinkUp gives you CURRENT information. Use it liberally when information might have changed.

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
