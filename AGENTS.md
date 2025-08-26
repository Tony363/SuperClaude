# SuperClaude Task Agent Framework

**Purpose**: Comprehensive guide for Task agent selection, quality evaluation, and agentic loop implementation

## Core Principles

### Quality-First Execution
- **You MUST** evaluate all Task outputs with quality scoring (0-100)
- **You MUST** iterate automatically when quality < 70
- **You MUST** maintain context consistency across iterations
- **IMPORTANT**: Never accept suboptimal results without explicit override

### Context Preservation
Every Task delegation includes a structured context package:
```yaml
context:
  goal: "High-level objective"
  constraints: ["resource limits", "performance requirements"]
  prior_work: {"agent_1": "output", "agent_2": "results"}
  dependencies: ["related files", "modules"]
  quality_criteria: {"min_score": 70, "required": [...]}
  iteration_history: ["attempt_1", "feedback_1", ...]
```

## Agent Catalog

### 🔍 Discovery & Analysis

#### general-purpose
**When to Use**: Unknown scope, exploratory searches, complex multi-step tasks
**Quality Factors**: Comprehensiveness, relevance, actionability
```
Example: "Find all authentication implementations across the codebase"
Context: {goal: "map auth patterns", constraints: ["focus on JWT"]}
Quality Check: Did it find ALL implementations? Score accordingly.
```

#### root-cause-analyst
**When to Use**: Debugging, error investigation, performance bottlenecks
**Quality Factors**: Root cause identification, evidence quality, fix viability
```
Example: "Why is the API returning 500 errors?"
Context: {goal: "identify failure point", prior_work: {logs: "..."}}
Quality Check: Is the root cause clearly identified? Are fixes proposed?
```

### 🛠️ Code Quality & Improvement

#### refactoring-expert
**When to Use**: Technical debt reduction, code cleanup, pattern improvements
**Quality Factors**: Code cleanliness, maintainability improvement, test preservation
```
Example: "Refactor authentication module for better maintainability"
Context: {goal: "reduce complexity", constraints: ["preserve API"]}
Quality Check: Complexity metrics improved? Tests still pass?
```

#### quality-engineer
**When to Use**: Test coverage, edge case detection, quality assessment
**Quality Factors**: Coverage completeness, edge case identification, test quality
```
Example: "Assess test coverage and identify gaps"
Context: {goal: "achieve 90% coverage", dependencies: ["test framework"]}
Quality Check: Are all critical paths covered? Edge cases identified?
```

#### performance-engineer
**When to Use**: Optimization, bottleneck identification, efficiency improvements
**Quality Factors**: Performance gains, measurement accuracy, optimization safety
```
Example: "Optimize database query performance"
Context: {goal: "reduce latency 50%", constraints: ["no schema changes"]}
Quality Check: Measurable improvement? No functionality broken?
```

### 📚 Documentation & Planning

#### technical-writer
**When to Use**: API documentation, user guides, comprehensive docs
**Quality Factors**: Clarity, completeness, accuracy, examples
```
Example: "Document all REST API endpoints"
Context: {goal: "OpenAPI spec", dependencies: ["existing routes"]}
Quality Check: All endpoints documented? Examples provided?
```

#### requirements-analyst
**When to Use**: Feature analysis, PRD breakdown, scope definition
**Quality Factors**: Requirement clarity, feasibility, completeness
```
Example: "Analyze requirements for payment system"
Context: {goal: "implementation plan", constraints: ["PCI compliance"]}
Quality Check: All requirements captured? Dependencies identified?
```

#### learning-guide
**When to Use**: Tutorial creation, educational content, concept explanation
**Quality Factors**: Pedagogical clarity, progression logic, example quality
```
Example: "Create tutorial for new developers"
Context: {goal: "onboarding guide", constraints: ["beginner-friendly"]}
Quality Check: Clear progression? Hands-on examples?
```

### 🏗️ Architecture & Design

#### system-architect
**When to Use**: System design, scalability planning, architecture decisions
**Quality Factors**: Scalability, maintainability, design pattern adherence
```
Example: "Design microservices architecture"
Context: {goal: "scalable system", constraints: ["AWS deployment"]}
Quality Check: Scalability addressed? Clear service boundaries?
```

#### backend-architect
**When to Use**: API design, database architecture, server patterns
**Quality Factors**: API consistency, data integrity, security
```
Example: "Design REST API structure"
Context: {goal: "RESTful API", constraints: ["backwards compatible"]}
Quality Check: RESTful principles? Consistent patterns?
```

#### frontend-architect
**When to Use**: UI/UX implementation, component architecture, accessibility
**Quality Factors**: Component reusability, accessibility compliance, performance
```
Example: "Design component architecture"
Context: {goal: "reusable components", constraints: ["WCAG 2.1"]}
Quality Check: Components reusable? Accessibility standards met?
```

### 🔒 Specialized Operations

#### security-engineer
**When to Use**: Security audits, vulnerability assessment, compliance
**Quality Factors**: Vulnerability coverage, severity accuracy, remediation quality
```
Example: "Audit authentication security"
Context: {goal: "OWASP compliance", dependencies: ["auth module"]}
Quality Check: All OWASP items checked? Fixes provided?
```

#### devops-architect
**When to Use**: Infrastructure planning, CI/CD optimization, deployment
**Quality Factors**: Pipeline efficiency, deployment safety, monitoring coverage
```
Example: "Optimize CI/CD pipeline"
Context: {goal: "reduce build time 50%", constraints: ["maintain quality"]}
Quality Check: Build time improved? Quality gates maintained?
```

#### socratic-mentor
**When to Use**: Teaching through questions, concept exploration, learning
**Quality Factors**: Question quality, learning progression, concept clarity
```
Example: "Explain algorithm through guided discovery"
Context: {goal: "teach sorting", constraints: ["interactive learning"]}
Quality Check: Concepts understood? Progression logical?
```

## Quality Evaluation Framework

### Scoring Dimensions
```python
def evaluate_quality(output):
    scores = {
        'correctness': score_correctness(output),      # 40%
        'completeness': score_completeness(output),    # 30%
        'code_quality': score_code_quality(output),    # 20%
        'performance': score_performance(output)       # 10%
    }
    
    total = sum(scores[k] * weights[k] for k in scores)
    
    return {
        'score': total,
        'breakdown': scores,
        'action': determine_action(total)
    }
```

### Action Thresholds
| Score | Action | Description |
|-------|--------|-------------|
| 90-100 | ✅ Accept | Production-ready, exceeds requirements |
| 70-89 | ⚠️ Accept with Notes | Acceptable, minor improvements noted |
| 50-69 | 🔄 Auto-Iterate | Must improve, automatic re-execution |
| 0-49 | ❌ Reject & Redesign | Fundamental issues, needs new approach |

## Agentic Loop Implementation

### Standard Loop Pattern
```
1. Initial Delegation
   → Task(agent, context, requirements)
   
2. Quality Evaluation
   → score = evaluate_quality(output)
   
3. Decision Point
   if score >= 70:
       → Accept and continue
   elif iterations < max_iterations:
       → Generate feedback
       → Enhance context
       → Re-delegate (same or different agent)
   else:
       → Present best result with limitations
```

### Feedback Generation
```python
def generate_feedback(output, quality_score):
    return {
        'score': quality_score,
        'issues': identify_specific_issues(output),
        'improvements': suggest_improvements(output),
        'priority': rank_by_impact(issues),
        'context_updates': enhance_context(issues)
    }
```

### Context Evolution
Each iteration enhances context:
```
Iteration 1: Base context
Iteration 2: Base + specific feedback + failed attempts
Iteration 3: Base + cumulative feedback + successful patterns
```

## Selection Decision Trees

### Primary Decision Flow
```
Need Task agent?
├─ Scope unknown? → general-purpose
├─ Debugging? → root-cause-analyst
├─ Refactoring? → refactoring-expert
├─ Documentation? → technical-writer
├─ Architecture? → system-architect
├─ Security? → security-engineer
├─ Performance? → performance-engineer
├─ UI/UX? → frontend-architect
├─ Backend? → backend-architect
├─ Teaching? → socratic-mentor
└─ Planning? → requirements-analyst
```

### Quality-Driven Re-selection
```
Quality < 70?
├─ Wrong agent type? → Switch agent
├─ Missing context? → Enhance context
├─ Unclear requirements? → requirements-analyst first
├─ Technical complexity? → Break into subtasks
└─ Resource constraints? → Adjust expectations
```

## Integration with SuperClaude

### Flag Interactions
- `--loop`: Enables automatic quality-driven iteration
- `--iterations [n]`: Sets maximum iteration count (default: 3)
- `--quality [n]`: Sets minimum quality threshold (default: 70)
- `--delegate`: Activates Task agent for appropriate operations

### Mode Synergy
- **Brainstorming Mode**: Use requirements-analyst for discovery
- **Task Management Mode**: Track quality scores in memory
- **Introspection Mode**: Analyze quality evaluation patterns
- **Token Efficiency Mode**: Compress context between iterations

### Memory Integration
```yaml
# Quality tracking in Serena memory
write_memory("quality_task_1", {
  "initial_score": 45,
  "final_score": 85,
  "iterations": 2,
  "feedback_applied": ["clarity", "completeness"],
  "agent_sequence": ["general-purpose", "refactoring-expert"]
})
```

## Best Practices

### DO
- ✅ Always evaluate Task output quality
- ✅ Iterate when quality < 70
- ✅ Preserve context across iterations
- ✅ Select agents based on specific expertise
- ✅ Track quality metrics in memory

### DON'T
- ❌ Accept low-quality outputs without iteration
- ❌ Lose context between agent delegations
- ❌ Use general-purpose when specialist exists
- ❌ Exceed iteration limits without user consent
- ❌ Ignore quality feedback in subsequent attempts

## Example Workflows

### Complex Debugging with Quality Loop
```
1. User: "API is slow and failing intermittently"

2. Task(root-cause-analyst, {goal: "identify issues"})
   → Output: Generic analysis
   → Quality: 55/100 (incomplete)

3. Auto-iterate with feedback:
   → Enhanced context: {specific_endpoints, error_logs}
   → Task(root-cause-analyst, enhanced_context)
   → Output: Found N+1 queries and race condition
   → Quality: 88/100 ✅

4. Task(performance-engineer, {goal: "fix N+1"})
   → Output: Optimized queries
   → Quality: 92/100 ✅
```

### Multi-Agent Refactoring
```
1. Task(general-purpose, {goal: "find technical debt"})
   → Quality: 75/100 ✅

2. Task(refactoring-expert, {goal: "refactor auth module"})
   → Quality: 65/100 🔄
   → Auto-iterate: "preserve tests"
   → Quality: 85/100 ✅

3. Task(quality-engineer, {goal: "verify refactoring"})
   → Quality: 90/100 ✅
```

## Metrics & Monitoring

Track these metrics for continuous improvement:
- Average quality scores by agent type
- Iteration success rates
- Context preservation effectiveness
- Time-to-acceptable-quality
- Agent selection accuracy

Use these insights to refine agent selection and context strategies over time.