# Modern Command Test Suite

This project now treats the `/sc:` command tests as *integration* checks that
exercise the real executor, guardrails, and telemetry stack. The previous
mock-heavy regression suite has been replaced with small, isolated workspaces
that surface the actual artefacts the framework emits today.

## How to run the suite

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_commands.py
```

By default the fixtures force the executor into offline mode and record
telemetry under a temporary `.superclaude_metrics/` directory. To exercise real
Codex / OpenAI integrations in CI (or locally) export the relevant keys before
running:

```bash
export OPENAI_API_KEY=...  # optional, runs in offline mode when unset
export CODEX_API_KEY=...
```

## Fixture overview

| Fixture | Purpose |
| --- | --- |
| `command_workspace` | Creates a disposable git workspace, pins offline / metrics environment variables, and ensures artefacts land under the temp directory. |
| `executor` | Instantiates `CommandExecutor` against the isolated workspace so each test calls the real command pipeline. |

The fixtures live in `tests/test_commands.py` and can be reused by additional
command scenarios.

## Behaviour coverage

| Behaviour | Modern test | Key assertion |
| --- | --- | --- |
| Fast Codex guardrails fail fast without concrete diffs | `test_implement_fast_codex_requires_evidence` | Command exits with `status == 'failed'`, emits consensus metadata, and surfaces a “no concrete change plan” error. |
| Safe-apply flag no longer creates stub placeholders | `test_implement_safe_apply_fails_without_plan` | Command fails early and no `.superclaude_metrics/safe_apply/` directory is produced. |
| `--safe` flag blocks fast-codex activation | `test_fast_codex_respects_safe_flag` | `fast_codex.active` becomes `False` and `blocked` mentions `safety-requested`. |
| Business panel still produces artefacts when optional personas fail to load | `test_business_panel_produces_artifact` | Artefact stored while surfacing loader warning. |
| Workflow command reads a PRD and emits structured steps | `test_workflow_command_generates_steps` | Returns `status==workflow_generated` with at least one step and a persisted artefact. |
| Git wrapper summarises repository state | `test_git_status_summarizes_repository` | Summaries include branch, unstaged and untracked counts derived from a live git repo. |
| `/sc:test` translates flags without spawning nested pytest | `test_test_command_reports_parameters` | Output reflects `--type`, `--coverage`, and marker arguments while skipping nested runs. |

## Telemetry expectations

Every integration test leaves artefacts under the temporary metrics directory.
The most relevant files are the `SuperClaude/Generated/...` command summaries
and any metrics emitted during execution. Inspecting these artefacts is the
recommended way to debug failing tests, since they reflect precisely what the
executor produced.
