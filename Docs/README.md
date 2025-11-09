# SuperClaude Documentation Hub

> This directory mirrors the structure described in the README and points to the
> authoritative resources already shipped under `SuperClaude/Core`.

## Quick Starts and Essentials

- [User Guide](User-Guide/README.md) — Daily workflows and command usage.
- [API Reference](Reference/README.md) — Module-level integration notes.
- [Developer Guide](Developer-Guide/README.md) — Architecture and contribution tips.

For the most detailed, always up-to-date information, consult the curated core
documents:

- [QUICKSTART](../SuperClaude/Core/QUICKSTART.md)
- [CHEATSHEET](../SuperClaude/Core/CHEATSHEET.md)
- [OPERATIONS Manual](../SuperClaude/Core/OPERATIONS.md)

These stubs anchor the documentation links advertised in `README.md` and will
expand alongside the regenerated manuals.

## CodeRabbit Integration Quick Notes

- **Configuration** lives in `Config/coderabbit.yaml` (mirrored under `config/` on macOS). Set `CODERABBIT_API_KEY` in CI or locally; `CODERABBIT_REPO` and `CODERABBIT_PR_NUMBER` default to the current GitHub slug/PR.
- **Quality gate CLI**: `python -m SuperClaude.Quality.coderabbit_gate --threshold production_ready --allow-degraded` blends SuperClaude + CodeRabbit scoring and writes telemetry to `.superclaude_metrics/ci/coderabbit_gate.jsonl`.
- **Degraded mode** is automatic when `ci.allow_degraded` is enabled in the config; gate output and telemetry include `coderabbit_status` so pipelines can surface neutral vs. blocking outcomes.
- **Secrets & logging**: the gate (and client) redact keys such as `api_key`, `token`, `secret`, and `authorization` before storing artifacts, satisfying the rotation guidance described in the integration plan.
