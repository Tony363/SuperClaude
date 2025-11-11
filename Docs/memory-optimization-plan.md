# Memory Profile Optimization Plan

Goal: reduce the default token footprint of Claude Code memory files installed by
`SuperClaude install`, while retaining the option to deploy the full guidance
bundle when needed.

## Milestones

- [x] Audit current memory imports and identify large `.md` bundles per component.
- [x] Define "minimal" vs "full" memory profiles and document their file lists.
- [x] Update installer components (core, agents, modes, MCP docs) to deploy files based on the selected profile.
- [x] Extend the CLI (`SuperClaude install`) to accept a `--memory-profile` flag, defaulting to the minimal bundle, and refresh README/docs accordingly.
- [x] Provide a token verification script (or command) and document how to audit the installed memory footprint.

Each milestone will be checked off as the work lands.

### Audit Notes

- **Core component** installs every Markdown file in `SuperClaude/Core/` (e.g., `RULES_*`, `OPERATIONS.md`, `AGENTS*.md`, `BUSINESS_*`). The heaviest contributors are `OPERATIONS.md`, `WORKFLOWS.md`, `AGENTS_EXTENDED.md`, and the business panel guides (>2 k tokens each).
- **Agents component** copies all top-level persona `.md` files in `SuperClaude/Agents/`, including the extended catalogues and business assistants.
- **Modes component** imports all `MODE_*.md` files even though most sessions only require `MODE_Normal.md` and `MODE_Task_Management.md`.
- **MCP docs** default to installing `MCP_Zen.md`, `MCP_Rube.md`, and `MCP_LinkUp.md`. Their footprint is modest, but they still count toward the memory bundle.

### Profile Definitions (current state)

- **Minimal core bundle**: `AGENTS.md`, `CHEATSHEET.md`, `CLAUDE_CORE.md`, `FLAGS.md`, `PRINCIPLES.md`, `QUICKSTART.md`, `RULES.md`, `RULES_CRITICAL.md`, `RULES_RECOMMENDED.md`, `TOOLS.md`, `WORKFLOWS_SUMMARY.md`, `OPERATIONS_SUMMARY.md`.
- **Full core bundle**: all Markdown files in `SuperClaude/Core/` (including extended agents, business references, and full workflow/operations manuals).
- **Minimal modes**: `MODE_Normal.md`, `MODE_Task_Management.md`, `MODE_Token_Efficiency.md`.
- **Full modes**: every `MODE_*.md` file (adds Brainstorming, Introspection, Orchestration, Business Panel).
- **Agents**: unchanged for now (top-level persona `.md` files ship in both profiles); extended persona catalogues stay inside the core bundle rather than the agents component.
