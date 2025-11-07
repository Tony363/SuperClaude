# Behavioural Modes

Modes bundle sets of flags, guardrails, and agents so you can switch execution
posture quickly.

## Safe Mode

- Activate via `--safe` or by setting `SC_SAFE_MODE=1`.
- Disables fast-codex, enforces consensus when required by policy, and tightens
  quality scoring thresholds.
- Auto-implementation artefacts are always written to the worktree for manual
  inspection.

## Fast Codex Mode

- Activate with `--fast-codex` (only on implementation commands).
- Requires the Codex CLI (`codex exec`) to be installed or referenced via
  `SUPERCLAUDE_CODEX_CLI`; the command aborts if the binary is missing.
- Loads the `codex-implementer` strategist, which now records Codex payloads
  when API keys are available. If keys are missing the mode falls back to the
  standard persona stack and emits a warning.
- Pair with `--think 1` for the quickest feedback loop; raise the think level to
  combine speed with deeper validation.

## Offline Mode

- Set `SUPERCLAUDE_OFFLINE_MODE=1` when running in air-gapped environments.
- ModelRouter no longer injects mock consensus executors; you must register
  local executors or expect commands requiring consensus to fail with a clear
  error.
- Telemetry continues to write to `.superclaude_metrics/` so you can analyse
  runs offline.

## Dry-Run Automation

- Export `SC_RUBE_MODE=dry-run` to exercise Rube MCP flows without calling the
  external service.
- Combine with `SC_NETWORK_MODE=debug` to log request bodies for approval.

Switch modes depending on the risk and connectivity constraints of your task.
The command executor will always surface the final mode in the telemetry payload
for auditing.
