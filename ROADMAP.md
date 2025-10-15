# SuperClaude Framework Roadmap

This roadmap captures the path to production-ready hallucination guardrails and reliable multi-agent execution.

## Version Status
- **Current**: v4.1.0 — Hallucination Guardrails (in progress)
- **Next Minor**: v4.2.0 — Consensus Validation
- **Next Major**: v5.0.0 — Production Agent Reliability
- **Long Term**: v6.0.0 — Autonomous Orchestration

---

## 🎯 v4.1.0 — Hallucination Guardrails (In Progress)
**Goal:** Block hallucinated diffs and plan-only responses by enforcing evidence, static validation, and quality scoring.

### Acceptance Criteria
- [x] Automatic quality scoring runs for every `requires_evidence` command and fails responses below the configured threshold. (Spec: 20251016-anti-hallucination-guardrails — Task HALL-001)
- [x] Static validation executes on all reported file changes and surfaces actionable errors when syntax compilation fails. (Spec: 20251016-anti-hallucination-guardrails — Task HALL-001)
- [x] Guardrail failures emit explicit user-facing remediation instructions (`Requires execution evidence...`). (Spec: 20251016-anti-hallucination-guardrails — Task HALL-001)
- [x] Telemetry records `commands.requires_evidence.*` counters/gauges for invocations, plan-only outcomes, missing evidence, and quality scores. (Spec: 20251016-anti-hallucination-guardrails — Task HALL-002)
- [ ] Dashboard and alert thresholds defined for `quality_fail`, `missing_evidence`, and `static_validation_fail` metrics.

### Key Deliverables
- Guardrail spec package: `.codex-os/specs/2025-10-16-anti-hallucination-guardrails/`
- Regression tests covering plan-only failures, static validation errors, and telemetry emission.
- Updated CLI guidance ensuring operators understand remediation output.

---

## 🧭 v4.2.0 — Consensus & Multi-Agent Reliability
**Goal:** Require multi-model agreement before success is reported and feed consensus outcomes into guardrails.

### Acceptance Criteria
- [ ] `ConsensusBuilder` integrated into validator pipeline for `/sc:implement` and `/sc:build`.
- [ ] Evidence payloads include consensus summary and dissenting agent notes.
- [ ] Guardrail metrics track consensus disagreements and retries.
- [ ] ADR captured for consensus thresholds and override policy.

---

## 🚀 v5.0.0 — Production Agent Reliability
**Goal:** Deliver end-to-end agent flows with deterministic evidence (diffs, tests, telemetry) in CI and release automation.

### Acceptance Criteria
- [ ] At least three top personas execute fully automated change workflows with passing tests.
- [ ] CI integrates guardrail metrics and blocks deployments on `quality_fail` spikes.
- [ ] Secrets handling, sandboxing, and rollback strategies documented in `product/decisions.md`.

---

## 🌌 v6.0.0 — Autonomous Orchestration
**Goal:** Coordinate dozens of agents with adaptive evidence gathering, real-time monitoring, and self-healing pipelines.

### Acceptance Criteria
- [ ] Dynamic load/trigger system activates agents based on telemetry hot spots.
- [ ] Hallucination incident response playbooks automated via Monitoring + MCP.
- [ ] Performance budgets maintained (<100ms load time, <5% hallucination rate) with quarterly reviews.

---

## References
- Spec: `.codex-os/specs/2025-10-16-anti-hallucination-guardrails/`
- Product analysis: `.codex-os/product/analysis.md`
- Metrics sink design: `SuperClaude/Monitoring/performance_monitor.py`
