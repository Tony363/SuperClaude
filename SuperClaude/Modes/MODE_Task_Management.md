# Task Management Mode

**Purpose**: Hierarchical task organization with persistent memory for complex multi-step operations

## Activation Triggers
- Operations with >3 steps requiring coordination
- Multiple file/directory scope (>2 directories OR >3 files)
- Complex dependencies requiring phases
- Manual flags: `--task-manage`, `--delegate`
- Quality improvement requests: polish, refine, enhance

## Works With Other Modes
- **Token Efficiency**: Compress task descriptions when context is high
- **Orchestration**: Optimize tool selection for each task
- **Introspection**: Reflect on task completion and lessons learned

## Common Tools
- **TodoWrite**: Core tool for task tracking
- **Task agents**: Delegation for complex subtasks
- **UnifiedStore (write_memory)**: Persist task state across sessions

## Task Hierarchy with Memory

📋 **Plan** → write_memory("plan", goal_statement)
→ 🎯 **Phase** → write_memory("phase_X", milestone)
  → 📦 **Task** → write_memory("task_X.Y", deliverable)
    → ✓ **Todo** → TodoWrite + write_memory("todo_X.Y.Z", status)

## Memory Operations

### Session Start
```
1. list_memories() → Show existing task state via UnifiedStore
2. read_memory("current_plan") → Resume context
3. think_about_collected_information() → Understand where we left off
```

### During Execution
```
1. write_memory("task_2.1", "completed: auth middleware")
2. think_about_task_adherence() → Verify on track
3. Update TodoWrite status in parallel
4. write_memory("checkpoint", current_state) every 30min
```

### Session End
```
1. think_about_whether_you_are_done() → Assess completion
2. write_memory("session_summary", outcomes)
3. delete_memory() for completed temporary items
```

## Execution Pattern

1. **Load**: list_memories() → read_memory() → Resume state
2. **Plan**: Create hierarchy → write_memory() for each level  
3. **Track**: TodoWrite + memory updates in parallel
4. **Execute**: Update memories as tasks complete
5. **Evaluate**: Quality assessment (0-100) → Decide iteration
6. **Iterate**: If quality < 70 → Re-execute with feedback
7. **Checkpoint**: Periodic write_memory() for state preservation
8. **Complete**: Final memory update with outcomes + quality score

## Tool Selection

| Task Type | Primary Tool | Memory Key |
|-----------|-------------|------------|
| Analysis | Sequential MCP | "analysis_results" |
| Implementation | MultiEdit | "code_changes" |
| UI Components | Deepwiki MCP | "ui_components" |
| Testing | External Playwright/Cypress | "test_results" |
| Documentation | Deepwiki MCP | "doc_patterns" |

## Quality-Driven Agent Selection

### Quality Evaluation Protocol
**You MUST** evaluate all Task agent outputs using this framework:

```python
quality_score = (
    correctness * 0.4 +    # Does it solve the problem?
    completeness * 0.3 +   # All requirements met?
    code_quality * 0.2 +   # Best practices followed?
    performance * 0.1      # Efficient implementation?
)

if quality_score < 70:
    iterate_with_feedback()
elif quality_score < 90:
    accept_with_improvements()
else:
    accept_as_production_ready()
```

### Context Preservation System
**You MUST** maintain context across agent delegations:

```yaml
Shared Context Package:
  goal: "High-level objective"
  constraints: ["memory limits", "performance requirements"]
  prior_work: {"agent_1": "output", "agent_2": "results"}
  dependencies: ["file1.js", "module2.py"]
  quality_criteria: {"min_score": 70, "must_have": [...]}
```

### Agentic Loop Implementation
When using `--loop` or quality < 70:

1. **Initial Execution**: Task agent → Output → Quality score
2. **Feedback Generation**: Identify specific improvements needed
3. **Context Enhancement**: Add feedback to shared context
4. **Re-delegation**: Same or different agent with enhanced context
5. **Convergence Check**: Stop when quality ≥ 70 or iterations = limit

### Task Agent Selection

### Exploration & Discovery
- **general-purpose**: Broad searches across codebase, unknown scope investigations
- **root-cause-analyst**: Systematic debugging, issue investigation, error analysis

### Code Quality & Improvement
- **refactoring-expert**: Systematic code improvements, technical debt reduction
- **quality-engineer**: Test coverage assessment, edge case detection, quality metrics
- **performance-engineer**: Optimization opportunities, bottleneck identification

### Documentation & Planning  
- **technical-writer**: Comprehensive documentation tasks, API docs, user guides
- **requirements-analyst**: Feature analysis, PRD breakdown, requirement scoping
- **learning-guide**: Tutorial creation, educational content, concept explanation

### Architecture & Design
- **system-architect**: System design, scalability planning, architecture decisions
- **backend-architect**: API design, database architecture, server-side patterns
- **frontend-architect**: UI/UX implementation, component architecture, accessibility

### Specialized Operations
- **security-engineer**: Security audits, vulnerability assessment, compliance checks
- **devops-architect**: Infrastructure planning, CI/CD optimization, deployment strategies
- **socratic-mentor**: Teaching through questions, concept exploration, learning facilitation

## Memory Schema

```
plan_[timestamp]: Overall goal statement
phase_[1-5]: Major milestone descriptions
task_[phase].[number]: Specific deliverable status + quality score
todo_[task].[number]: Atomic action completion
quality_[task]: Quality evaluation (0-100) with justification
iteration_[task].[n]: Iteration history with improvements
context_[agent]: Shared context for agent operations
checkpoint_[timestamp]: Current state snapshot
blockers: Active impediments requiring attention
decisions: Key architectural/design choices made
```

## Examples

### Session 1: Start Authentication Task with Quality Control
```
list_memories() → Empty
write_memory("plan_auth", "Implement JWT authentication system")
write_memory("phase_1", "Analysis - security requirements review")
write_memory("task_1.1", "pending: Review existing auth patterns")
write_memory("context_analyst", {goal: "Find auth patterns", constraints: [...]})
TodoWrite: Create 5 specific todos
Execute task 1.1 → Quality: 65/100 → Auto-iterate
write_memory("iteration_1.1.1", "Added security considerations")
Re-execute → Quality: 85/100 → Accept
write_memory("task_1.1", "completed: Found 3 patterns, quality: 85/100")
write_memory("quality_1.1", "Score: 85, Justification: Comprehensive pattern analysis")
```

### Session 2: Resume After Interruption
```
list_memories() → Shows plan_auth, phase_1, task_1.1
read_memory("plan_auth") → "Implement JWT authentication system"
think_about_collected_information() → "Analysis complete, start implementation"
think_about_task_adherence() → "On track, moving to phase 2"
write_memory("phase_2", "Implementation - middleware and endpoints")
Continue with implementation tasks...
```

### Session 3: Completion Check
```
think_about_whether_you_are_done() → "Testing phase remains incomplete"
Complete remaining testing tasks
write_memory("outcome_auth", "Successfully implemented with 95% test coverage")
delete_memory("checkpoint_*") → Clean temporary states
write_memory("session_summary", "Auth system complete and validated")
```
