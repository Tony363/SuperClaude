# Testing & Debugging

The SuperClaude Framework favours integration-style validation. This guide
explains how to run the suites efficiently and debug failing runs.

## 1. Test Matrix

| Layer         | Command                                                     | Notes |
| ------------- | ----------------------------------------------------------- | ----- |
| Smoke         | `python benchmarks/run_benchmarks.py --suite smoke`         | CLI help + version check |
| Integration   | `python benchmarks/run_benchmarks.py --suite integration`   | Exercises workflow + worktree guardrails |
| Full (CI)     | `python benchmarks/run_benchmarks.py --suite full`          | Pytest `-m not slow` + agent usage report |
| Targeted test | `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/<module>.py` | Run before pushing focused fixes |

The benchmark harness records execution time and flags non-zero exits without
relying on placeholder logic.

## 2. Running Pytest Directly

```bash
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
pytest -m "not slow" tests/test_model_router.py
```

- Integration tests register explicit consensus executors—no patching of the
  production code is required.
- Use `-k <keyword>` when iterating on an individual scenario.

## 3. Debugging Command Failures

1. Re-run the command with `--think 3 --verbose` to capture richer telemetry.
2. Inspect `.superclaude_metrics/metrics.jsonl` and
   `.superclaude_metrics/auto_implementation_plans.jsonl` for recorded plans.
3. If consensus fails with `No consensus executors registered`, check that the
   required provider API keys (OPENAI/ANTHROPIC/GOOGLE/XAI) are present or
   register custom executors in your test harness.
4. For MCP flows, set `SC_NETWORK_MODE=debug` to enable verbose client logging.

## 4. Debugging Agents

- Agents log via `logging.getLogger(__name__)`. Enable debug logs by exporting
  `SUPERCLAUDE_LOG_LEVEL=DEBUG`.
- The `scripts/report_agent_usage.py` script summarises how often agents run and
  highlights dormant personas.
- To inspect Markdown personas, run `python -m SuperClaude.Agents.loader --list`.

## 5. Profiling & Benchmarks

- Use `python benchmarks/run_benchmarks.py --suite full --verbose` to capture
  stdout/stderr for each case.
- For deeper profiling, wrap the command in `python -m cProfile -o profile.out
  -m SuperClaude ...` and analyse with `snakeviz profile.out`.

## 6. Common Test Issues

| Symptom | Likely Cause | Fix |
| ------- | ------------ | --- |
| `No consensus executors registered` | Missing API key or forgot to register stub in test | Export provider key or call `ConsensusBuilder.register_executor` in fixture |
| `Command requires evidence` failure | Agent returned plan only | Ensure tests create temporary repo and write actual diff |
| CLI hangs during consensus | External provider timed out | Set `SUPERCLAUDE_OFFLINE_MODE=1` for tests and register explicit executors |

Document tricky edge cases in `Docs/Reference/common-issues.md` when you find
them so the next contributor has a shorter debug cycle.

## 7. Modern Command Test Suite

The `/sc:` command tests now run as *integration* scenarios that execute the real
`CommandExecutor`, guardrails, and telemetry stack inside disposable workspaces.

### Running the Suite

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_commands.py
```

The fixtures pin the executor to offline mode and capture metrics inside a
temporary `.superclaude_metrics/` directory. To exercise live Codex/OpenAI
integrations, export the relevant keys before invoking pytest:

```bash
export OPENAI_API_KEY=...
export CODEX_API_KEY=...
```

### Key Fixtures

| Fixture | Purpose |
| --- | --- |
| `command_workspace` | Creates a disposable git workspace, sets offline/metrics env vars, and ensures artefacts land under the temp directory. |
| `executor` | Instantiates `CommandExecutor` against that workspace so each test hits the real command pipeline. |

### Behaviour Coverage

| Behaviour | Test | Assertion |
| --- | --- | --- |
| Fast Codex guardrails fail fast without diffs | `test_implement_fast_codex_requires_evidence` | Command fails, consensus metadata present, “no concrete change plan” surfaced. |
| Safe-apply flag no longer writes stub placeholders | `test_implement_safe_apply_fails_without_plan` | Command fails early and no `.superclaude_metrics/safe_apply/` directory is created. |
| `--safe` blocks fast-codex activation | `test_fast_codex_respects_safe_flag` | `fast_codex.active` becomes false and `blocked` lists `safety-requested`. |
| Business panel still emits artefacts when personas fail | `test_business_panel_produces_artifact` | Artefact recorded despite loader warning. |
| Workflow command consumes a PRD and emits steps | `test_workflow_command_generates_steps` | Returns `status == workflow_generated` with stored artefacts. |
| Git helper summarises repo state | `test_git_status_summarizes_repository` | Summary reflects branch plus staged/unstaged counts from real git metadata. |
| `/sc:test` translates CLI flags without nesting pytest | `test_test_command_reports_parameters` | Output surfaces `--type`/`--coverage` inputs while skipping nested runs. |

Each integration test leaves concrete evidence under the temporary metrics
directory (command artefacts, metrics JSONL, etc.). Inspecting those artefacts is
the fastest way to understand failures because they reflect the actual executor
output.

- When API keys are available, `--pal-review` (GPT-5) now becomes the primary
  `QualityScorer` evaluator during `--loop`. Tests that stub pal responses should
  assert on `QualityDimension.PAL_REVIEW` metrics or the GPT-provided
  `improvements` list as part of their expectations.
