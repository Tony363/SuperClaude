# Quick Start

This walkthrough shows how to execute a full `/sc:implement` cycle on a sample
repository.

## 1. Create a Playground Repository

```bash
mkdir ~/superclaude-playground
cd ~/superclaude-playground
git init
cat <<'PY' > app.py
def greet(name: str) -> str:
    return f"hello {name}"  # TODO: capitalise
PY
```

## 2. Launch the Implement Command

From the framework checkout, run:

```bash
python -m SuperClaude --cwd ~/superclaude-playground \
  /sc:implement "capitalise greeting" --think 2 --consensus
```

- `--cwd` points the executor at the target repository.
- `--think 2` enables deeper routing. Try `--think 3` for more exhaustive
  exploration.
- `--consensus` forces the ModelRouter to gather votes. Without provider keys
  you will receive a clear error prompting you to register executors.

## 3. Review Artefacts

- Inspect `~/superclaude-playground/SuperClaude/Implementation/Auto/` for
  generated plans or edits.
- Metrics and consensus payloads are captured under
  `~/superclaude-playground/.superclaude_metrics/`.

## 4. Run Tests & Benchmarks

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
python benchmarks/run_benchmarks.py --suite smoke --verbose
```

The benchmark suite confirms the CLI remains healthy and records execution time
for future comparisons.

## 5. Iterate Quickly

- Use `--fast-codex` for low-risk diffs once you have supplied API keys.
- Combine `--safe` with `--consensus` when touching security-sensitive modules.
- Capture notes with `/sc:document` after significant edits; it writes concise
  summaries you can attach to PRs.

You now have a repeatable workflow from prompt to diff with telemetry and
benchmarks baked in.
