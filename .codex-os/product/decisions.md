# Decisions Log

## 2025-10-17 – MCP Coverage Guardrail
- **Context:** CLI commands and documentation referenced the `morphllm` MCP server, but no integration was registered. New CLI flags (`--think`, `--loop`, `--consensus`, `--delegate`) required end-to-end validation to prevent future regressions.
- **Decision:** Ship a deterministic `MorphLLMIntegration` stub with a packaged recipe catalog and register it in the MCP factory. Added a smoke test that instantiates every enabled MCP server and verifies MorphLLM planning output. Documented runtime requirements for the new flags in the README.
- **Consequences:** Commands that declare `morphllm` now activate without error in offline environments. CI enforces MCP coverage and quality loop/consensus guardrails via targeted pytest runs and the benchmark smoke harness (`python benchmarks/run_benchmarks.py --suite smoke`).
