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

## 2. Milestones & Timeline
- **Milestone 1 (Week of 2025-11-03) – Consensus Enablement**
  - Implement real model executors for `ConsensusBuilder` (wrappers around local model stubs or deterministic prompts).
  - Calibrate vote thresholds per command (`implement`: quorum=3, `build`: majority, `test`: optional).
  - Update executor configuration to register executors and enforce calibrated thresholds.
  - Deliver regression tests covering consensus failure/success paths.
- **Milestone 2 (Week of 2025-11-10) – Semantic Validation & Telemetry**
  - Extend `_run_static_validation` to perform import graph checks, symbol lookup, and dependency inventory diffs.
  - Add semantic validator CLI for local use; integrate into CI.
  - Surface plan-only, missing-evidence, quality-fail metrics in PerformanceMonitor sinks and create Grafana-style dashboards (JSON spec checked into repo).
  - Configure CI guard (pre-merge) to fail on threshold breaches.
- **Milestone 3 (Week of 2025-11-17) – Testing & Grounding**
  - Add end-to-end pytest flows that run `/sc:implement` with deterministic agent fixtures producing real diffs.
  - Curate hallucination failure corpus for QualityScorer iteration loops.
  - Introduce retrieval-grounding hook (e.g., local repository index) wired into top personas.
  - Document new guardrails in README + `.codex-os/product/decisions.md`.

## 3. Workstreams & Tasks
| Workstream | Owner | Tasks | Deliverables |
|------------|-------|-------|--------------|
| Consensus Integration | Agent platform | Register executors, configure router ensembles, add quorum configs, write consensus fixture tests | Working consensus module with ≥2-model agreement documented |
| Semantic Validation | Framework core | Build import/symbol/static analyzers, handle language-specific adapters, expose CLI | Enhanced validator, CI job, developer docs |
| Observability | DevOps | Metrics aggregation to dashboards, alert thresholds, CI gate integration | Dashboard JSON, CI scripts, alert runbooks |
| Integration Testing | QA | Create deterministic fixtures, seed hallucination cases, expand pytest suite | New tests in `tests/integration/test_requires_evidence.py` |
| Retrieval Grounding | Agent platform | Implement local knowledge adapters (e.g., ripgrep-based retriever), update personas config, add fallbacks | Retrieval modules, updated agent configs |

## 4. Dependencies & Risks
- Availability of at least two deterministic local model executors; mitigated by shipping thin wrappers around existing stubs.
- Semantic validator performance on large repos; mitigate via caching and per-diff scope.
- Observability stack requires storage (SQLite/JSONL already available) and dashboard rendering; solution: generate static HTML report if full Grafana unavailable.
- Integration tests might be slow; mitigate by using focused fixtures and marking as `integration` to parallelize in CI.

## 5. Follow-Up Documentation
- Update `.codex-os/product/decisions.md` when consensus calibration and grounding hooks ship.
- Add troubleshooting guide for hallucination alerts under `Docs/hallucination-playbook.md`.
- Revisit this plan after Milestone 1 to adjust scope based on metrics.
