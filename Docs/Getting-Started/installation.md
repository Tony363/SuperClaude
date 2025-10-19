# Installation Guide (Stub)

Follow these steps to install SuperClaude while the expanded guide is rebuilt:

1. **PyPI installation**  
   ```bash
   pip install SuperClaude && SuperClaude install
   ```
2. **Validate the installation**  
   Run `SuperClaude --version` and the smoke benchmark:
   ```bash
   python benchmarks/run_benchmarks.py --suite smoke
   ```
3. **Review the core documentation**  
   - [Operations manual](../../SuperClaude/Core/OPERATIONS.md)
   - [Quickstart](../../SuperClaude/Core/QUICKSTART.md)

For environment specifics (conda, pipx, npm wrapper) consult the source modules
under `SuperClaude/Setup` until the full matrix returns.
