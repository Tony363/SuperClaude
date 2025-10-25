# Maintenance Toolkit

This guide covers the built-in hygiene tooling that keeps the SuperClaude Framework
focused and free of stale artifacts.

## Auto-Stub Cleanup

- `/sc:implement --cleanup` removes auto-generated stubs that still contain the
  placeholder banner and have not been touched for seven days.
- Use `--cleanup-ttl=<days>` to adjust the retention window for a single run.
- Safety rails:
  - Only files that still include the auto-generated sentinel text are eligible.
  - Files with pending git modifications are skipped.
  - Empty category folders under `SuperClaude/Implementation/Auto/` are pruned.

For scheduled maintenance, wire `/sc:cleanup --type files --safe` into cron and
add the `--cleanup` flag to any automation that calls `/sc:implement`.

## Agent Usage Report

- Every agent load and execution updates `.superclaude_metrics/agent_usage.json`.
- Generate a markdown dashboard with `python scripts/report_agent_usage.py`.
- The report groups agents into buckets:
  - **Active** – executed at least once.
  - **Observed** – loaded but not yet executed.
  - **Planned** – discovered personas without runtime usage yet.

To isolate telemetry for experiments, set `SUPERCLAUDE_METRICS_DIR` to an empty
directory before invoking commands; the script will honour the override.
