# Task Tool Integration

**Purpose**: Intelligent delegation engine for complex multi-step operations with specialized agent routing

## Triggers
- Operations with unknown scope or exploration needs
- Complex searches spanning multiple directories or files
- Systematic debugging and root cause analysis
- Multi-file refactoring and code improvements
- Documentation generation across components
- Any operation where full scope isn't clear initially

## Choose When
- **Over direct search**: When scope is unknown or spans >3 directories
- **Over manual analysis**: For systematic investigation with multiple steps
- **Over sequential operations**: When operations can be parallelized
- **For exploration**: When you don't know exactly what you're looking for
- **For complexity**: Operations requiring >3 steps or multiple tool combinations
- **For specialization**: When specific expertise is needed (debugging, refactoring, etc.)

## Agent Types & Specializations

### Core Agents
- **general-purpose**: General research, complex searches, multi-step tasks, exploration
- **root-cause-analyst**: Systematic debugging, error investigation, evidence-based analysis
- **refactoring-expert**: Code quality improvement, technical debt reduction, clean code
- **technical-writer**: Documentation creation, API docs, user guides, technical content

### Quality & Testing
- **quality-engineer**: Test coverage, edge case detection, quality metrics, validation
- **requirements-analyst**: PRD analysis, feature scoping, requirement discovery
- **learning-guide**: Tutorial creation, educational content, progressive learning

### Architecture & Design  
- **system-architect**: System design, scalability planning, technical decisions
- **backend-architect**: API design, data integrity, fault tolerance, server architecture
- **frontend-architect**: UI/UX implementation, accessibility, modern frameworks
- **devops-architect**: Infrastructure automation, CI/CD, deployment optimization

### Specialized Expertise
- **security-engineer**: Vulnerability assessment, compliance, security patterns
- **performance-engineer**: Optimization, bottleneck analysis, efficiency improvements
- **socratic-mentor**: Teaching through questions, concept exploration, discovery learning
- **statusline-setup**: Status line configuration (specific to editor setup)
- **output-style-setup**: Output formatting and style configuration

## Works Best With
- **Sequential MCP**: Task delegates complex analysis → Sequential provides structured reasoning
- **Deepwiki MCP**: Task finds documentation needs → Deepwiki provides official patterns
- **Magic MCP**: Task identifies UI needs → Magic generates components
- **Morphllm MCP**: Task plans bulk edits → Morphllm executes pattern-based changes

## Decision Framework

```
Start: Is the scope clearly defined?
├─ No → Use general-purpose agent
├─ Yes → What type of task?
│   ├─ Debugging → root-cause-analyst
│   ├─ Refactoring → refactoring-expert
│   ├─ Documentation → technical-writer
│   ├─ Testing → quality-engineer
│   ├─ Architecture → system-architect
│   ├─ Performance → performance-engineer
│   └─ Security → security-engineer
```

## Usage Examples

```
"Find all authentication implementations" → Task (general-purpose)
"Debug why API returns 500 errors" → Task (root-cause-analyst)
"Refactor auth module for better maintainability" → Task (refactoring-expert)
"Document all REST endpoints" → Task (technical-writer)
"Identify missing test coverage" → Task (quality-engineer)
"Analyze system architecture" → Task (system-architect)
"Find performance bottlenecks" → Task (performance-engineer)
```

## Key Benefits

### Efficiency
- **Parallel Execution**: Agents can run operations concurrently
- **Automatic Tool Selection**: Agents choose optimal tools for each step
- **Context Preservation**: Maintains understanding across complex operations
- **Reduced Token Usage**: Delegation reduces main context consumption

### Accuracy
- **Specialized Expertise**: Each agent optimized for specific domains
- **Systematic Approach**: Structured methodology for each agent type
- **Comprehensive Coverage**: Agents don't miss important aspects
- **Evidence-Based**: Results backed by thorough analysis

### Scalability
- **Handle Complexity**: Manages operations of any size or scope
- **Progressive Enhancement**: Can start broad and narrow down
- **Cross-Domain**: Agents can coordinate for multi-aspect tasks
- **Stateless Operations**: Each invocation independent and focused

## Integration Patterns

### Search Pattern
```
User: "Where is user authentication handled?"
→ Task (general-purpose) for broad search
→ Agent searches multiple directories
→ Returns comprehensive results
```

### Debug Pattern
```
User: "Why is the login failing?"
→ Task (root-cause-analyst) for systematic debugging
→ Agent traces through logs, code, and config
→ Identifies root cause with evidence
```

### Refactor Pattern
```
User: "Improve code quality in payments module"
→ Task (refactoring-expert) for systematic improvement
→ Agent analyzes and refactors with best practices
→ Maintains functionality while improving structure
```

## Best Practices

1. **Let Agents Handle Scope**: Don't pre-filter - let agents determine scope
2. **Trust Agent Selection**: Agents know which tools to use
3. **Provide Context**: Give agents clear goals and constraints
4. **Review Agent Output**: Agents provide detailed analysis - use it
5. **Combine Agents**: Multiple agents can work on different aspects

## When NOT to Use Task Tool

- **Single File Operations**: When scope is clearly one file
- **Simple Queries**: Direct questions with known answers
- **Specific Tool Needs**: When you know exactly which tool to use
- **UI Generation**: Use Magic MCP directly for UI components
- **Documentation Lookup**: Use Deepwiki MCP for framework docs