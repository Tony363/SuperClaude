## Implementation Plan — README Alignment

### 1. Release-State Alignment
- Decide whether to promote the codebase to match the v6.0.0-alpha feature set or amend the README back to v4.x.
- Update `README.md`, `CHANGELOG.md`, `pyproject.toml`, `package.json`, and `VERSION` so they cite the same release number.
- Add an automated check (unit test or lint rule) that fails when version strings diverge.

### 2. Restore Referenced Assets
- Recreate the documented `Docs/` hierarchy with stubs for the User Guide, API Reference, Developer Guide, and linked subsections.
- Provide placeholder content that references the existing materials under `SuperClaude/Core` so the links resolve immediately.
- Add a `benchmarks/` package containing a runnable `run_benchmarks.py` harness (even if it proxies to smoke tests) so README commands succeed.

### 3. Wire CLI Flags to Behavior
- Extend `CommandExecutor` to read `--think`/`--think N` and pass the requested think level into the model router and consensus facade.
- Honor `--loop` by invoking `QualityScorer.agentic_loop` when the flag is present (respecting optional iteration limits).
- Support `--consensus` by forcing `_ensure_consensus` and surfacing any consensus failures to the user.
- Implement auto-delegation for `--delegate` (and related variations) by selecting candidates through `AgentLoader`/`ExtendedAgentLoader` and recording selections in `CommandContext`.
- Add targeted unit coverage in `tests/test_model_router.py`, `tests/test_agents.py`, and any new test modules to protect these pathways.

### 4. Complete MCP Coverage
- Either remove the `morphllm` MCP reference from command manifests or deliver a stub `MorphLLMIntegration` registered in `SuperClaude/MCP/__init__.py` with configuration under `SuperClaude/MCP/configs/`.
- Include a smoke test that verifies activation of every listed MCP server to prevent future drift.

### 5. Documentation & Regression Protection
- Update README examples once the behaviors exist, clarifying the runtime requirements for new flags and tools.
- Add changelog entries summarizing the fixes and capture any architectural decisions in `.codex-os/product/decisions.md` if scope changes.
- Ensure CI runs the new tests and any benchmark harness smoke checks.
