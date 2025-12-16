# SuperClaude Reference Guide

This document consolidates principles, recommended rules, and best practices for enhanced operation.

---

## Core Philosophy
**Evidence > Assumptions | Code > Documentation | Efficiency > Verbosity**

---

## Engineering Principles

### SOLID
| Principle | Rule |
|-----------|------|
| **Single Responsibility** | One reason to change |
| **Open/Closed** | Extend, don't modify |
| **Liskov Substitution** | Subtypes must be substitutable |
| **Interface Segregation** | No unused dependencies |
| **Dependency Inversion** | Depend on abstractions |

### Essential Patterns
- **DRY**: Don't Repeat Yourself
- **KISS**: Keep It Simple, Stupid
- **YAGNI**: You Aren't Gonna Need It

---

## Quality Standards

### Four Quadrants
1. **Functional**: Does it work correctly?
2. **Structural**: Is it maintainable?
3. **Performance**: Is it efficient?
4. **Security**: Is it safe?

### Enforcement
- Automated testing and linting
- Error prevention > exception handling
- Make illegal states unrepresentable

---

## Decision Framework

### Evidence-Based
- Measure before optimizing
- Test hypotheses systematically
- Verify all claims with data

### Trade-offs
- Immediate vs long-term impact
- Reversible vs irreversible decisions
- Simplicity vs completeness

### Risk Management
- Identify risks proactively
- Assess probability × impact
- Maintain reversibility when uncertain

---

## Code Organization

### Naming Conventions
- **Consistency**: Follow language standards (camelCase for JS, snake_case for Python)
- **Descriptive**: Names must clearly describe purpose
- **Pattern Following**: Match existing project conventions
- **No Mixed Conventions**: Never mix styles within same project

### Directory Structure
- **Logical**: Organize by feature/domain, not file type
- **Hierarchical**: Clear parent-child relationships
- **Elegant**: Clean, scalable structure

---

## Tool Optimization

### Selection Priority
```
MCP Servers > Native Tools > Basic Tools
```

### Tool Selection Matrix
| Task | Recommended Tool |
|------|------------------|
| Automation | Rube MCP |
| Consensus Checks | PAL MCP |
| Web Research | LinkUp via Rube |
| Symbol Operations | UnifiedStore |
| Documentation | Repository templates |
| Pattern Search | Grep (not bash grep) |
| Bulk Edits | MultiEdit |

### Execution Patterns
- **Parallel Everything**: Execute independent operations in parallel
- **Batch Operations**: Use MultiEdit over multiple Edits
- **Agent Delegation**: Use Task agents for >3 step operations

---

## Performance Optimization

### Parallel Execution
- **File Operations**: Read multiple files in parallel
- **Independent Edits**: Apply edits simultaneously
- **Search Operations**: Run multiple patterns concurrently
- **Test Execution**: Run independent suites in parallel

### Resource Management
- **Context Awareness**: Switch to `--uc` mode at >75% context
- **Token Efficiency**: Use symbol communication when appropriate
- **Memory Management**: Clean up temporary resources promptly
- **Cache Utilization**: Reuse computed results

---

## Testing Guidelines

- **Coverage**: Aim for >80% on critical paths
- **Edge Cases**: Always test boundary conditions
- **Error Scenarios**: Test failure paths explicitly
- **Performance Tests**: Include benchmarks for critical operations

---

## Debugging Strategies

1. **Binary Search**: Isolate by halving the problem space
2. **Minimal Reproduction**: Create smallest failing case
3. **Logging Strategy**: Add strategic log points
4. **Hypothesis Testing**: Form and test specific theories

---

## Architecture Guidelines

### Component Design
- **Single Purpose**: One clear responsibility per component
- **Loose Coupling**: Minimize dependencies
- **High Cohesion**: Related functionality stays together
- **Clear Interfaces**: Well-defined APIs

### Data Flow
- **Unidirectional**: Prefer one-way data flow
- **Immutability**: Avoid mutating shared state
- **Event-Driven**: Use events for loose coupling
- **Caching Strategy**: Cache expensive computations

---

## Communication Best Practices

### Progress Updates
- Update TodoWrite every 3-5 completed items
- Use status symbols consistently: ✅ 🔄 ⏳ ❌
- Brief, technical descriptions
- Specific next steps when blocked

### Error Reporting
- Include error messages and stack traces
- Document reproduction steps
- List attempted solutions
- Describe impact scope

---

## Quick Reference Checklist

- [ ] Parallel operations planned?
- [ ] Best tool selected for task?
- [ ] Batch operations utilized?
- [ ] Context usage monitored?
- [ ] Clean workspace maintained?
- [ ] Code patterns followed?
- [ ] Tests comprehensive?
- [ ] Documentation updated?

---

## Key Takeaways

1. Build only what's requested
2. Complete what you start
3. Validate inputs, not exceptions
4. Evidence drives decisions
5. Simple solutions first
6. Always parallelize independent operations
7. Use specialized tools over generic ones
8. Profile before optimizing
