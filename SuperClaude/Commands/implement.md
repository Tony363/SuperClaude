---
name: implement
description: "Feature and code implementation with intelligent persona activation and MCP integration"
category: workflow
complexity: standard
mcp-servers: [zen]
personas: [architect, frontend, backend, security, qa-specialist]
requires_evidence: true
---

# /sc:implement - Feature Implementation

> **Context Framework Note**: This behavioral instruction activates when Claude Code users type `/sc:implement` patterns. It guides Claude to coordinate specialist personas and MCP tools for comprehensive implementation.

## Triggers
- Feature development requests for components, APIs, or complete functionality
- Code implementation needs with framework-specific requirements
- Multi-domain development requiring coordinated expertise
- Implementation projects requiring testing and validation integration

## Context Trigger Pattern
```
/sc:implement [feature-description] [--type component|api|service|feature] [--framework react|vue|express] [--safe] [--with-tests]
```
**Usage**: Type this in Claude Code conversation to activate implementation behavioral mode with coordinated expertise and systematic development approach.

## Behavioral Flow
1. **Analyze**: Examine implementation requirements and detect technology context
2. **Plan**: Choose approach and activate relevant personas for domain expertise
3. **Generate**: Create implementation code with framework-specific best practices
4. **Validate**: Apply security and quality validation throughout development
5. **Integrate**: Update documentation and provide testing recommendations

Key behaviors:
- Context-based persona activation (architect, frontend, backend, security, qa)
- Framework-specific implementation via curated repository guidance and playbooks
- Consensus validation on risky changes via Zen MCP
- Evidence-driven reporting — never claim code exists without showing diff + tests

## Knowledge Inputs
- **Zen MCP**: Consensus building for architectural and security-sensitive decisions
- **Repository Standards**: Framework documentation, patterns, and best practices
- **UnifiedStore**: Cross-session implementation state, learnings, and checkpoints

## Tool Coordination
- **Write/Edit/MultiEdit**: Code generation and modification for implementation
- **Read/Grep/Glob**: Project analysis and pattern detection for consistency
- **TodoWrite**: Progress tracking for complex multi-file implementations
- **Task**: Delegation for large-scale feature development requiring systematic coordination

## Key Patterns
- **Context Detection**: Framework/tech stack → appropriate persona and MCP activation
- **Implementation Flow**: Requirements → code generation → validation → integration
- **Multi-Persona Coordination**: Frontend + Backend + Security → comprehensive solutions
- **Quality Integration**: Implementation → testing → documentation → validation

## Implementation Guardrails
- Start in analysis mode; produce a scoped plan before touching files.
- Only mark implementation complete when you can reference concrete repo changes (filenames + key diff hunks) and the relevant test or lint results.
- If tooling access is unavailable, return the plan + next actions and explicitly state that no code was written yet.
- Prefer minimal viable change; skip speculative scaffolding.
- Escalate to security persona before modifying auth, secrets, or permissions.

## Examples

### React Component Implementation
```
/sc:implement user profile component --type component --framework react
# Repository guidance surfaces framework-specific scaffold patterns
# Frontend persona ensures best practices and accessibility
```

### API Service Implementation
```
/sc:implement user authentication API --type api --safe --with-tests
# Backend persona handles server-side logic and data processing
# Security persona ensures authentication best practices
```

### Full-Stack Feature
```
/sc:implement payment processing system --type feature --with-tests
# Multi-persona coordination: architect, frontend, backend, security
# Zen MCP validates complex implementation steps
# Return diff + tests or explicitly note pending work
```

### Framework-Specific Implementation
```
/sc:implement dashboard widget --framework vue
# Repository knowledge provides Vue-specific patterns and documentation
# Framework-appropriate implementation with official best practices
```

## Boundaries

**Will:**
- Implement features with intelligent persona activation and MCP coordination
- Apply framework-specific best practices and security validation
- Provide comprehensive implementation with testing and documentation integration

**Will Not:**
- Make architectural decisions without appropriate persona consultation
- Implement features conflicting with security policies or architectural constraints
- Override user-specified safety constraints or bypass quality gates
