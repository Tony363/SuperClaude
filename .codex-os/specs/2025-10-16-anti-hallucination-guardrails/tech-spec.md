---
spec_id: 20251016-anti-hallucination-guardrails
title: Anti-Hallucination Guardrails — Technical Spec
owners: [@tony, @codex]
status: draft
updated: 2025-10-16
links:
  impl: ./tasks.md
---

## Architecture Overview
- Extend `CommandExecutor` so the requires-evidence path snapshots git, enumerates diff artifacts, and invokes static validation + quality scoring before declaring success.
- Emit telemetry via `PerformanceMonitor` with a dedicated `commands.requires_evidence.*` namespace for dashboards and alerting.
- Persist quality assessments alongside actionable suggestions in the command output for downstream automation (e.g., retry loops).

## Components
- `CommandExecutor`: orchestrates git snapshots, validation hooks, and error collation.
- `QualityScorer`: scores correctness/completeness/testability, enforces threshold, and returns improvement suggestions.
- `PerformanceMonitor`: central sink capturing counters, gauges, and histogram data for requires-evidence execution outcomes.
- Test harness: fixtures in `tests/test_commands.py` verifying guardrail enforcement and telemetry emission.

## Data Model
- Command result payload grows with `quality_assessment`, `quality_suggestions`, `static_validation_errors`, `executed_operations`, and `applied_changes`.
- Monitoring records include tags for `command`, `status`, `score`, and `threshold`; counters for plan-only, missing evidence, static validation failures, and quality pass/fail.
- No persistent storage schema changes required.

## APIs
- No external API contracts change. Guardrail feedback rides in command result JSON and monitoring events.
- Internal helper `_record_requires_evidence_metrics` gains new gauges (`quality_score`, `static_issue_count`) and counters (`missing_evidence`).

## Security & Privacy
- Validation only inspects workspace files (no network or external secrets).
- Errors avoid echoing raw source unless already present in diff output.
- Monitoring data contains command names and aggregated scores—no PII introduced.

## Observability & SRE
- Metrics namespace: `commands.requires_evidence.*`
  - Counters: `invocations`, `plan_only`, `missing_evidence`, `static_validation_fail`, `quality_pass`, `quality_fail`, `success`, `failure`.
  - Gauges: `quality_score`, `static_issue_count`.
  - Tags: `command`, `status`, optional `score`, `threshold`, and `issue_count`.
- Alert thresholds:
  - Page when `missing_evidence` > 0 for the same `command` within a 5-minute window.
  - Warn when `quality_fail` / `invocations` exceeds 0.2 over the last 15 minutes.
  - Warn when `static_validation_fail` ≥ 1 for two consecutive windows (indicates syntax errors slipping through).
- Dashboard layout (Grafana/Looker):
  1. Guardrail funnel (Invocations → Executed → Plan-only) stacked by command.
  2. Quality score gauge with P95 overlay and threshold line.
  3. Alert table listing recent missing-evidence and static-validation incidents with repo/session tags.
  4. Runbook links for remediation (docs/guardrail-monitoring.md).
- Quality assessment errors emit `quality_missing` counter for alerting when scoring is unavailable.
- Follow-up: wire dashboards (Grafana/Looker) using these metrics once telemetry sink shipping confirmed.

## Performance & NFRs
- Static validation limited to fast syntactic checks (e.g., `py_compile`) to keep latency <1s for single-file updates.
- Quality scoring remains in-process and should complete within 500ms for typical outputs.
- Guardrail leakage budget: <5% of requires-evidence runs should exit without evidence or actionable remediation.

## Risks & Alternatives
- Risk: Static validation may produce false negatives for unsupported languages → Mitigation: treat as warnings and expand validators iteratively.
- Risk: Quality scoring failures could block legitimate workflows → Mitigation: emit `quality_missing` metric and surface remediation hints; allow manual override for trusted operators.
- Alternative considered: executing full test suites for every run; rejected for cost—keep flag-based.

## Deployment
- No migrations. Ship via standard release (pytest + lint). Include regression tests for guardrail behavior.
- Monitoring sinks (SQLite/JSONL) already available; ensure deployment nodes have write permissions.
- Rollback: revert executor changes; telemetry additions are backwards compatible.
