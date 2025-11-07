# Technical Architecture

This document describes how the SuperClaude Framework is assembled so new
contributors can map features to code quickly.

## 1. High-Level Overview

```
/sc:* command → CommandParser → CommandRegistry → CommandExecutor
                 │                                   │
                 │                                   ├─ ModelRouterFacade (model selection)
                 │                                   ├─ ConsensusBuilder (vote orchestration)
                 │                                   ├─ Agents (core + extended)
                 │                                   └─ Monitoring/Performance sinks
```

- **CommandParser/Registry** resolve CLI invocations into `CommandContext`
  instances with structured flags and metadata.
- **CommandExecutor** orchestrates agents, consensus, guardrails, quality loops
  and telemetry emission.
- **Agents** live under `SuperClaude/Agents/`. Core agents are Python classes,
  extended personas are Markdown playbooks that load on demand.
- **Consensus** relies on `ModelRouterFacade`, which now requires real provider
  executors. Offline runs must register custom executors explicitly; mock
  fallbacks were removed in favour of deterministic error reporting.

## 2. Command Execution Pipeline

1. Parsing produces a `ParsedCommand` and fetches the `CommandMetadata` entry.
2. `CommandExecutor` builds a `CommandContext`, including behavioural flags,
   session ID, and guardrail requirements.
3. The executor selects primary and supporting agents via `AgentLoader` and
   `ExtendedAgentLoader`.
4. Agent results feed into consensus if the command requires multi-model
   agreement (`requires_consensus` flag) or if the user supplies `--consensus`.
5. The quality loop (`QualityScorer`) validates correctness, maintainability,
   and evidence. Commands tagged `requires_evidence` must present a diff or a
   recorded plan.
6. Telemetry is written through `PerformanceMonitor` to SQLite/JSON lines under
   `.superclaude_metrics/`.

## 3. Model Routing & Consensus

- `ModelRouter` ranks candidate models using capability metadata and runtime
  availability. It no longer installs heuristic executors.
- `ModelRouterFacade` resolves provider clients (OpenAI, Anthropic, Google,
  X.AI). When credentials are missing it returns a structured error so callers
  can decide whether to retry or short-circuit.
- `ZenIntegration` (MCP) now delegates to `ModelRouterFacade.run_consensus`,
  re-packaging the payload into a simple dataclass. The integration therefore
  shares the same provider availability rules as the core executor.
- Tests that need deterministic behaviour register in-memory executors directly
  on `ConsensusBuilder`.

## 4. Auto-Implementation Artifacts

- When a command can only produce a plan, the executor writes structured files
  under `SuperClaude/Implementation/Auto/…`.
- Python and TypeScript stubs now emit real code that records the plan to
  `.superclaude_metrics/auto_implementation_plans.jsonl` instead of raising
  `NotImplementedError`.
- Markdown artefacts summarise the plan for human review; other languages fall
  back to a serialised plan function that logs steps via `console.info`.

## 5. Monitoring & Metrics

- `PerformanceMonitor` exposes timers/counters; sinks live in
  `SuperClaude/Monitoring/`. The default JSONL sink appends to
  `.superclaude_metrics/metrics.jsonl`.
- Quality and consensus payloads are included in command results so CI jobs can
  assert on them without reaching into internal modules.
- The benchmark harness (`benchmarks/run_benchmarks.py`) captures execution time
  for representative workloads and now forms part of the release checklist.

## 6. Data Storage

- Session artefacts and change plans are written into the workspace under
  `SuperClaude/Implementation/` and `.superclaude_metrics/`.
- Saved sessions use the UnifiedStore (SQLite at `~/.claude/unified_store.db`).
- Configuration lives in `SuperClaude/Config/`; consensus policies and MCP
  adapters read YAML files from this directory.

## 7. Extensibility

- Add new commands by creating a Markdown playbook under
  `SuperClaude/Commands/` with YAML front matter, then registering it in the
  `CommandRegistry`.
- New agents should extend `HeuristicMarkdownAgent` or one of the strategist
  classes so they inherit evidence capture and telemetry wiring.
- Additional MCP servers can be registered via `SuperClaude/MCP/__init__.py`; a
  server must expose `initialize()`, `initialize_session()`, and the async
  operation hooks used by `CommandExecutor`.

When in doubt, trace execution starting from `CommandExecutor.run_command`—it
serves as the central coordinator for everything described above.
