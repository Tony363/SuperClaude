# Zen MCP Integration

The Zen integration exposes SuperClaude's consensus engine over the Model
Context Protocol. It now delegates to the live `ModelRouterFacade` instead of a
mock heuristic.

## Capabilities

- **Consensus:** Executes the same voting logic as the core executor.
- **Thinking modes:** Maps MCP thinking levels to `--think` values (minimal → 1,
  max → 5).
- **Quorum rules:** Respects the `vote` parameter supplied by the client; quorum
  size defaults to `⌈n/2⌉ + 1` when unspecified.

## Configuration

- Enable in `SuperClaude/Config/mcp.yaml` under the `zen` entry.
- Optional environment variables:
  - `SC_ZEN_OFFLINE=1` to force offline mode (expect explicit executor
    registration).
  - `SUPERCLAUDE_OFFLINE_MODE=1` to turn off provider lookups globally.

## Usage

```python
from SuperClaude.MCP import ZenIntegration
from SuperClaude.ModelRouter.facade import ModelRouterFacade

facade = ModelRouterFacade()
zen = ZenIntegration(facade=facade)
zen.initialize()
await zen.initialize_session()
result = await zen.consensus("Approve deployment?", models=None)
```

## Error Handling

- If no provider executors are registered the integration raises `RuntimeError`
  instead of returning fabricated votes.
- Downstream callers should catch the exception and either register custom
  executors (for offline tests) or prompt the operator to configure API keys.

## Telemetry

- Consensus payloads contain the selected models, agreement score, and
  per-model metadata. Capture them in your MCP client logs for auditing.

Refer to `Docs/User-Guide/mcp-servers.md` for broader MCP configuration details.
