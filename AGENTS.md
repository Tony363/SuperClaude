# Repository Guidelines

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
- Core validation: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -m "not slow" tests/`; browser MCP
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
