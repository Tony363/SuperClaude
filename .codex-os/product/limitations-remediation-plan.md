# SuperClaude Framework Limitations Remediation Plan

## Purpose
Provide a focused remediation roadmap for the current limitations that remain relevant after excluding documentation retrieval, heuristic-only consensus defaults, and roadmap integrations.

## Scope
- **Included limitations**
  - Auto-generated change plans blocked by the requires-evidence guardrail until humans supply diffs.
  - Extended personas relying on heuristic wrappers instead of strategist-class implementations.
  - Browser MCP integration kept opt-in and often disabled in local configs.
  - Test suite lacking end-to-end coverage for Claude Code IDE workflows.
- **Out of scope**
  - Documentation retrieval architecture.
  - Consensus and model routing heuristics.
  - Roadmap feature integrations (deployments, performance tuning, remote MCP servers).

## Guiding Principles
- Maintain requires-evidence safety guarantees while improving developer feedback loops.
- Prioritize high-traffic personas and user journeys when introducing strategist upgrades.
- Provide opt-in pathways that can graduate to defaults once telemetry confirms stability.
- Use incremental rollouts with measurable success criteria and regression tests.

## Workstream 1 – Requires-Evidence Friendly Change Application
1. [x] **Telemetry Enhancements (Week 1)**
   - Record stub-only plan runs with structured payloads in `.superclaude_metrics/plan_only.jsonl`.
   - Surface actionable guidance in CLI output summarizing missing diffs and suggested files.
   - _Success metric_: ≥90% of `/sc:implement` failures include explicit next-step hints.
2. [ ] **Safe Apply Mode (Week 2)**
   - Introduce a `--safe-apply` flag allowing operators to checkpoint generated stubs into a scratch worktree.
   - Guard writes behind explicit confirmation and auto-clean after review.
   - _Success metric_: No regression in `tests/test_commands.py::test_implement_stub_runs_fail_requires_evidence` while new tests cover safe-apply workflows.
3. [ ] **Quality Loop Integration (Week 3)**
   - Feed diff presence into the quality scorer to auto-request follow-up iterations when plan-only persists after safe apply.
   - _Success metric_: Quality loop emits remediation guidance in ≥80% of stub-only reruns during CI smoke tests.

## Workstream 2 – Strategist Upgrades for High-Traffic Personas
1. **Persona Prioritization (Week 1)**
   - Use `.superclaude_metrics/agent_usage.json` to rank extended personas by invocation frequency.
   - Finalize top 5 candidates and log decision in `.codex-os/product/decisions.md`.
   - _Success metric_: ADR created with rationale and rollout order.
2. **Python Strategist Implementations (Weeks 2-4)**
   - Port prioritized personas into Python strategist classes with domain-specific validation, mirroring `Agents/core/fullstack_developer.py` patterns.
   - Add unit tests in `tests/test_agents.py` ensuring new strategists return actionable operations and follow-up guidance.
   - _Success metric_: All promoted personas pass new strategist behavior tests and reduce plan-only outcomes by ≥20% in benchmarks.
3. **Heuristic Wrapper Decommission (Week 5)**
   - Update registry to fall back to strategist classes first, keeping markdown definitions as documentation only.
   - Remove unused heuristic metadata after verifying no regression in `tests/test_extended_loader.py`.
   - _Success metric_: Benchmarks show unchanged load times (<5% delta) and CLI smoke suite stays green.

## Workstream 3 – Browser MCP Enablement & UX
1. **Configuration UX (Week 1)**
   - Ship `SuperClaude --configure browser` helper that toggles `SuperClaude/Config/mcp.yaml` safely and validates prerequisites.
   - Provide CLI prompts reminding users to register the local browser MCP server.
   - _Success metric_: Helper covered by new integration test in `tests/test_cli.py` confirming config toggle behavior.
2. **Telemetry-Driven Defaulting (Weeks 2-3)**
   - Capture browser run stats (pass/fail, duration) in `.superclaude_metrics/browser_usage.jsonl`.
   - Define auto-opt-in criteria (e.g., five successful runs with no failures) and reflect state in CLI status output.
   - _Success metric_: Browser runs recorded for ≥70% of eligible test commands in internal smoke suite.
3. **Resilience Improvements (Week 4)**
   - Harden `_execute_browser_tests` with retry/backoff and clearer failure messaging.
   - Add regression tests simulating timeouts in `tests/test_browser_mcp.py`.
   - _Success metric_: Timeout simulations pass without crashing executor; user-facing warnings mention retry guidance.

## Workstream 4 – End-to-End IDE Coverage
1. **Harness Design (Week 1)**
   - Draft an IDE interaction harness under `tests/ide/` using headless mode to drive `/sc:implement` and `/sc:test` sequences.
   - Document assumptions and environment requirements in `Docs/Developer-Guide/ide-e2e.md`.
   - _Success metric_: ADR update plus harness skeleton merged without impacting existing test runtime.
2. **Scenario Authoring (Weeks 2-3)**
   - Create representative end-to-end scenarios (e.g., simple refactor, doc update) referencing fixtures in `examples/`.
   - Ensure each scenario asserts telemetry artifacts and guardrail outcomes.
   - _Success metric_: New pytest marker `ide_e2e` passes locally and in CI nightly workflow.
3. **Automation & Reporting (Week 4)**
   - Integrate harness into GitHub Actions nightly pipeline with artifact upload (screenshots, logs).
   - Add summary report generation via `scripts/report_ide_e2e.py`.
   - _Success metric_: Nightly job produces artifacts and posts status badge; failures auto-open GitHub issues via workflow.

## Risks & Mitigations
- **Telemetry overhead**: Batch writes and reuse UnifiedStore to avoid I/O spikes.
- **Persona regressions**: Roll out one strategist per release and gate behind feature flags.
- **Browser flakiness**: Keep helper opt-in until telemetry proves stability; provide manual disable flag.
- **CI runtime creep**: Run IDE E2E suite nightly with parallel shards; keep unit/PR suites unchanged.

## Next Steps
1. Socialize this plan at the next platform sync and capture feedback.
2. Create execution tickets aligned with each workstream milestone.
3. Kick off Workstream 1 telemetry enhancements to unblock other improvements.
