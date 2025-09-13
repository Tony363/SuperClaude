# SuperClaude Framework Extended - Conditional Components

This file contains the full SuperClaude framework components that load on-demand.
These components are triggered automatically when their specific features are needed.

## 📚 Full Framework Components

### Behavioral Modes
These load automatically when their flags are detected:

@MODE_Brainstorming.md    # Activated by: --brainstorm, exploration keywords
@MODE_Introspection.md    # Activated by: --introspect, self-analysis needs
@MODE_Orchestration.md    # Activated by: --orchestrate, multi-tool operations
@MODE_Task_Management.md  # Activated by: --task-manage, complex operations
@MODE_Token_Efficiency.md # Activated by: --uc, context >75%
@MODE_CORE.md            # Reference for all cognitive patterns
@MODE_EXECUTION.md       # Reference for all operational patterns

### Task Management & Agents
Loads when delegation or task management is needed:

@AGENTS.md               # Activated by: --delegate, Task() commands
@WORKFLOWS.md            # Activated by: complex multi-step operations

### MCP Server Documentation
Loads when specific MCP servers are used:

@MCP_Fetch.md           # Activated by: web content retrieval, URL fetching
@MCP_Filesystem.md      # Activated by: file operations, directory management
@MCP_Playwright.md      # Activated by: browser testing, E2E scenarios
@MCP_Sequential.md      # Activated by: --think flags, complex analysis
@MCP_Serena.md          # Activated by: symbol operations, project memory

### Extended Rules & Operations
Additional guidelines and frameworks:

@RULES_RECOMMENDED.md    # Best practices and optimization guidelines
@OPERATIONS.md          # Extended quality framework (if exists)

### Legacy & Reference Components
Historical or reference documentation:

@AGENTS_EXTENDED.md     # 100+ specialized agents (load when needed)
@MCP_Task.md           # Task agent detailed documentation

## 🔄 Dynamic Loading Triggers

The framework intelligently loads components based on these triggers:

### Mode Activation
- `--brainstorm` → Loads MODE_Brainstorming.md
- `--introspect` → Loads MODE_Introspection.md  
- `--task-manage` → Loads MODE_Task_Management.md + WORKFLOWS.md
- `--orchestrate` → Loads MODE_Orchestration.md
- `--uc` or context >75% → Loads MODE_Token_Efficiency.md

### Task & Agent Usage
- `Task()` command → Loads AGENTS.md
- `--delegate` flag → Loads AGENTS.md
- Complex workflows → Loads WORKFLOWS.md

### MCP Server Usage
- Web content retrieval → Loads MCP_Fetch.md
- File operations → Loads MCP_Filesystem.md
- Browser testing → Loads MCP_Playwright.md
- Deep analysis → Loads MCP_Sequential.md
- Symbol operations → Loads MCP_Serena.md

### Quality & Optimization
- Performance issues → Loads RULES_RECOMMENDED.md
- Quality concerns → Loads full RULES.md
- Extended agents → Loads AGENTS_EXTENDED.md on request

## 📊 Memory Impact

| Component | Size | Load Trigger | Impact |
|-----------|------|--------------|--------|
| MODE_*.md files | ~20KB | Mode flags | Behavioral changes |
| AGENTS.md | 11.5KB | Delegation | Agent selection |
| WORKFLOWS.md | 8KB | Complex tasks | Execution patterns |
| MCP_*.md files | ~10KB | MCP usage | Tool documentation |
| AGENTS_EXTENDED.md | ~15KB | On request | 100+ agents |

## 🚀 Usage Notes

1. **Automatic Loading**: Components load automatically when their triggers are detected
2. **No Manual Import**: You don't need to explicitly request these files
3. **Context Efficient**: Only loads what's needed for the current task
4. **Full Access**: All components remain available when specifically needed

## 🔗 Component Dependencies

Some components work best together:
- Task Management + Agents + Workflows
- All Mode files for comprehensive behavioral adaptation
- MCP documentation when using multiple servers
- Critical + Recommended rules for complete guidelines

---
*SuperClaude Extended v4.0.8 - Conditional Loading System*
*Components load automatically based on usage patterns*