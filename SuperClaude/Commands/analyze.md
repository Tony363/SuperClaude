---
name: analyze
description: "Comprehensive code analysis, quality assessment, and issue diagnosis across all domains"
category: utility
complexity: basic
mcp-servers: []
personas: []
aliases: [troubleshoot]
flags:
  - name: focus
    description: >
      Analysis focus area
    type: string
    default: quality
    options: [quality, security, performance, architecture, bug, build, deployment]
  - name: troubleshoot
    description: >
      Enable troubleshooting mode for issue diagnosis and resolution
    type: boolean
    default: false
  - name: trace
    description: >
      Enable detailed trace analysis for debugging
    type: boolean
    default: false
  - name: fix
    description: >
      Automatically apply safe fixes for identified issues
    type: boolean
    default: false
---

# /sc:analyze - Code Analysis, Quality Assessment & Troubleshooting

## Triggers
- Code quality assessment requests for projects or specific components
- Security vulnerability scanning and compliance validation needs
- Performance bottleneck identification and optimization planning
- Architecture review and technical debt assessment requirements
- Code defects and runtime error investigation (formerly `/sc:troubleshoot`)
- Build failure analysis and resolution needs
- Deployment problem analysis and system behavior debugging

## Usage
```
/sc:analyze [target] [--focus quality|security|performance|architecture] [--depth quick|deep] [--format text|json|report]
/sc:analyze [issue] --troubleshoot [--focus bug|build|performance|deployment] [--trace] [--fix]
```

**Note**: This command consolidates former `/sc:troubleshoot` command. Use `--troubleshoot` for issue diagnosis and resolution.

## Behavioral Flow
1. **Discover**: Categorize source files using language detection and project analysis
2. **Scan**: Apply domain-specific analysis techniques and pattern matching
3. **Evaluate**: Generate prioritized findings with severity ratings and impact assessment
4. **Recommend**: Create actionable recommendations with implementation guidance
5. **Report**: Present comprehensive analysis with metrics and improvement roadmap

Key behaviors:
- Multi-domain analysis combining static analysis and heuristic evaluation
- Intelligent file discovery and language-specific pattern recognition
- Severity-based prioritization of findings and recommendations
- Comprehensive reporting with metrics, trends, and actionable insights

## Tool Coordination
- **Glob**: File discovery and project structure analysis
- **Grep**: Pattern analysis and code search operations
- **Read**: Source code inspection and configuration analysis
- **Bash**: External analysis tool execution and validation
- **Write**: Report generation and metrics documentation

## Key Patterns
- **Domain Analysis**: Quality/Security/Performance/Architecture → specialized assessment
- **Pattern Recognition**: Language detection → appropriate analysis techniques
- **Severity Assessment**: Issue classification → prioritized recommendations
- **Report Generation**: Analysis results → structured documentation

## Troubleshooting Mode (`--troubleshoot`)
When activated, enables issue diagnosis and resolution:
- **Bug Investigation**: Error analysis → stack trace examination → code inspection → fix validation
- **Build Troubleshooting**: Build log analysis → dependency checking → configuration validation
- **Performance Diagnosis**: Metrics analysis → bottleneck identification → optimization recommendations
- **Deployment Issues**: Environment analysis → configuration verification → service validation

## Examples

### Comprehensive Project Analysis
```
/sc:analyze
# Multi-domain analysis of entire project
# Generates comprehensive report with key findings and roadmap
```

### Focused Security Assessment
```
/sc:analyze src/auth --focus security --depth deep
# Deep security analysis of authentication components
# Vulnerability assessment with detailed remediation guidance
```

### Performance Optimization Analysis
```
/sc:analyze --focus performance --format report
# Performance bottleneck identification
# Generates HTML report with optimization recommendations
```

### Quick Quality Check
```
/sc:analyze src/components --focus quality --depth quick
# Rapid quality assessment of component directory
# Identifies code smells and maintainability issues
```

### Code Bug Investigation (formerly /sc:troubleshoot)
```
/sc:analyze "Null pointer exception in user service" --troubleshoot --focus bug --trace
# Systematic analysis of error context and stack traces
# Identifies root cause and provides targeted fix recommendations
```

### Build Failure Analysis
```
/sc:analyze "TypeScript compilation errors" --troubleshoot --focus build --fix
# Analyzes build logs and TypeScript configuration
# Automatically applies safe fixes for common compilation issues
```

### Performance Issue Diagnosis
```
/sc:analyze "API response times degraded" --troubleshoot --focus performance
# Performance metrics analysis and bottleneck identification
# Provides optimization recommendations and monitoring guidance
```

### Deployment Problem Resolution
```
/sc:analyze "Service not starting in production" --troubleshoot --focus deployment --trace
# Environment and configuration analysis
# Systematic verification of deployment requirements and dependencies
```

## Boundaries

**Will:**
- Perform comprehensive static code analysis across multiple domains
- Generate severity-rated findings with actionable recommendations
- Provide detailed reports with metrics and improvement guidance
- Execute systematic issue diagnosis using structured debugging methodologies
- Provide validated solution approaches with comprehensive problem analysis
- Apply safe fixes with verification and detailed resolution documentation

**Will Not:**
- Execute dynamic analysis requiring code compilation or runtime
- Modify source code or apply fixes without explicit user consent
- Analyze external dependencies beyond import and usage patterns
- Apply risky fixes without proper analysis and user confirmation
- Modify production systems without explicit permission and safety validation
- Make architectural changes without understanding full system impact