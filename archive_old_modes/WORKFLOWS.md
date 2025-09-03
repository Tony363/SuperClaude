# SuperClaude Framework Workflows

**Purpose**: Practical execution patterns for common development tasks using optimal tool combinations and quality-driven iterations.

## Core Workflow Pattern

**Standard Flow**: `git status` → Plan → TodoWrite → Execute → Quality(0-100) → Iterate(<70) → Validate → Clean

## Common Workflows

### 🔍 Debugging & Investigation

#### Debug Failed Test
```
--think → Task(root-cause-analyst) → Quality Check → Fix → Playwright(E2E) → --test
```

#### API Performance Issue
```
git status → --think-hard → Task(root-cause-analyst) → {
  Quality < 70? → Enhanced context → Re-execute
  Quality ≥ 70? → Task(performance-engineer) → Sequential → Implement
} → Validate
```

#### Unknown Codebase Issue  
```
git status → Task(general-purpose, "find X") → {
  Scope clear? → Task(root-cause-analyst)
  Still unclear? → --delegate-search
} → Fix → --test
```

### 🏗️ Feature Development

#### New Feature (Standard)
```
git checkout -b feature/X → Read(existing patterns) → {
  Scope clear? → --task-manage → TodoWrite → Implementation
  Vague scope? → --brainstorm → requirements clarification → proceed
} → --test → --review → PR
```

#### New Project Kickoff
```
--brainstorm → {discovery dialogue} → --task-manage → {
  write_memory("plan", goal)
  TodoWrite(phases)
  git checkout -b feature/init
} → Implementation → --test
```

#### UI Component Creation
```
--magic → /ui → Magic MCP → {component generation} → {
  Playwright(interactions) → Integration → --test
  Quality < 70? → Iterate with accessibility focus
}
```

### ⚡ Code Quality & Optimization

#### Refactoring Workflow
```
git status → Task(refactoring-expert, "analyze module X") → {
  Quality ≥ 70? → --delegate → MultiEdit → --test
  Quality < 70? → Enhanced context → Re-execute
} → --safe-mode → Validate
```

#### Performance Optimization
```
--think-hard → Task(performance-engineer) → Sequential → {
  Benchmark current → Identify bottlenecks → Implement fixes
} → Measure improvement → Quality(performance gains)
```

#### Multi-File Code Cleanup
```
Task(general-purpose, "find technical debt") → Task(refactoring-expert) → {
  Quality check → --delegate → Morphllm(bulk patterns) → MultiEdit
} → Task(quality-engineer, "verify changes") → --test
```

### 📋 Documentation & Analysis

#### API Documentation
```
Task(technical-writer, "document endpoints") → {
  Quality < 70? → Deepwiki(patterns) → Enhanced context → Re-execute
  Quality ≥ 70? → Generate OpenAPI spec
} → Validate completeness
```

#### Architecture Analysis
```
--ultrathink → Task(system-architect, "analyze system") → {
  Sequential(structured analysis) → Deepwiki(patterns) → 
  Task(requirements-analyst, "scope improvements")
} → Document decisions
```

## Specialized Workflows

### 🔒 Security & Compliance

#### Security Audit
```
Task(security-engineer, "audit auth flow") → {
  Quality check → OWASP compliance → Vulnerability assessment
} → Fix critical → Validate
```

### 🧪 Testing & Quality

#### Test Coverage Analysis  
```
Task(quality-engineer, "assess coverage") → {
  Identify gaps → Playwright(E2E scenarios) → Unit test generation
} → --test → Coverage report
```

#### Cross-Browser Testing
```
Playwright → {multi-browser test suite} → Accessibility validation → 
Performance testing → Report
```

### 📦 Deployment & DevOps

#### CI/CD Optimization
```
Task(devops-architect, "optimize pipeline") → {
  Analysis → Bottleneck identification → Implementation
} → Measure improvement → Validate
```

## Multi-Agent Workflows

### Complex Feature Implementation
```
1. Task(requirements-analyst) → PRD breakdown → Quality check
2. Task(system-architect) → Design → write_memory("design_decisions")  
3. Task(backend-architect) → API design → Task(frontend-architect) → UI design
4. Implementation phases with quality gates
5. Task(quality-engineer) → Comprehensive testing
```

### Legacy System Modernization
```
1. Task(general-purpose, "analyze legacy system") → Assessment
2. Task(system-architect, "design migration") → Strategy  
3. Task(refactoring-expert, "incremental improvements") → Quality loops
4. Task(security-engineer, "audit changes") → Validation
5. Task(devops-architect, "deployment strategy") → Implementation
```

### Learning & Knowledge Transfer
```
Task(socratic-mentor, "explain concept X") → {
  Interactive teaching → Concept validation → 
  Task(learning-guide, "create tutorial") → Quality iteration
}
```

## Quality-Driven Iterations

### Automatic Quality Loop
```
Execute Task → Quality(0-100) → {
  Score ≥ 90: ✅ Accept (production-ready)
  Score 70-89: ⚠️ Accept with notes  
  Score 50-69: 🔄 Auto-iterate with feedback
  Score < 50: ❌ Reject & redesign
}
```

### Context Enhancement Pattern
```
Iteration 1: Base context → Output → Quality evaluation
Iteration 2: Base + specific feedback + failed attempts → Output  
Iteration 3: Base + cumulative feedback + successful patterns → Final output
```

### Multi-Agent Quality Handoff
```
Agent 1 → Output(Q=65) → Agent 2(enhanced context) → Output(Q=85) → Accept
```

## Decision Trees

### Task Agent Selection
```
Need analysis? → {
  Scope unknown? → general-purpose
  Debugging? → root-cause-analyst  
  Code quality? → refactoring-expert
  Architecture? → system-architect
  Documentation? → technical-writer
  Performance? → performance-engineer
}
```

### MCP Server Selection
```
Task type? → {
  UI work? → Magic MCP
  Bulk edits? → Morphllm MCP  
  Complex analysis? → Sequential MCP
  Memory operations? → Serena MCP
  Browser testing? → Playwright MCP
  Documentation? → Deepwiki MCP
}
```

### Flag Combination Decision
```
Complexity? → {
  Simple: --think
  Moderate: --think-hard  
  Complex: --ultrathink
  
  + Multi-file? → --task-manage
  + Context >75%? → --uc
  + Production? → --safe-mode
  + Unknown scope? → --brainstorm
}
```

## Session Management Workflows

### Session Start Pattern
```
list_memories() → {
  Existing work? → read_memory("current_plan") → Resume
  Fresh start? → git status → Plan new work
} → think_about_collected_information()
```

### Checkpoint Pattern (Every 30min)
```
write_memory("checkpoint", current_state) → 
write_memory("quality_scores", task_evaluations) →
TodoWrite(update progress)
```

### Session End Pattern  
```
think_about_whether_you_are_done() → {
  Complete? → write_memory("session_summary", outcomes) → Clean workspace
  Incomplete? → write_memory("next_actions", todo_list) → Preserve state
} → delete_memory(temp_items)
```

## Error Recovery Workflows

### Tool Failure Recovery
```
Tool fails → --introspect → {
  Root cause analysis → Alternative tool selection →
  Context preservation → Re-execute → Quality check
}
```

### Quality Failure Recovery
```
Quality < 70 → {
  Wrong agent? → Switch agent type
  Missing context? → Enhanced context package  
  Unclear requirements? → Task(requirements-analyst)
  Too complex? → Break into subtasks
}
```

### Context Loss Recovery
```
Context unclear → {
  list_memories() → read_memory(relevant_keys) →
  think_about_collected_information() → Reconstruct context →
  Continue with enhanced understanding
}
```

## Optimization Patterns

### Parallel Execution
```
Independent operations → {
  Read(file1, file2, file3) in parallel →
  Analysis → Edit(file1, file2, file3) in parallel
} → Validate
```

### Resource-Conscious Workflow  
```
Context >75%? → --uc → {
  Symbol communication → Table format → 
  Compressed explanations → Essential operations only
}
```

### Batch Operations
```
>3 similar edits → MultiEdit → >5 files → Task(agent) → 
>7 directories → --delegate
```