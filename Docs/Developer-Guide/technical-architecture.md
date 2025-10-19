# Technical Architecture (Stub)

SuperClaude's architecture is documented primarily inside the curated core
bundle:

- [Core profile](../../SuperClaude/Core/CLAUDE_CORE.md) — active modules under
  the 40KB optimized footprint.
- [Extended profile](../../SuperClaude/Core/CLAUDE_EXTENDED.md) — optional
  modules, coordination strategies, and MCP overlays.
- [Model router facade](../../SuperClaude/ModelRouter/facade.py) — programmatic
  entry point for orchestrating providers.

## System Overview

- **Agents**: see [AGENTS.md](../../SuperClaude/Core/AGENTS.md) for domain
  coverage.
- **Commands**: inspect the dispatcher
  [`SuperClaude/Commands/executor.py`](../../SuperClaude/Commands/executor.py).
- **Quality Loop**: check the quality scorer at
  [`SuperClaude/Quality/quality_scorer.py`](../../SuperClaude/Quality/quality_scorer.py).

Detailed diagrams and deployment blueprints will return alongside the full
v6 documentation refresh.
