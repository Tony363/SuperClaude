---
spec_id: 20251016-anti-hallucination-guardrails
title: Anti-Hallucination Guardrails
owners: [@tony, @codex]
status: draft
updated: 2025-10-16
links:
  roadmap: ../../product/analysis.md
---

## Summary
Deliver a verifiable workflow where `/sc:` commands that require evidence are blocked when they cannot demonstrate real repository changes or passing tests. The initiative closes the gap between aspirational guardrails and the current behavior by wiring automatic quality scoring, lightweight static validation, and telemetry-backed feedback.

## Users & Jobs
- Claude Code operators who expect the framework to refuse hallucinated diffs.
- QA and release engineers who audit automation logs for policy compliance.
- Product stewards who track anti-hallucination health metrics over time.

## Goals
- G1: Every command flagged `requires_evidence` fails fast without concrete diffs or test artifacts.
- G2: Static validation surfaces actionable errors for all reported Python/TS changes.
- G3: Quality scores, static validation failures, and missing-evidence counts emit structured metrics to the monitoring layer.
- Success metrics:
  - < 5% of `requires_evidence` executions exit as plan-only without actionable remediation notes.
  - 100% coverage of static validation on files declared in command output.
  - Dashboard visualizing `commands.requires_evidence.*` metrics with weekly review.

## Non-Goals
- NG1: Delivering fully autonomous remediation loops (agent self-healing).
- NG2: Adding new model providers or consensus algorithms.
- NG3: Implementing heavy static analyzers beyond syntactic checks.

## Scope
- In-scope: Command executor wiring, quality scoring integration, static validation hooks, telemetry for hallucination controls, doc/spec updates.
- Out-of-scope: UI/CLI changes, MCP integration rewrites, cost optimization for multi-model flows.

## User Experience
- Commands that fail guardrails explain the reason, suggested remediation, and next steps (diff/test requirement).
- Monitoring dashboards highlight failing guardrails so operators can triage hot spots.
- Documentation provides acceptance criteria and links to supporting specs/tasks.

## Assumptions
- Repository access is available for git diff snapshots.
- Tests run via `pytest`; additional runners may be configured later.
- No outbound network calls are permitted during validation.

## Open Questions
- Should consensus-based validation block non-evidence commands in future milestones?
- What thresholds roll up to product-level SLAs for hallucination incident response?
