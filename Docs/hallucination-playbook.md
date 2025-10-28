# Hallucination Guardrail Playbook

## Responding to Alerts
1. **Inspect telemetry:** Review `.superclaude_metrics/metrics.jsonl` or the SQLite sink to confirm `hallucination.guardrail` events and identify offending commands.
2. **Check plan-only ratio:** Run `python scripts/check_hallucination_metrics.py --threshold 0.05` to ensure CI guard thresholds hold.
3. **Review consensus summary:** Examine `consensus` payload inside command output for disagreement details and model votes.
4. **Validate evidence:** Rerun the command locally with `--verbose` to capture diff summaries and quality scores.

## Remediation Steps
- **Consensus failure:** Verify model executors are available; adjust quorum thresholds in `SuperClaude/Config/consensus_policies.yaml` if specific commands are too strict.
- **Semantic validation failure:** Run `python scripts/semantic_validate.py <path>` (after Task HT-002) to identify missing modules or unresolved names.
- **Plan-only spike:** Investigate agent outputs recorded in `.superclaude_metrics/agent_usage.json` and ensure retrieval context was attached.
- **Quality degradation:** Inspect `quality_assessment` suggestions included in command warnings and loop iteration history.

## Preventive Checklist
- Keep repository retriever up to date by calling `RepoRetriever.refresh()` after large structural changes.
- Record telemetry dashboards updates in `Docs/monitoring/hallucination_dashboard.json` for shared visualization.
- Add new regression cases to `tests/integration/test_requires_evidence.py` whenever a hallucination bug is fixed.
