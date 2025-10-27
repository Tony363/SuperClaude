# Claude Code Recommended Rules

Best practices and optimization guidelines for enhanced Claude Code operation.
These 🟢 RECOMMENDED rules should be applied when practical.
For critical and important rules, see RULES_CRITICAL.md.

## 🟢 RECOMMENDED Rules

### Code Organization
**Triggers**: Creating files, structuring projects, naming decisions

- **Naming Convention Consistency**: Follow language/framework standards (camelCase for JS, snake_case for Python)
- **Descriptive Names**: Files, functions, variables must clearly describe their purpose
- **Logical Directory Structure**: Organize by feature/domain, not file type
- **Pattern Following**: Match existing project organization and naming schemes
- **Hierarchical Logic**: Create clear parent-child relationships in folder structure
- **No Mixed Conventions**: Never mix camelCase/snake_case/kebab-case within same project
- **Elegant Organization**: Clean, scalable structure that aids navigation and understanding

✅ **Right**: `getUserData()`, `user_data.py`, `components/auth/`  
❌ **Wrong**: `get_userData()`, `userdata.py`, `files/everything/`

### Tool Optimization
**Triggers**: Multi-step operations, performance needs, complex tasks

- **Best Tool Selection**: Always use the most powerful tool for each task (MCP > Native > Basic)
- **Parallel Everything**: Execute independent operations in parallel, never sequentially
- **Agent Delegation**: Use Task agents for complex multi-step operations (>3 steps)
- **MCP Server Usage**: Leverage specialized MCP servers for their strengths:
  - MultiEdit for bulk edits
  - Zen for consensus and risk validation
  - Rube for cross-system automation
  - Browser MCP for quick local browser workflows; scale out with Playwright/Cypress when needed
- **Batch Operations**: Use MultiEdit over multiple Edits, batch Read calls, group operations
- **Powerful Search**: Use Grep tool over bash grep, Glob over find, specialized search tools
- **Efficiency First**: Choose speed and power over familiarity - use the fastest method available
- **Tool Specialization**: Match tools to their designed purpose

✅ **Right**: Use MultiEdit for 3+ file changes, parallel Read calls  
❌ **Wrong**: Sequential Edit calls, bash grep instead of Grep tool

### Performance Optimization

#### Parallel Execution Patterns
- **File Operations**: Read multiple files in parallel, not sequentially
- **Independent Edits**: Apply edits to multiple files simultaneously
- **Search Operations**: Run multiple search patterns concurrently
- **Test Execution**: Run independent test suites in parallel

#### Resource Management
- **Context Awareness**: Monitor context usage, switch to --uc mode at >75%
- **Token Efficiency**: Use symbol communication when appropriate
- **Memory Management**: Clean up temporary resources promptly
- **Cache Utilization**: Reuse computed results across operations

### Code Quality Best Practices

#### Documentation Standards
- **Inline Comments**: Only when logic is non-obvious
- **Function Documentation**: Clear purpose and parameter descriptions
- **README Updates**: Keep synchronized with code changes
- **API Documentation**: Include examples for all endpoints

#### Testing Guidelines
- **Test Coverage**: Aim for >80% coverage on critical paths
- **Edge Cases**: Always test boundary conditions
- **Error Scenarios**: Test failure paths explicitly
- **Performance Tests**: Include benchmarks for critical operations

#### Refactoring Principles
- **Small Increments**: Refactor in small, testable chunks
- **Preserve Behavior**: Ensure tests pass before and after
- **Clean As You Go**: Improve code quality during feature work
- **Technical Debt**: Track and address systematically

### Communication Best Practices

#### Progress Updates
- **Regular Checkpoints**: Update TodoWrite every 3-5 completed items
- **Clear Status**: Use status symbols (✅, 🔄, ⏳, ❌) consistently
- **Concise Explanations**: Brief, technical descriptions
- **Actionable Feedback**: Specific next steps when blocked

#### Error Reporting
- **Relevant Context**: Include error messages and stack traces
- **Reproduction Steps**: Document how to reproduce issues
- **Attempted Solutions**: List what was already tried
- **Impact Assessment**: Describe scope of the problem

### Development Workflow Optimizations

#### Branch Management
- **Descriptive Names**: feature/, bugfix/, refactor/ prefixes
- **Small PRs**: Keep pull requests focused and reviewable
- **Regular Rebasing**: Keep feature branches up-to-date
- **Clean History**: Squash commits when appropriate

#### Dependency Management
- **Version Pinning**: Use exact versions in production
- **Regular Updates**: Schedule dependency updates
- **Security Scanning**: Check for vulnerabilities
- **License Compliance**: Verify license compatibility

#### Debugging Strategies
- **Binary Search**: Isolate issues by halving the problem space
- **Minimal Reproduction**: Create smallest failing case
- **Logging Strategy**: Add strategic log points
- **Hypothesis Testing**: Form and test specific theories

### Architecture Guidelines

#### Component Design
- **Single Purpose**: Each component has one clear responsibility
- **Loose Coupling**: Minimize dependencies between components
- **High Cohesion**: Related functionality stays together
- **Clear Interfaces**: Well-defined APIs between components

#### Data Flow
- **Unidirectional**: Prefer one-way data flow patterns
- **Immutability**: Avoid mutating shared state
- **Event-Driven**: Use events for loose coupling
- **Caching Strategy**: Cache expensive computations

#### Scalability Considerations
- **Horizontal Scaling**: Design for multiple instances
- **Stateless Services**: Keep services stateless when possible
- **Database Optimization**: Use appropriate indexes
- **Async Processing**: Offload heavy work to background jobs

## Quick Reference

### Tool Selection Matrix
```
Task Type → Recommended Tool:
├─ Automation → Rube MCP
├─ Consensus Checks → Zen MCP
├─ Browser Testing → Browser MCP for targeted flows; Playwright/Cypress for large suites
├─ Symbol Operations → UnifiedStore
├─ Documentation → Repository templates & standards
└─ Pattern Search → Grep (not bash grep)
```

### Optimization Checklist
- [ ] Parallel operations planned?
- [ ] Best tool selected for task?
- [ ] Batch operations utilized?
- [ ] Context usage monitored?
- [ ] Clean workspace maintained?
- [ ] Code patterns followed?
- [ ] Tests comprehensive?
- [ ] Documentation updated?

### Performance Tips
1. **Always parallelize** independent operations
2. **Batch similar operations** together
3. **Use specialized tools** over generic ones
4. **Monitor context usage** and adapt
5. **Clean as you go** to prevent bloat
6. **Cache computed results** when possible
7. **Profile before optimizing** specific code

---
*Recommended practices for optimal Claude Code operation*
*Apply these guidelines when practical to enhance quality and efficiency*
