# Test Suite Hardening Checklist

- [x] Agents & Loader: add regression tests that cover selector fallback when no specialist matches and verify exclusion handling so delegation failures are observable.
- [x] Extended Loader: replace time-based sleeps with injectable clock fixtures and add negative tests for unknown IDs or stale metadata in `explain_selection`.
- [x] Fast Codex Commands: stub the Codex CLI to assert successful plan execution paths, retries, and telemetry emission without requiring the real binary.
- [x] CodeRabbit Loop: cover missing env vars, degraded reviews, and taxonomy suppression so `_attach_coderabbit_review` and `_route_coderabbit_feedback` handle failures deterministically.
- [x] CLI Dispatch: add unit tests that invoke `main()` with patched operation modules to validate argument translation and dispatch without spawning subprocesses.
- [x] Codex Live: introduce mocked transports to exercise error handling, malformed payloads, and CodexUnavailable fallbacks when API keys are absent.
- [x] Browser MCP: add async tests for failure scenarios (navigation before init, screenshot errors, cleanup failures) and ensure coroutines use `pytest.mark.asyncio`.
- [x] MCP Integrations: parametrize server activation failures, telemetry emissions, and concurrency between Browser and CodeRabbit activation paths.
- [x] Model Router & Consensus: cover degraded states, unavailable-model exhaustion, invalid force/exclude inputs, and ensure async helpers rely on pytest's event loop fixtures.
- [x] Guardrails & Retrieval: add tests for toggling `requires_evidence`, repeated metric writes, and RepoRetriever failures to prove resilience across iterations.
- [x] Quality Pipeline: craft fixtures with multi-issue reviews, lint/test failures, and custom thresholds to validate evidence paths and degraded states.
- [x] Usage Tracker: simulate concurrent updates, missing metrics directories, and locked report files to ensure telemetry is durable.
- [x] Version Consistency: relax strict equality to compare all artifacts against the runtime version and downgrade README/CHANGELOG mismatches to actionable diagnostics.
- [x] Worktree State: simulate duplicate IDs, concurrent processes, and stale rows to guarantee cleanup and persistence correctness.
- [x] Integration Journeys: replace object-existence assertions with scenario-driven flows (e.g., `/sc:workflow` offline run or basic MCP conversation) to verify cross-component wiring.
