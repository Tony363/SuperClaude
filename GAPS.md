# Gaps Between README Claims and Codebase

- ~~`README.md:1` advertises **v6.0.0-alpha**, but `pyproject.toml:7`, `package.json:3`, and `VERSION` still report 4.x releases.~~ ✅ Resolved in v6.0.0-alpha promotion.
- Documentation tree (`README.md:376`, `README.md:500-514`, `README.md:531`) points to a `Docs/` directory that does not exist (`find . -maxdepth 1 -type d -iname 'docs'` returns nothing).
- Benchmark instructions (`README.md:392-393`) reference `benchmarks/run_benchmarks.py`, yet no `benchmarks/` directory is present.
- CLI flag examples (`README.md:162-164`, `README.md:277-279`, `README.md:326`) rely on `--think`, `--loop`, `--consensus`, and `--delegate`, but `CommandExecutor` never consumes those flags (`rg '--think'`, `rg '--loop'`, `rg '--consensus'`, `rg '--delegate'` under `SuperClaude/Commands` return no matches).
- MCP command manifests include `morphllm` (`SuperClaude/Commands/task.md:6`, `brainstorm.md:6`, `workflow.md:6`), yet `SuperClaude/MCP/__init__.py:68-75` registers only six integrations, so activating `morphllm` will fail.
