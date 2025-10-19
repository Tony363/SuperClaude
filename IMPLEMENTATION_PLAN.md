## Implementation Plan — README Alignment

### 1. Deliver Evidence-Backed Command Execution
- Evolve `/sc:implement` and other requires-evidence commands so agent pipelines can propose edits, apply them via the worktree manager, and only report success after detecting repository diffs and passing tests.
- Emit explicit quality and test artifacts in the command result, and fail fast when no evidence is produced.
- Add regression tests that confirm a simple implementation task generates a diff and surfaces errors otherwise.

### 2. Honor `/sc:test` Flags
- Extend `_run_requested_tests` to translate `--coverage`, `--e2e`, targets, and markers into the appropriate `pytest` arguments and capture coverage output.
- Surface structured test results (pass rate, coverage, logs) in the executor response and treat failures as hard errors.
- Cover the new behavior with unit tests around `_run_requested_tests` plus an integration test for `/sc:test --coverage`.

### 3. Implement a Real Quality Loop
- Replace the identity improver with a remediation pipeline that can re-invoke selected agents, apply suggested fixes, rerun tests, and re-evaluate quality until thresholds are met or retries are exhausted.
- Persist loop iteration history and outcomes in the command payload so downstream guardrails have actionable data.
- Add tests that simulate a failing assessment and verify the loop adjusts the output or propagates a failure.

### 4. Wire Multi-Model Consensus to Real Providers
- Connect `ModelRouterFacade` to concrete `OpenAIClient`/provider adapters, managing rate limits and fallbacks while retaining deterministic mocks for offline test mode.
- Ensure consensus failures propagate back to commands and block requires-evidence workflows when agreement is not reached.
- Introduce asynchronous tests that exercise consensus across multiple models using recorded fixtures.

### 5. Flesh Out Operational Command Handlers
- Implement real behaviors for `/sc:build`, `/sc:git`, `/sc:workflow`, and similar operational commands so they execute the advertised automation or emit actionable errors.
- Capture artifacts (logs, git outputs) alongside success/failure status for traceability.
- Add unit and smoke tests that validate each command’s side effects align with README promises.
