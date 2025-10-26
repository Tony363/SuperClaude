# Zen MCP (Offline Stub)

The SuperClaude Framework ships an offline-friendly Zen MCP implementation that
behaves as a deterministic consensus helper. It **does not** call the public
zen-mcp-server, does not require API keys, and deliberately avoids real network
traffic so `/sc:*` commands remain usable in restricted environments.

## Capabilities

- **Consensus simulation** – the stub accepts a prompt, pretends three models
  voted, and returns a weighted majority decision.
- **Think-level awareness** – the executor can request different “thinking”
  depths; the stub simply records the preference.
- **Local sessions** – the object exposes `initialize()` /
  `initialize_session()` so it plugs into the command executor lifecycle.

Everything else (vision models, specialized tools, continuation IDs, CLI
bridges) is intentionally out of scope for the offline build.

## Configuration

`SuperClaude/Config/mcp.yaml` enables the Zen server with a small set of flags:

```yaml
servers:
  zen:
    enabled: true
    triggers: [--zen, --consensus, --thinkdeep, --zen-review]
```

These triggers keep parity with the command playbooks while avoiding claims
about nonexistent endpoints.

## Usage

The framework invokes the stub automatically when `/sc:*` commands request
consensus or deep thinking. Example flags:

- `/sc:implement feature --consensus`
- `/sc:cleanup --thinkdeep`
- `/sc:business-panel --zen`

Outputs include:

- `consensus_reached`
- `final_decision`
- synthetic vote entries (`model`, `vote`, `confidence`)

## Limitations

- No API key or provider setup.
- No multi-tool orchestration beyond the simulated consensus.
- No conversation threading or continuation IDs.
- No CLI bridges (`zen__clink`) or remote MCP integration.

By keeping Zen lightweight, the framework remains deterministic and easy to
audit while still demonstrating how consensus hooks are wired. Live MCP support
would require a different build that re-introduces credentials, tool catalogues,
and networking—features intentionally omitted here.
