---
spec_id: 20251016-anti-hallucination-guardrails
title: Anti-Hallucination Guardrails — Task Plan
owners: [@tony, @codex]
status: draft
updated: 2025-10-16
links:
  tech-spec: ./tech-spec.md
---

## Legend
Type: feat | infra | tests | docs  
Estimate: S (≤2h), M (≤1d), L (≤3d), XL (>3d)

## Tasks (prioritized)
1. [HALL-001] Harden requires-evidence execution path (Type: feat, Est: M)
   - Rationale: Prevent hallucinated diffs from claiming success.
   - Changes: `SuperClaude/Commands/executor.py`, `SuperClaude/Quality/quality_scorer.py` (if needed), `tests/test_commands.py`.
   - Test Plan: pytest coverage for plan-only failure, static validation errors, quality assessment output.
   - Acceptance Criteria:
     - [ ] Commands with `requires_evidence` emit `quality_assessment`, `quality_suggestions`, and explicit missing-evidence errors when no diff is detected.
     - [ ] Static validation errors appear in `validation_errors` and block success.
     - [ ] Tests cover missing evidence + static validation scenarios.
2. [HALL-002] Instrument PerformanceMonitor telemetry (Type: infra, Est: S)
   - Rationale: Track guardrail health over time.
   - Changes: `SuperClaude/Commands/executor.py`, `SuperClaude/Monitoring/performance_monitor.py`, `tests/test_commands.py`.
   - Test Plan: unit tests asserting metrics (invocations, plan-only, missing evidence, quality score gauge) recorded.
   - Acceptance Criteria:
     - [ ] Metrics namespace includes `quality_score`, `static_issue_count`, `missing_evidence`.
     - [ ] Counter/gauge tags capture command name and status.
     - [ ] Monitoring test validates emitted metrics for plan-only failure.
3. [HALL-003] Document guardrail program (Type: docs, Est: S)
   - Rationale: Provide roadmap alignment and acceptance criteria for future work.
   - Changes: `ROADMAP.md`, `.codex-os/specs/2025-10-16-anti-hallucination-guardrails/*`.
   - Test Plan: docs review only.
   - Acceptance Criteria:
     - [ ] Roadmap includes anti-hallucination milestone with measurable criteria.
     - [ ] Spec folder contains SRD, tech spec, and task plan aligned with guardrail scope.
     - [ ] Links between roadmap and spec are documented.

## Milestones
- M1: Guardrail Enforcement — [HALL-001], [HALL-002] ✅ When evidence-free runs fail with actionable remediation and telemetry captured.
- M2: Product Alignment — [HALL-003] ✅ When roadmap/spec docs describe acceptance criteria and hand-offs.

## Out of Scope / Parking Lot
- P1: Automatic remediation loop that tries alternative agents when guardrails fail.
- P2: UI dashboard for metrics; requires downstream observability work.
