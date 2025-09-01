# SuperClaude Framework Cheatsheet

> **Quick lookup for the SuperClaude framework. For details, see master docs: [WORKFLOWS.md](WORKFLOWS.md) | [FLAGS.md](FLAGS.md) | [AGENTS.md](AGENTS.md) | [RULES.md](RULES.md)**

## 🚀 Quick Decision Guide
| I want to... | Use this | Detailed Guide |
|-------------|----------|----------------|
| Explore ideas | `--brainstorm` | [Brainstorming Mode](MODE_CORE.md#brainstorming-mode) |
| Debug issues | `--think` → Task (root-cause-analyst) | [Debug Workflows](WORKFLOWS.md#debugging--investigation) |
| Optimize performance | `--think-hard` + Task (performance-engineer) | [Performance Optimization](WORKFLOWS.md#performance-optimization) |
| Build UI components | `--magic` or `/ui` | [UI Component Creation](WORKFLOWS.md#ui-component-creation) |
| Refactor code | Task (refactoring-expert) | [Refactoring Workflow](WORKFLOWS.md#refactoring-workflow) |
| Generate docs | Task (technical-writer) | [API Documentation](WORKFLOWS.md#api-documentation) |
| Run tests | `--test` after changes | [Testing Flags](FLAGS.md#testing--quality-flags) |
| Save tokens | `--uc` or `--token-efficient` | [Token Efficiency](MODE_CORE.md#token-efficiency-mode) |

## 🎯 Essential Flags

> **Complete Reference**: [FLAGS.md](FLAGS.md) - All flags, triggers, combinations, and conflicts

| Category | Key Flags | Purpose |
|----------|-----------|---------|
| **Discovery** | `--brainstorm`, `--introspect` | Requirements, self-analysis |
| **Execution** | `--task-manage`, `--orchestrate` | Organization, tool routing |
| **Analysis** | `--think`, `--think-hard`, `--ultrathink` | 4K, 10K, 32K token analysis |
| **Quality** | `--test`, `--review`, `--safe-mode` | Testing, validation, safety |
| **Efficiency** | `--uc`, `--delegate` | Token saving, parallel processing |

## 🔄 Behavioral Modes

> **Complete Mode Guide**: [MODE_CORE.md](MODE_CORE.md) | [MODE_EXECUTION.md](MODE_EXECUTION.md) - Detailed activation triggers and behavioral changes

| Mode | When to Use | Reference |
|------|-------------|-----------|
| **Brainstorming** | Vague requests, exploration | [MODE_CORE.md](MODE_CORE.md#brainstorming-mode) |
| **Introspection** | Error recovery, self-analysis | [MODE_CORE.md](MODE_CORE.md#introspection-mode) |
| **Task Management** | >3 steps, complex operations | [MODE_EXECUTION.md](MODE_EXECUTION.md#task-management-mode) |
| **Orchestration** | Multi-tool, performance constraints | [MODE_EXECUTION.md](MODE_EXECUTION.md#orchestration-mode) |
| **Token Efficiency** | Resource limits, >75% context | [MODE_CORE.md](MODE_CORE.md#token-efficiency-mode) |

## 🛠️ Tool Selection

> **Complete Tool Matrix**: [FLAGS.md](FLAGS.md#mcp-server-flags) - MCP servers, triggers, and integration patterns

### MCP Servers Quick Reference
| Task Type | Best MCP Server | Alternative |
|-----------|-----------------|-------------|
| **UI components** | Magic | Manual coding |
| **Complex analysis** | Sequential | Native reasoning |
| **Bulk code edits** | Morphllm | Individual edits |
| **Browser testing** | Playwright | Unit tests |
| **Documentation** | Deepwiki | Web search |
| **Symbol operations** | Serena | Manual search |

### Task Agent Selection

> **Complete Agent Guide**: [AGENTS.md](AGENTS.md#agent-catalog) - Full catalog with examples and quality frameworks

| Purpose | Agent | Use Case |
|---------|-------|----------|
| **Exploration** | `general-purpose` | Unknown scope, broad searches |
| **Debugging** | `root-cause-analyst` | Error investigation, systematic debugging |
| **Code Quality** | `refactoring-expert` | Technical debt, systematic improvements |
| **Documentation** | `technical-writer` | API docs, comprehensive documentation |
| **Architecture** | `system-architect` | Design decisions, scalability |
| **Performance** | `performance-engineer` | Optimization, bottleneck analysis |

## ⚡ Quick Workflow Patterns

> **Complete Workflows**: [WORKFLOWS.md](WORKFLOWS.md) - Step-by-step processes for all scenarios

| Scenario | Quick Pattern | Full Guide |
|----------|---------------|------------|
| **Debug Test** | `--think → Task(root-cause-analyst) → Fix → --test` | [Debug Failed Test](WORKFLOWS.md#debug-failed-test) |
| **New Feature** | `--brainstorm → --task-manage → TodoWrite → Implement → Validate` | [New Feature Standard](WORKFLOWS.md#new-feature-standard) |  
| **Performance** | `--think-hard → Task(performance-engineer) → Optimize → Measure` | [Performance Optimization](WORKFLOWS.md#performance-optimization) |
| **UI Component** | `--magic → /ui → Magic MCP → Playwright → Integration` | [UI Component Creation](WORKFLOWS.md#ui-component-creation) |

## 🔴 Critical Rules

> **All Rules**: [RULES.md](RULES.md) - Complete behavioral rules with priority system and detection methods

| Priority | Rule | Reference |
|----------|------|-----------|
| **🔴 CRITICAL** | Always `git status` first | [Git Workflow](RULES.md#git-workflow) |
| **🔴 CRITICAL** | Quality score ≥ 70 or iterate | [Quality Framework](RULES.md#quality-evaluation-system) |
| **🟡 IMPORTANT** | Complete all started features | [Implementation Completeness](RULES.md#implementation-completeness) |
| **🟡 IMPORTANT** | Build only what's requested | [Scope Discipline](RULES.md#scope-discipline) |
| **🟢 RECOMMENDED** | Clean workspace after operations | [Workspace Hygiene](RULES.md#workspace-hygiene) |

## 💡 Essential Patterns & Decision Trees

> **Complete Reference**: [FLAGS.md](FLAGS.md#flag-priority-rules) | [RULES.md](RULES.md#tool-optimization) | [AGENTS.md](AGENTS.md#selection-decision-trees)

**Key Combinations**: `--think + --sequential` (deep analysis) | `--task-manage + --uc` (efficient tracking) | `--safe-mode + --validate` (maximum safety)

**Decision Hierarchy**: Tool Selection (MCP > Native > Basic) | Agent Selection (Specialist > General) | Quality Control (Score < 70 = Auto-iterate)

## 📚 Master Documentation Navigation

| Topic | File | Key Sections |
|-------|------|--------------|
| **Workflows** | [WORKFLOWS.md](WORKFLOWS.md) | Debug, Feature Dev, Quality, Docs |
| **Flags** | [FLAGS.md](FLAGS.md) | All flags, combinations, conflicts |  
| **Task Agents** | [AGENTS.md](AGENTS.md) | Complete catalog, quality framework |
| **Modes** | [MODE_CORE.md](MODE_CORE.md) | Brainstorming, Introspection, Token Efficiency |
| **Execution** | [MODE_EXECUTION.md](MODE_EXECUTION.md) | Task Management, Orchestration |
| **Rules** | [RULES.md](RULES.md) | Quality gates, behavioral rules, safety |

> **Quick Start**: [QUICKSTART.md](QUICKSTART.md) | **This Cheatsheet**: Quick lookups and cross-references