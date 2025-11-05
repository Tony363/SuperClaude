# Troubleshooting

Follow these steps when commands do not behave as expected.

## Consensus Failures

1. **Check credentials:** run `env | grep API_KEY` and confirm the necessary
   provider keys are exported.
2. **Review logs:** inspect `.superclaude_metrics/mcp.log` for provider error
   messages.
3. **Retry with explicit executors:** in tests or offline mode, register stub
   executors on `ModelRouterFacade.consensus` before invoking the command.

## MCP Problems

- Run `python -m SuperClaude.MCP --list` to view enabled servers.
- Set `SC_NETWORK_MODE=debug` to capture detailed HTTP traces.
- For Rube automation, confirm `SC_RUBE_API_KEY` is present or switch to dry-run
  mode.

## Command-Specific Issues

- `/sc:implement` fails with “requires evidence”: ensure the target repository
  has a clean working tree and that the command produced a diff.
- `/sc:workflow` returns no steps: include a spec path or additional context so
  the agent has material to expand.
- `/sc:test` exits immediately: use `--passthrough "--maxfail=1"` to forward
  Pytest arguments when needed.

## Telemetry & Artefacts

- If `.superclaude_metrics/` is missing, check filesystem permissions and rerun
  the command. The executor no longer proceeds silently when telemetry cannot be
  written.
- Use `python scripts/report_agent_usage.py --since 7d` to review recent agent
  activity when debugging unexpected persona selection.

When these steps fail, capture the command, environment variables, and relevant
artefacts, then open an issue so the team can investigate.
