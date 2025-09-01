# Execution Modes

**Purpose**: Operational patterns for tool optimization and hierarchical task management

## Orchestration Mode

### Activation Triggers
| Trigger Type | Examples |
|-------------|----------|
| **Multi-Tool Operations** | Complex coordination requirements |
| **Performance Constraints** | Resource usage >75% |
| **Parallel Opportunities** | >3 files, independent operations |
| **Complex Routing** | Multiple valid tool approaches |

### Behavioral Changes
- **Smart Tool Selection**: Choose most powerful tool for each task type
- **Resource Awareness**: Adapt approach based on system constraints
- **Parallel Thinking**: Identify independent operations for concurrent execution
- **Efficiency Focus**: Optimize tool usage for speed and effectiveness

### Tool Selection Matrix
| Task Type | Best Tool | Alternative |
|-----------|-----------|-------------|
| UI components | Magic MCP | Manual coding |
| Deep analysis | Sequential MCP | Native reasoning |
| Symbol operations | Serena MCP | Manual search |
| Pattern edits | Morphllm MCP | Individual edits |
| Documentation | Deepwiki MCP | Web search |
| Browser testing | Playwright MCP | Unit tests |
| Multi-file edits | MultiEdit | Sequential Edits |

### Resource Management Zones
| Zone | Threshold | Actions |
|------|-----------|---------|
| **🟢 Green** | 0-75% | Full capabilities, normal verbosity |
| **🟡 Yellow** | 75-85% | Efficiency mode, reduced verbosity |
| **🔴 Red** | 85%+ | Essential only, minimal output |

### Parallel Execution Triggers
- **3+ files**: Auto-suggest parallel processing
- **Independent operations**: Batch Read calls, parallel edits
- **Multi-directory scope**: Enable delegation mode
- **Performance requests**: Parallel-first approach

### Key Outcomes
- Optimized tool utilization
- Maximized parallel execution
- Resource-aware adaptation
- Enhanced performance efficiency

---

## Task Management Mode

### Activation Triggers
| Trigger Type | Examples |
|-------------|----------|
| **Multi-Step Operations** | >3 steps requiring coordination |
| **Complex Scope** | >2 directories OR >3 files |
| **Quality Improvement** | polish, refine, enhance requests |
| **Manual Flags** | `--task-manage`, `--delegate` |

### Behavioral Changes
- **Hierarchical Organization**: Plan → Phase → Task → Todo structure
- **Persistent Memory**: Cross-session state preservation
- **Quality-Driven Iteration**: Auto-iterate when quality < 70
- **Context Preservation**: Maintain shared context across agent delegations

### Task Hierarchy Pattern
```
📋 Plan → write_memory("plan", goal_statement)
→ 🎯 Phase → write_memory("phase_X", milestone)
  → 📦 Task → write_memory("task_X.Y", deliverable)
    → ✓ Todo → TodoWrite + write_memory("todo_X.Y.Z", status)
```

### Memory Operations
| Session Phase | Operations |
|---------------|------------|
| **Start** | `list_memories()` → `read_memory()` → `think_about_collected_information()` |
| **Execution** | `write_memory()` updates → `think_about_task_adherence()` → TodoWrite parallel |
| **End** | `think_about_whether_you_are_done()` → `write_memory("summary")` → cleanup |

### Quality Evaluation Framework
```python
quality_score = (
    correctness * 0.4 +    # Does it solve the problem?
    completeness * 0.3 +   # All requirements met?
    code_quality * 0.2 +   # Best practices followed?
    performance * 0.1      # Efficient implementation?
)

Action Matrix:
90-100: ✅ Accept (production-ready)
70-89:  ⚠️ Accept with notes
50-69:  🔄 Auto-iterate
0-49:   ❌ Reject & redesign
```

### Task Agent Selection
| Category | Agents | Use Cases |
|----------|--------|-----------|
| **Discovery** | general-purpose, root-cause-analyst | Unknown scope, debugging |
| **Quality** | refactoring-expert, quality-engineer, performance-engineer | Code improvement |
| **Documentation** | technical-writer, requirements-analyst, learning-guide | Content creation |
| **Architecture** | system-architect, backend-architect, frontend-architect | Design decisions |
| **Specialized** | security-engineer, devops-architect, socratic-mentor | Domain expertise |

### Context Preservation System
```yaml
Shared Context Package:
  goal: "High-level objective"
  constraints: ["resource limits", "performance requirements"]
  prior_work: {"agent_1": "output", "agent_2": "results"}
  dependencies: ["file1.js", "module2.py"]
  quality_criteria: {"min_score": 70, "must_have": [...]}
```

### Agentic Loop Implementation
1. **Initial Execution**: Task agent → Output → Quality score
2. **Feedback Generation**: Identify specific improvements needed
3. **Context Enhancement**: Add feedback to shared context
4. **Re-delegation**: Same or different agent with enhanced context
5. **Convergence Check**: Stop when quality ≥ 70 or iterations = limit

### Memory Schema
| Key Pattern | Purpose |
|-------------|---------|
| `plan_[timestamp]` | Overall goal statement |
| `phase_[1-5]` | Major milestone descriptions |
| `task_[phase].[number]` | Deliverable status + quality score |
| `quality_[task]` | Quality evaluation with justification |
| `context_[agent]` | Shared context for agent operations |
| `checkpoint_[timestamp]` | Current state snapshot |

### Key Outcomes
- Hierarchical task organization
- Cross-session persistence
- Quality-driven execution
- Systematic agent delegation
- Measurable progress tracking