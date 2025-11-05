# Contributing Code

This guide documents the workflow the core team follows when shipping changes
to the SuperClaude Framework. It replaces the old stub with concrete steps you
can follow today.

## 1. Environment Setup

1. Install Python 3.11 or newer and Node 18+ (for the optional CLI shims).
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```

3. Install the Node tooling used by the CLI wrapper and docs:

   ```bash
   npm install
   ```

4. Run `python -m SuperClaude --help` to confirm the CLI entry point is
   available.

## 2. Branching & Tickets

- Create feature branches from `main` using the pattern
  `feat/<scope>-<short-title>` or `fix/<scope>-<short-title>`.
- Keep branches focused and short‑lived. When work grows beyond a few days,
  split it into smaller pull requests linked from a tracking issue.
- Reference relevant specs in `.codex-os/specs/` within commit messages or PR
  descriptions so reviewers understand the intent.

## 3. Coding Standards

- Python code is formatted with **Black** (88 columns) and linted with **ruff**.
- Type annotations are required for new modules; run `mypy` if you change core
  typing contracts.
- Markdown docs should wrap at ~100 columns and use ATX headings.
- Prefer descriptive names over comments; when behaviour is non‑obvious, add a
  short docstring explaining the *why*.

## 4. Required Checks Before Opening a PR

Run the following commands from the repository root:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -m "not slow" tests/
python benchmarks/run_benchmarks.py --suite smoke
python benchmarks/run_benchmarks.py --suite integration --verbose
npm run lint
```

- The benchmark harness now records timing information and will fail if any
  case exits non‑zero.
- If you touch the CLI or installer, add the `full` benchmark suite to your
  local checklist.
- Capture relevant telemetry artefacts from `.superclaude_metrics/` in the PR
  description when they help reviewers understand the change.

## 5. Writing Tests

- Mirror production package paths under `tests/`. For example,
  `SuperClaude/ModelRouter/facade.py` is covered by `tests/test_model_router.py`.
- Integration tests should exercise the real command executor rather than mocks
  whenever possible. If you must stub behaviour, describe why in the test.
- Snapshot artefacts generated during tests should be stored under
  `tests/fixtures/` and referenced via helpers to keep assertions focused.

## 6. Review Expectations

- Open PRs in draft until the checklist in section 4 is green.
- Summarise *why* the change exists, what risk it mitigates, and how you tested
  it. Link to benchmarks when performance is relevant.
- Reviewers are expected to run `python benchmarks/run_benchmarks.py --suite smoke`
  on suspicious changes and request evidence for consensus or guardrail
  behaviour when it is not obvious from the diff.

## 7. After Merge

- Update `.codex-os/product/decisions.md` if the architecture changed or a new
  policy was introduced.
- Run `scripts/report_agent_usage.py` so the aggregated agent dataset stays up
  to date. This script now doubles as a benchmark case.
- Announce changes that affect external MCP integrations in the #integrations
  channel so operators can adjust credentials or policies.

Keeping this workflow disciplined ensures the deterministic consensus pipeline
and documentation stay accurate while we scale the project.
