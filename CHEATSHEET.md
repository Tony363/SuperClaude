# SuperClaude Framework Cheatsheet

## 🚀 Quick Decision Guide
| I want to... | Use this |
|-------------|----------|
| Explore ideas | `--brainstorm` |
| Debug issues | `--think` → Task (root-cause-analyst) |
| Optimize performance | `--think` + `--focus performance` |
| Build UI components | `--magic` or `/ui` |
| Refactor code | Task (refactoring-expert) |
| Generate docs | Task (technical-writer) |
| Run tests | `--test` after changes |
| Save tokens | `--uc` or `--token-efficient` |

## 🎯 Flags Reference
| Flag | Trigger | Purpose |
|------|---------|---------|
| `--brainstorm` | Vague requests, "maybe", "thinking about" | Interactive discovery |
| `--introspect` | Self-analysis, error recovery | Meta-cognitive analysis |
| `--task-manage` | >3 steps OR >2 directories | Hierarchical organization |
| `--orchestrate` | Multi-tool operations | Optimal tool routing |
| `--token-efficient` | Context >75% | Compressed communication |
| `--think` | Moderate complexity | ~4K token analysis |
| `--think-hard` | System-wide analysis | ~10K token analysis |
| `--ultrathink` | Critical redesign | ~32K token analysis |
| `--delegate` | >7 directories OR >50 files | Sub-agent processing |
| `--safe-mode` | Production, critical ops | Maximum validation |
| `--test` | After code changes | Run test suites |
| `--review` | Before commits | Code review mode |

## 🔄 Behavioral Modes
| Mode | Activation Keywords | Primary Use |
|------|-------------------|-------------|
| **Brainstorming** | explore, discuss, figure out | Requirements discovery |
| **Introspection** | analyze reasoning, reflect | Self-examination |
| **Orchestration** | Performance constraints | Tool optimization |
| **Task Management** | Complex operations | Progress tracking |
| **Token Efficiency** | Resource limits | Compressed output |

## 🛠️ MCP Servers
| Server | Best For | Don't Use For |
|--------|----------|---------------|
| **Deepwiki** | Framework docs, API patterns | Simple explanations |
| **Magic** | UI components, design systems | Backend logic |
| **Morphllm** | Bulk edits, pattern replacement | Symbol operations |
| **Playwright** | Browser testing, E2E | Static analysis |
| **Sequential** | Complex analysis, debugging | Simple tasks |
| **Serena** | Symbol ops, project memory | Pattern edits |

## 📋 Task Agents
| Agent | Use When |
|-------|----------|
| `general-purpose` | Unknown scope, exploration |
| `root-cause-analyst` | Debugging, investigations |
| `refactoring-expert` | Code improvements |
| `technical-writer` | Documentation |
| `quality-engineer` | Test coverage |
| `system-architect` | Design decisions |
| `performance-engineer` | Optimization |

## ⚡ Common Workflows

### Debug Failed Test
```bash
--think → Task (root-cause-analyst) → Playwright → Fix → --test
```

### Implement Feature
```bash
--brainstorm → --task-manage → TodoWrite → Implementation → --test → --review
```

### Optimize Performance
```bash
--think-hard → Task (performance-engineer) → Sequential → Implement → Validate
```

### UI Component
```bash
--magic → /ui → Magic MCP → Playwright (test) → Integration
```

## 🔴 Priority Rules
1. **Safety First**: Never compromise security
2. **Complete Features**: No partial implementations
3. **Build Only Asked**: No scope creep
4. **Evidence-Based**: Verify all claims
5. **Clean Workspace**: Remove temp files

## 💡 Quick Tips
- Use `--delegate-search` for unknown file locations
- Combine `--think` + `--sequential` for deep analysis
- Always `git status` before starting work
- Run lint/typecheck before marking complete
- Use Task agents for >5 file operations

## 🔗 Flag Combinations
| Compatible | Effect |
|------------|--------|
| `--think` + `--sequential` | Deep structured analysis |
| `--task-manage` + `--uc` | Efficient task tracking |
| `--safe-mode` + `--validate` | Maximum safety checks |
| `--delegate` + specific agents | Targeted delegation |

## ⚠️ Conflicts
- `--no-mcp` overrides all MCP flags
- `--safe-mode` overrides optimization flags
- Cannot use multiple `--think` levels simultaneously