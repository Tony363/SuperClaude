# Test Modernization Plan for `/sc:` Command Suite

## Context
- Historical tests in `tests/test_commands.py` still assume the legacy `/sc:implement` pipeline that auto-generated real diffs, wrote plan-only telemetry files, and forced consensus scaffolding.
- Current executor behaviour emphasises fast-codex workflows, guardrail telemetry, and optional consensus depending on policies; the old expectations no longer match reality.
- Goal: rewrite the regression suite so it validates the modern behaviour end-to-end **without relying on mocks**, using real command execution and filesystem assertions.

## Objectives
1. **Align test expectations with current guardrails:** Ensure `requires_evidence`, fast mode fallbacks, consensus policies, and telemetry artefacts are verified exactly as produced today.
2. **Exercise commands as integration tests:** Each test should invoke the actual command executor, assert on tangible diffs/artifacts, and avoid mocks/stubs.
3. **Document new fixtures and flows:** Provide clear guidance so future contributors know how to run and extend the modern suite.

## Workstreams & Tasks

### WS-1 – Baseline Audit
- Capture current failure output for all `tests/test_commands.py` cases.
- Catalogue which expectations reflect obsolete behaviour (auto stubs, legacy consensus, plan-only snapshots).
- Produce a mapping table: *test name → modern behaviour to assert*.

### WS-2 – Fixture Overhaul
- Introduce reusable helpers that spin up a temporary repo workspace (e.g., via `tmp_path`) and execute `/sc:` commands end-to-end.
- Ensure fixtures clear `.superclaude_metrics`/`SuperClaude/Implementation` artefacts between tests to avoid cross-test pollution.
- Replace existing mock-based helpers with real command execution + deterministic assertions.

### WS-3 – `/sc:implement` Test Rewrite
- For each failing implement test:
  - Define the modern success criteria (e.g., fast-codex active, guardrails enforced, codex suggestions recorded).
  - Add filesystem assertions verifying actual diffs or plan-only artefacts produced by the current executor.
  - Confirm auto telemetry (metrics JSONL/SQLite) is written or intentionally skipped; adjust assertions accordingly.
- Include coverage for both standard and `--fast-codex` paths.

### WS-4 – Consensus & Telemetry Validation
- Inspect `SuperClaude/Config/consensus_policies.yaml` and codify the expectations (majority/quorum) in tests.
- Run commands that require consensus, assert on the real consensus payload returned, and verify failures when policies demand more than the heuristic provides.
- Validate telemetry outputs by reading actual `.superclaude_metrics` artefacts instead of expecting legacy file names.

### WS-5 – Business Panel & Ancillary Commands
- Update `/sc:business-panel` tests to inflate real agent output and confirm artefact creation without relying on mocks.
- Ensure supporting commands (build, test, git, workflow) have representative coverage that mirrors their modern behaviours.

### WS-6 – Documentation & CI Updates
- Document the new testing philosophy in `docs/testing.md` (or similar): no mocks, rely on integration-style assertions, clean-up expectations.
- Update CI workflows to surface `OPENAI_API_KEY`/`CODEX_API_KEY` for Codex integration tests when available.
- Provide troubleshooting guidance for contributors running the suite locally (e.g., how to supply keys, disable integration tests via marker skip if necessary).

## Deliverables
- Modernised `tests/test_commands.py` (and related modules) with passing integration tests against current behaviour.
- Updated documentation describing the new testing approach.
- CI pipeline configuration that runs the full suite with optional Codex integration when credentials are present.

## Success Metrics
- 100% pass rate for the rewritten command suite without mocks.
- No recurring loader/executor warnings during test runs.
- Codex integration test executes successfully in CI environments with keys; cleanly skipped otherwise.

