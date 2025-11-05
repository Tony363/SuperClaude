# Common Issues

This reference lists frequent problems and their remedies now that mock
behaviour has been removed from the framework.

## Consensus Errors

- **Message:** `No consensus executors registered for: gpt-4o`
  - **Cause:** Provider credentials missing or offline mode active without
    manual executors.
  - **Fix:** Export the relevant API keys or call
    `facade.consensus.register_executor` in your test harness.

- **Message:** `RuntimeError: Rube MCP integration is disabled`
  - **Cause:** `servers.rube.enabled` is set to `false` in `mcp.yaml`.
  - **Fix:** Toggle the flag or run with `SC_RUBE_MODE=dry-run` to simulate.

## Command Failures

- **Symptom:** `/sc:implement` exits with “command requires evidence”.
  - Ensure the command produced a diff. When running tests, create a temporary
    repo and write files; plan-only responses no longer pass guardrails.

- **Symptom:** `/sc:workflow` generates empty steps.
  - Provide richer context (spec path, objectives) or raise the think level.
    Empty outputs usually indicate insufficient input rather than a bug.

## Telemetry Issues

- **Symptom:** `.superclaude_metrics/` missing after a run.
  - Commands now treat missing metrics as an error. Confirm the process has
    permission to create the directory and rerun.

- **Symptom:** Benchmark harness exits with non-zero status.
  - Run with `--verbose` to inspect captured stdout/stderr. A failing case will
    typically expose the underlying pytest error immediately.

Document additional issues in this file as they appear so the team can resolve
them quickly.
