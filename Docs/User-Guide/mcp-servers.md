# MCP Server Integrations

SuperClaude ships with three Model Context Protocol (MCP) servers. This guide
explains how to configure each one and how they behave now that mock fallbacks
have been removed.

## 1. Configuration Overview

- Edit `SuperClaude/Config/mcp.yaml` to enable/disable servers or to override
  endpoints.
- The CLI honours `SC_NETWORK_MODE`. Set it to `offline` to skip network calls,
  `online` for full access, or `debug` to log request payloads.
- Server-specific environment variables:
  - `SC_PAL_OFFLINE=1` to force PAL into offline mode (requires manual executor
    registration).
  - `SC_RUBE_API_KEY` for Rube automation calls and LinkUp web searches.

## 2. PAL Integration (Consensus)

SuperClaude uses PAL MCP directly via Claude Code's native tool system. The
Python `ModelRouter` and `APIClients` modules have been removed in favor of
meta-prompting patterns.

PAL MCP provides these tools for consensus and model routing:
- `mcp__pal__consensus` - Multi-model consensus with stances
- `mcp__pal__chat` - General model chat with model selection
- `mcp__pal__codereview` - Systematic code review
- `mcp__pal__thinkdeep` - Multi-stage investigation
- `mcp__pal__debug` - Root cause analysis
- `mcp__pal__planner` - Interactive planning
- `mcp__pal__listmodels` - Available models

See `CLAUDE.md` for usage patterns and when to use each tool.

## 3. Rube Integration (Automation)

- Enable by setting `servers.rube.enabled: true` in `mcp.yaml` and exporting
  `SC_RUBE_API_KEY`.
- Use `SC_RUBE_MODE=dry-run` to simulate responses without hitting the network.
- Errors bubble up with actionable messages (e.g., missing token, HTTP failure)
  so automation scripts can abort cleanly.

## 4. LinkUp Web Intelligence (via Rube)

- Pass `--linkup` (or the legacy `--browser`) to commands such as `/sc:test` to
  perform LinkUp searches through the active Rube session.
- Configure defaults under `servers.rube.linkup` in `mcp.yaml` to adjust depth,
  output type, concurrency, and throttle behaviour.
- When `SC_RUBE_MODE=dry-run` is set the integration echoes payloads instead of
  contacting LinkUp, allowing offline validation.

## 5. Troubleshooting

- Check `.superclaude_metrics/mcp.log` for detailed request/response traces.
- Use `python -m SuperClaude.MCP --list` to confirm available integrations, or
  `python -m SuperClaude.MCP --describe rube --json` for structured metadata.
- Run `python benchmarks/run_benchmarks.py --suite integration` after changing
  MCP settings; the suite exercises Rube and LinkUp paths alongside the main
  workflow tests.
