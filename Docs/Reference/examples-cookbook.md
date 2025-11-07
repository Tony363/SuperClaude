# Examples Cookbook

Quick recipes demonstrating how to chain SuperClaude commands.

## Implement + Test Loop

```bash
# Generate a plan and apply changes with fast consensus
python -m SuperClaude /sc:implement "refactor logging" --think 2 --consensus

# Run integration tests and benchmark afterwards
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/test_integration.py
python benchmarks/run_benchmarks.py --suite smoke --verbose
```

## Generate Workflow from a Spec

```bash
python -m SuperClaude /sc:workflow \
  "Implement feature spec" \
  --spec .codex-os/specs/2025-10-20-fast-codex-rollout/srd.md \
  --think 3 --consensus
```

The command emits a Markdown plan under `SuperClaude/Implementation/` and
captures consensus metadata for audit.

## Save, Pause, and Resume

```bash
SuperClaude backup --create --output ~/repos/app/.claude/backups/latest.tar.gz
SuperClaude backup --restore ~/repos/app/.claude/backups/latest.tar.gz --cwd ~/repos/app
```

Use this when you need to switch branches without losing telemetry or plan
artefacts. The backup command snapshots `.superclaude_metrics/`, change plans,
and the UnifiedStore database.

## Quickly Review Telemetry

```bash
python scripts/report_agent_usage.py
python -m SuperClaude /sc:document telemetry-dashboard --type guide --style brief
```

The report summarises agent activity, while `/sc:document` produces a focused
summary you can attach to retrospectives or status updates.
