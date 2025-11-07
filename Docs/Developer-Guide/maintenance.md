# Maintenance & Cleanup Guide (November 2025)

## Artifact Hygiene
- Worktree outputs now land directly in `SuperClaude/Implementation/` and
  `.superclaude_metrics/`. We no longer maintain the temporary
  `SuperClaude/quarantine/` hierarchy.
- Keep `SuperClaude/backups/README.md` in place so backup tasks can recreate
  dated directories on demand.
- When retiring generated artefacts, remove empty directories in the
  implementation tree to prevent stale breadcrumbs in the CLI summary.

## Verification Checklist
1. Run `pytest tests/test_commands.py tests/test_worktree_state.py` before and
   after large refactors to confirm executor and worktree guardrails remain
   healthy.
2. Manually exercise `/sc:implement` and `/sc:business-panel` via the CLI when
   changing guardrail or persona loading behaviour.
3. Confirm `.superclaude_metrics/` contains fresh telemetry after maintenance
   jobs; missing metrics should now surface as command failures.

## Future Automation Ideas
- Add a cleanup flag to `/sc:cleanup` that prunes stale auto-implementation
  artefacts older than a configurable number of days.
- Extend CI to alert when `.superclaude_metrics/` exceeds target size so we can
  rotate logs proactively.
