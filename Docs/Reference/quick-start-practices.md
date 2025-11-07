# Quick Start Practices

Use these habits to stay productive once you have the framework installed.

1. **Keep commands explicit.** Mention the file or subsystem in the prompt so
   the agent loader picks the right personas.
2. **Run benchmarks early.** `python benchmarks/run_benchmarks.py --suite smoke`
   takes seconds and catches CLI regressions immediately.
3. **Capture evidence.** Attach artefacts from
   `.superclaude_metrics/auto_implementation_plans.jsonl` to PRs when consensus
   rejects a run—reviewers can see the plan you executed.
4. **Fail fast without credentials.** The consensus layer now returns errors
   instead of heuristically approving work. Wire API keys into your shell or
   register local executors before starting a risky command.
5. **Tighten loops with `--think`.** Begin with `--think 1` for small fixes and
   escalate if you need deeper analysis. Higher levels activate more expensive
   models when available.
6. **Persist sessions intentionally.** Capture tarball snapshots with
   `SuperClaude backup --create` and clean up using `/sc:cleanup` once merged.
7. **Document decisions.** Update `.codex-os/product/decisions.md` whenever a
   command introduces a new pattern, dependency, or workflow.
