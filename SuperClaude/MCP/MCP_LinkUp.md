# LinkUp Web Intelligence (via Rube MCP)

LinkUp extends the existing Rube MCP integration with deep web search
capabilities. It issues `LINKUP_SEARCH` requests over the active Rube session
and returns sourced answers, citations, and URLs that SuperClaude commands can
surface as evidence.

## Capabilities

- **Deep search with citations** – combine summarised answers, source lists, and
  follow-up links suitable for change plans.
- **Configurable depth/output** – adjust `depth`, `output_type`, and throttle
  controls without modifying code.
- **Batch-friendly** – run multiple LinkUp queries per command using the shared
  Rube session (respecting concurrency and throttling limits).

## Prerequisites

1. Provision Rube MCP access (see `MCP_Rube.md`) and set `SC_RUBE_API_KEY`.
2. Ensure `SC_NETWORK_MODE` permits outbound requests (`online`, `mixed`,
   `rube`, or `auto`).
3. Optional: export `SC_RUBE_MODE=dry-run` to inspect payloads without sending
   live traffic (responses echo the payload for debugging).

## Configuration (`SuperClaude/Config/mcp.yaml`)

```yaml
servers:
  rube:
    linkup:
      default_depth: deep
      default_output_type: sourcedAnswer
      max_concurrent: 4
      throttle_seconds: 0.0
```

- `default_depth` / `default_output_type` are applied when commands do not
  override `depth` or `output_type`.
- `max_concurrent` limits the number of in-flight LinkUp calls (tune for rate
  limits).
- `throttle_seconds` enforces a minimum delay between calls when providers ask
  for pacing.
- Add any persistent payload keys under `payload_defaults` (e.g., domain
  filters) to avoid repeating them in command parameters.

## CLI Usage

```
/sc:test --linkup --query "pytest asyncio best practices"
```

- `--linkup` (or the legacy `--browser`) toggles LinkUp for `/sc:test`.
- Provide one or more queries via `--query`, `--linkup-query`, or `--linkup-queries`.
- Results are stored under `context.results['linkup_queries']` with per-query
  status, citation data, and any surfaced warnings.

## Dry-Run Behaviour

When `SC_RUBE_MODE=dry-run`, LinkUp logs payloads and returns structured
placeholders. Commands still receive deterministic responses but no outbound
traffic occurs—ideal for CI environments lacking network access.

## Troubleshooting

- **Missing Rube server** – ensure `/sc:test` metadata lists `rube` in its MCP
  servers and that `_activate_mcp_servers` successfully initialised Rube.
- **Empty queries** – commands emit `linkup_failed` when no query is supplied;
  pass `--query` or positional `https://…` targets.
- **Rate limits** – increase `throttle_seconds` or reduce `max_concurrent` if
  providers return HTTP `429` responses.
