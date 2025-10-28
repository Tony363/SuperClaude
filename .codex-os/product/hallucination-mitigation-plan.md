# Hallucination Mitigation Plan

## 0. Context
- Source analysis: `.codex-os/product/analysis.md` (2025-10-27).
- Target outcomes: Reduce plan-only completions, ensure consensus uses real ensembles, surface hallucination regressions within CI/observability, and ground agent outputs with verifiable evidence.
- Constraints: Offline-first runtime, limited MCP roster (Sequential, Zen, Deepwiki), rely on git evidence and local tests.

## 1. Goals & Success Metrics
- **G1 – Reliable consensus:** All `requires_evidence` commands succeed only after multi-model agreement.
  - *Metric:* ≥95% of consensus-enforced runs reach agreement using ≥2 distinct models (tracked via `commands.requires_evidence.consensus`).
- **G2 – Semantic validation:** Automatically block hallucinated diffs that reference missing symbols or modules.
  - *Metric:* 0 releases with post-run missing-import regressions; static validator CI job catches ≥90% of seeded semantic failures.
- **G3 – Observability:** Hallucination telemetry drives automated feedback loops.
  - *Metric:* CI fails when plan-only rate >5% per suite; dashboards show 7-day trend for plan-only, quality-fail, consensus-fail.
- **G4 – Guardrail tests:** Golden-path integration tests prevent regressions in `/sc:implement` and `/sc:build` flows.
  - *Metric:* New pytest integration suite runs in CI and fails on seeded plan-only scenarios.

## 2. Spec Tasks

### [x] Task HT-001 — Enable Consensus Executors
- **Summary:** Register deterministic model executors for `ConsensusBuilder` and enforce tuned agreement thresholds on all `requires_evidence` commands.
- **Key Steps:**
  1. Implement lightweight executors (e.g., local stub runners) and bind them with `ConsensusBuilder.register_executor`.
  2. Configure router ensembles and per-command quorum/majority settings in the command metadata layer.
  3. Extend `_ensure_consensus` tests to cover agreement, disagreement, and cache scenarios.
- **Acceptance Criteria:**
  - Executor logs include at least two distinct model votes per consensus run in offline mode.
  - `/sc:implement` fails when consensus quorum is not achieved.
  - New pytest coverage proving success/failure pathways (`tests/test_consensus_execution.py`).
- **Deliverables:** Updated consensus module, router configuration, consensus-focused tests, documentation snippet in README.

### [x] Task HT-002 — Add Semantic Static Validation
- **Summary:** Expand `_run_static_validation` to catch missing imports, undefined symbols, and dependency mismatches before success is reported.
- **Key Steps:**
  1. Build Python import graph analyzer using `ast` and `importlib.util` to ensure referenced modules exist.
  2. Add language adapters (JSON schema, TypeScript stub) as needed; expose CLI `scripts/semantic_validate.py`.
  3. Integrate validator into CI pipeline with seeded failure fixtures.
- **Acceptance Criteria:**
  - Plan-only outputs triggered by missing imports surface actionable error messages.
  - CI job `pytest --integration semantic_validation` fails on injected unresolved symbol cases.
  - Developer doc updated with validator usage.
- **Deliverables:** Enhanced validator code paths, CLI tool, CI config, doc updates.

### [x] Task HT-003 — Instrument Hallucination Telemetry & Alerts
- **Summary:** Turn existing metrics into dashboards and automated gates that block regressions when plan-only or quality-fail rates spike.
- **Key Steps:**
  1. Emit structured events from `_record_requires_evidence_metrics` with pass/fail metadata and consensus scores.
  2. Generate dashboard JSON (or static HTML report) visualizing 7-day trends and per-command breakdowns.
  3. Add CI guard that fails when plan-only rate exceeds 5% per suite.
- **Acceptance Criteria:**
  - Dashboards or reports render locally from repo artifacts.
  - CI pipeline aborts on simulated plan-only spike.
  - Runbook describes alert response steps.
- **Deliverables:** Metrics schema updates, dashboard/report assets, CI guard scripts, runbook.

### [x] Task HT-004 — Ship Guardrail Integration Tests
- **Summary:** Create deterministic end-to-end tests that exercise `/sc:implement` and `/sc:build` with real diffs under `requires_evidence`.
- **Key Steps:**
  1. Build fixture agents that apply predictable file edits and run tests.
  2. Capture plan-only failure fixtures for regression detection.
  3. Wire tests into CI with `integration` marker.
- **Acceptance Criteria:**
  - Tests fail before tasks HT-001/002 complete and pass afterwards.
  - Evidence artifacts captured in test output for auditing.
  - Execution time ≤5 minutes total.
- **Deliverables:** Integration test suite, fixtures, CI configuration.

### [x] Task HT-005 — Introduce Retrieval Grounding Hooks
- **Summary:** Provide agents with retrieval-based context (e.g., repo indexing) to reduce speculative reasoning.
- **Key Steps:**
  1. Implement retriever module that searches local repo (ripgrep/AST index) and returns relevant snippets.
  2. Update top personas to call retriever before generating plans.
  3. Add telemetry to track retrieved context usage.
- **Acceptance Criteria:**
  - Agents log retrieved references for ≥80% of implement runs.
  - Quality scorer metrics show ≥10 point improvement on seeded hallucination corpus.
  - Documentation covers configuration and fallback behavior.
- **Deliverables:** Retrieval module, persona config updates, telemetry wiring, docs.

## 3. Schedule Overview
- [x] Week of 2025-11-03: Run Task HT-001 & HT-004 in parallel to activate consensus and proof tests.
- [x] Week of 2025-11-10: Complete Task HT-002 and HT-003 (semantic validator plus telemetry/alerts).
- [x] Week of 2025-11-17: Deliver Task HT-005 and refresh documentation/decisions.

## 4. Workstreams & Roles
| Workstream | Owner | Tasks | Deliverables |
|------------|-------|-------|--------------|
| Consensus Integration | Agent platform | Register executors, configure router ensembles, add quorum configs, write consensus fixture tests | Working consensus module with ≥2-model agreement documented |
| Semantic Validation | Framework core | Build import/symbol/static analyzers, handle language-specific adapters, expose CLI | Enhanced validator, CI job, developer docs |
| Observability | DevOps | Metrics aggregation to dashboards, alert thresholds, CI gate integration | Dashboard JSON, CI scripts, alert runbooks |
| Integration Testing | QA | Create deterministic fixtures, seed hallucination cases, expand pytest suite | New tests in `tests/integration/test_requires_evidence.py` |
| Retrieval Grounding | Agent platform | Implement local knowledge adapters (e.g., ripgrep-based retriever), update personas config, add fallbacks | Retrieval modules, updated agent configs |

## 5. Dependencies & Risks
- Availability of at least two deterministic local model executors; mitigated by shipping thin wrappers around existing stubs.
- Semantic validator performance on large repos; mitigate via caching and per-diff scope.
- Observability stack requires storage (SQLite/JSONL already available) and dashboard rendering; solution: generate static HTML report if full Grafana unavailable.
- Integration tests might be slow; mitigate by using focused fixtures and marking as `integration` to parallelize in CI.

## 6. Follow-Up Documentation
- Update `.codex-os/product/decisions.md` when consensus calibration and grounding hooks ship.
- Add troubleshooting guide for hallucination alerts under `Docs/hallucination-playbook.md`.
- Revisit this plan after Milestone 1 to adjust scope based on metrics.
