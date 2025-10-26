# SuperClaude Framework Core - Optimized for Performance

This is the essential core configuration optimized to stay under the 40KB threshold.
Extended functionality is available on-demand through CLAUDE_EXTENDED.md.

## 🚀 Essential Components (Always Loaded)

### Quick Navigation & Help
@QUICKSTART.md     # Getting started guide (5.8KB)
@CHEATSHEET.md     # Quick reference lookup (6.6KB)

### Core Framework
@FLAGS.md          # All behavioral flags (4.8KB)
@PRINCIPLES.md     # Engineering philosophy (2.6KB)
@RULES_CRITICAL.md # Critical & Important rules only (7KB)

## 📦 On-Demand Components (Load When Needed)

The following components load automatically when their triggers are detected:

### Task Management & Agents
- **Trigger**: `--delegate`, `Task()` commands
- **Loads**: @AGENTS.md (11.5KB)

### Complex Workflows
- **Trigger**: Multi-step operations, `--task-manage`
- **Loads**: @WORKFLOWS.md (8KB)

### Behavioral Modes
- **Trigger**: Mode flags like `--brainstorm`, `--introspect`
- **Loads**: Relevant MODE_*.md files

### MCP Servers
- **Trigger**: MCP usage like Fetch, Filesystem, Sequential, Zen
- **Loads**: Relevant MCP_*.md documentation

## 💡 Quick Commands

Essential flags for common tasks:
- `--brainstorm` → Interactive discovery mode
- `--delegate` → Auto-select best agent
- `--loop` → Quality-driven iteration
- `--think` → Structured analysis
- `--uc` → Ultra-compressed output

For extended features, components load automatically when needed.
Full documentation available in @CLAUDE_EXTENDED.md when required.

---
*SuperClaude Core v4.0.8 - Optimized for Performance*
*Total size: ~27KB (67% reduction from original)*
