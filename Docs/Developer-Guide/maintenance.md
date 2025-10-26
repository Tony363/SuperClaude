# Maintenance & Cleanup Guide

## Artifact Quarantine Procedure
- October 26, 2025: moved historical command evidence from `SuperClaude/Generated/` to `SuperClaude/quarantine/generated/` and relocated dated backups to `SuperClaude/quarantine/backups/20250826_192917`.
- Leave `SuperClaude/Generated/` and `SuperClaude/backups/` present with README files so runtime commands can recreate fresh artifacts without error.
- Keep quarantine artifacts for at least one week before deletion so we can confirm no workflows depend on the legacy data.

## Verification Checklist
1. Run `pytest tests/test_commands.py tests/test_worktree_state.py` to ensure the executor and worktree flows still execute. (As of 2025-10-26, `TestCommandExecutor.test_business_panel_executor_produces_panel_artifact` still fails with `dictionary changed size during iteration`; track this upstream bug separately.)
2. Manually spot-check `/sc:implement` and `/sc:business-panel` through the CLI if those commands are part of your workflow.
3. When the soak period finishes, delete `SuperClaude/quarantine/generated/` and `SuperClaude/quarantine/backups/` or archive them if no regressions surface.

## Future Automation
- Add a script to purge generated artifacts older than seven days after each run.
- Update CI to alert if quarantined artifacts exceed the retention window.
