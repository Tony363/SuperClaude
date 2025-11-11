# LinkUp Web Intelligence Workflows

This guide demonstrates how to gather fresh, sourced insights using LinkUp via
the Rube MCP integration. The patterns mirror the retired browser automation
playbooks but focus on deep search instead of Chromium control.

## Quick Start

```bash
/sc:test --linkup --query "python pytest async best practices"
```

1. Ensure Rube MCP is enabled (`servers.rube.enabled: true`) and that
   `SC_RUBE_API_KEY` is set for live traffic. Dry-run mode (`SC_RUBE_MODE=dry-run`)
   echoes payloads without network access.
2. Configure defaults in `SuperClaude/Config/mcp.yaml` under
   `servers.rube.linkup` to adjust `default_depth`, `output_type`, concurrency,
   and throttling.
3. The executor stores results under
   `context.results['linkup_queries']` with per-query status and metadata. CI
   artifacts land in `.superclaude_metrics/linkup/` when evidence capture is
   enabled.

## Collecting Multiple Queries

```python
from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry

registry = CommandRegistry()
parser = CommandParser(registry=registry)
executor = CommandExecutor(registry, parser)

command = parser.parse('/sc:test --linkup --linkup-queries vulnerability, "latest pytest releases"')
metadata = registry.get_metadata(command.name)
context = executor.CommandContext(command=command, metadata=metadata)

# Assume _activate_mcp_servers already ran in the real executor path
result = await executor._execute_linkup_queries(context, scenario_hint='security')
```

- Provide comma-separated queries via `--linkup-queries` or repeat `--query`
  flags. The helper normalises them before invoking LinkUp.
- Partial failures are returned with `status='linkup_partial'` and populate
  `context.results['linkup_failures']` for downstream handling.

## Customising Payloads

```bash
/sc:test --linkup --query "s3 bucket hardening" --depth "deep" --output-type "structured"
```

- Additional parameters are passed directly to the LinkUp payload.
- Add persistent overrides (e.g., domain filters) to
  `servers.rube.linkup.payload_defaults` so every search inherits them.

## Evidence Handling

- `executed_operations` records `linkup:search` once per command.
- When evidence capture is enabled, responses serialise to
  `.superclaude_metrics/linkup/<timestamp>.json` alongside the command result.
- Downstream telemetry (`.superclaude_metrics/events.jsonl`) tags entries with
  `linkup_completed`, `linkup_partial`, or `linkup_failed` for dashboards.

## Troubleshooting

- **Missing Rube instance** – ensure `context.metadata.mcp_servers` includes
  `rube` and that `_activate_mcp_servers` completed successfully.
- **Validation errors** – empty or whitespace-only queries trigger
  `linkup_failed`; supply at least one `--query`/`--linkup-query` argument.
- **Rate limiting** – bump `throttle_seconds` or lower `max_concurrent` in the
  LinkUp config when providers return HTTP `429` responses.
- **Dry-run confusion** – when `SC_RUBE_MODE=dry-run` is active the response
  contains `status: "dry-run"`. Remove the environment variable to resume live
  traffic.
