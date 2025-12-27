---
name: improve
description: "Apply systematic improvements to code quality, performance, maintainability, and cleanup"
category: workflow
complexity: standard
mcp-servers: [pal, rube]
personas: [architect, performance, quality, security]
aliases: [cleanup]
flags:
  - name: cleanup
    description: >
      Enable cleanup mode: systematically remove dead code, optimize imports, and improve project structure.
    type: boolean
    default: false
  - name: type
    description: >
      Improvement focus area
    type: string
    default: quality
    options: [quality, performance, maintainability, style, code, imports, files, all]
  - name: safe
    description: >
      Conservative mode with automatic safety validation
    type: boolean
    default: true
  - name: aggressive
    description: >
      Thorough cleanup with framework patterns (use with caution)
    type: boolean
    default: false
---

# /sc:improve - Code Improvement & Cleanup

## Triggers
- Code quality enhancement and refactoring requests
- Performance optimization and bottleneck resolution needs
- Maintainability improvements and technical debt reduction
- Best practices application and coding standards enforcement
- Code maintenance and dead code removal requests (formerly `/sc:cleanup`)
- Import optimization and project structure improvements
- Codebase hygiene and organization requirements

## Usage
```
/sc:improve [target] [--type quality|performance|maintainability|style] [--safe] [--interactive]
/sc:improve [target] --cleanup [--type code|imports|files|all] [--safe|--aggressive]
```

**Note**: This command consolidates former `/sc:cleanup` command. Use `--cleanup` for dead code removal and project structure optimization.

## Behavioral Flow
1. **Analyze**: Examine codebase for improvement opportunities and quality issues
2. **Plan**: Choose improvement approach and activate relevant personas for expertise
3. **Execute**: Apply systematic improvements with domain-specific best practices
4. **Validate**: Ensure improvements preserve functionality and meet quality standards
5. **Document**: Generate improvement summary and recommendations for future work

Key behaviors:
- Multi-persona coordination (architect, performance, quality, security) based on improvement type
- Framework-specific optimization via curated repository standards and best practices
- Consensus validation via PAL MCP for complex multi-component improvements
- Safe refactoring with comprehensive validation and rollback capabilities

## Knowledge Inputs
- **Repository Standards**: Framework-specific best practices and optimization patterns
- **PAL MCP**: Consensus-backed validation for high-impact changes
- **Rube MCP**: Coordinate code-quality follow-ups (tickets, release announcements, alerts)
- **Persona Coordination**: Architect (structure), Performance (speed), Quality (maintainability), Security (safety)

## Tool Coordination
- **Read/Grep/Glob**: Code analysis and improvement opportunity identification
- **Edit/MultiEdit**: Safe code modification and systematic refactoring
- **TodoWrite**: Progress tracking for complex multi-file improvement operations
- **Task**: Delegation for large-scale improvement workflows requiring systematic coordination

## Key Patterns
- **Quality Improvement**: Code analysis → technical debt identification → refactoring application
- **Performance Optimization**: Profiling analysis → bottleneck identification → optimization implementation
- **Maintainability Enhancement**: Structure analysis → complexity reduction → documentation improvement
- **Security Hardening**: Vulnerability analysis → security pattern application → validation verification

## Cleanup Mode (`--cleanup`)
When activated, enables systematic cleanup operations:
- **Dead Code Detection**: Usage analysis → safe removal with dependency validation
- **Import Optimization**: Dependency analysis → unused import removal and organization
- **Structure Cleanup**: Architectural analysis → file organization and modular improvements
- **Safety Validation**: Pre/during/post checks → preserve functionality throughout cleanup

## Examples

### Code Quality Enhancement
```
/sc:improve src/ --type quality --safe
# Systematic quality analysis with safe refactoring application
# Improves code structure, reduces technical debt, enhances readability
```

### Performance Optimization
```
/sc:improve api-endpoints --type performance --interactive
# Performance persona analyzes bottlenecks and optimization opportunities
# Interactive guidance for complex performance improvement decisions
```

### Maintainability Improvements
```
/sc:improve legacy-modules --type maintainability --preview
# Architect persona analyzes structure and suggests maintainability improvements
# Preview mode shows changes before application for review
```

### Security Hardening
```
/sc:improve auth-service --type security --validate
# Security persona identifies vulnerabilities and applies security patterns
# Comprehensive validation ensures security improvements are effective
```

### Dead Code Cleanup (formerly /sc:cleanup)
```
/sc:improve src/ --cleanup --type code --safe
# Conservative cleanup with automatic safety validation
# Removes dead code while preserving all functionality
```

### Import Optimization
```
/sc:improve --cleanup --type imports --preview
# Analyzes and shows unused import cleanup without execution
# Framework-aware optimization leveraging repository patterns
```

### Comprehensive Project Cleanup
```
/sc:improve --cleanup --type all --interactive
# Multi-domain cleanup with user guidance for complex decisions
# Activates all personas for comprehensive analysis
```

## Boundaries

**Will:**
- Apply systematic improvements with domain-specific expertise and validation
- Provide comprehensive analysis with multi-persona coordination and best practices
- Execute safe refactoring with rollback capabilities and quality preservation
- Systematically clean code, remove dead code, and optimize project structure
- Provide comprehensive safety validation with backup and rollback capabilities
- Apply intelligent cleanup algorithms with framework-specific pattern recognition

**Will Not:**
- Apply risky improvements without proper analysis and user confirmation
- Make architectural changes without understanding full system impact
- Override established coding standards or project-specific conventions
- Remove code without thorough safety analysis and validation
- Override project-specific cleanup exclusions or architectural constraints
- Apply cleanup operations that compromise functionality or introduce bugs
