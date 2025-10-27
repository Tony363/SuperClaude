# Workflows Overview (Minimal Profile)

This summary captures the high-level commands and expectations from the full
`WORKFLOWS.md` guide without pulling the entire reference into the Claude Code
context. For detailed step-by-step playbooks, open
`SuperClaude/Core/WORKFLOWS.md` or install the full memory profile.

## Core Behaviours

- Always create a lightweight plan before touching code when a task involves
  more than a trivial edit.
- Capture evidence for `requires_evidence` commands: diff snippets, test
  results, and short rationale.
- Prefer incremental, reversible changes. Surface blockers in the summary if a
  plan cannot proceed.
- Record decisions in the relevant specification or ADR when the architecture
  changes.

## Common Commands

- `/sc:plan` → produce or update a change plan, identify risks, list follow-up
  tasks.
- `/sc:implement` → execute the plan, generate diffs, run targeted tests, and
  summarise the work performed.
- `/sc:test` → run the appropriate test suite (unit/integration/e2e) and report
  coverage gaps or flaky failures.
- `/sc:analyze` → review the codebase or specification, document hotspots, and
  propose mitigations.

Refer to the full workflow document for exhaustive scenarios, checklists, and
handoff templates.
