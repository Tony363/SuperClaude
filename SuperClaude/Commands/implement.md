---
name: implement
description: "Feature and code implementation with intelligent persona activation, task orchestration, and MCP integration"
category: workflow
complexity: standard
mcp-servers: [zen, rube]
personas: [architect, frontend, backend, security, qa-specialist, project-manager, devops]
requires_evidence: true
aliases: [task, spawn]
flags:
  - name: fast-codex
    description: >
      Skip multi-persona orchestration and route through the Codex implementer path
      for quick diffs. Guardrails (evidence, telemetry, MCP) remain enforced.
    type: boolean
    default: false
    guardrails:
      - >
        Falls back to the full persona set when consensus, security, or evidence
        checks require broader coverage.
  - name: orchestrate
    description: >
      Enable meta-system task orchestration with intelligent breakdown and delegation.
      Activates hierarchical task decomposition (Epic → Story → Task → Subtask).
    type: boolean
    default: false
  - name: strategy
    description: >
      Task execution strategy: systematic (comprehensive), agile (iterative),
      enterprise (governance), sequential, parallel, or adaptive.
    type: string
    default: systematic
    options: [systematic, agile, enterprise, sequential, parallel, adaptive]
  - name: delegate
    description: >
      Enable intelligent delegation to appropriate MCP servers and personas.
    type: boolean
    default: false
---

# /sc:implement - Feature Implementation & Task Orchestration

> **Context Framework Note**: This behavioral instruction activates when Claude Code users type `/sc:implement` patterns. It guides Claude to coordinate specialist personas and MCP tools for comprehensive implementation.

## Triggers
- Feature development requests for components, APIs, or complete functionality
- Code implementation needs with framework-specific requirements
- Multi-domain development requiring coordinated expertise
- Implementation projects requiring testing and validation integration
- Complex tasks requiring multi-agent coordination and delegation (formerly `/sc:task`)
- Large-scale operations requiring intelligent task breakdown (formerly `/sc:spawn`)
- Projects needing structured workflow management and cross-session persistence

## Context Trigger Pattern
```
/sc:implement [feature-description] [--type component|api|service|feature] [--framework react|vue|express] [--safe] [--with-tests]
/sc:implement [task] --orchestrate [--strategy systematic|agile|enterprise|parallel|adaptive] [--delegate]
```
**Usage**: Type this in Claude Code conversation to activate implementation behavioral mode with coordinated expertise and systematic development approach.

**Note**: This command consolidates former `/sc:task` and `/sc:spawn` commands. Use `--orchestrate` for complex multi-domain operations requiring intelligent task breakdown.

### Quick Codex Flow (`--fast-codex`)
- Prefer for low-risk or repetitive edits where rapid Codex execution is desired.
- Activates a streamlined `codex-implementer` persona instead of the full architect/front/back/security set.
- Guardrails remain: evidence capture, telemetry tagging, MCP integrations, and `requires_evidence` enforcement.
- Automatically falls back to standard mode when consensus, security, or evidence gates trigger.

**Example**
```
/sc:implement refactor logging middleware --fast-codex
```

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
- **Rube MCP**: External automation (ticketing, notifications, CI hooks) aligned to task outputs
- **Repository Standards**: Framework documentation, patterns, and best practices
- **UnifiedStore**: Cross-session implementation state, learnings, and checkpoints

## Task Orchestration Mode (`--orchestrate`)
When activated, enables meta-system task orchestration:
- **Task Hierarchy**: Epic-level objectives → Story coordination → Task execution → Subtask granularity
- **Strategy Selection**: Systematic (comprehensive) → Agile (iterative) → Enterprise (governance) → Parallel → Adaptive
- **Multi-Agent Coordination**: Persona activation → MCP routing → parallel execution → result integration
- **Cross-Session Management**: Task persistence → context continuity → progressive enhancement

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

### Fast Codex Shortcut
```
/sc:implement legacy cleanup --fast-codex --with-tests
# Codex persona runs streamlined diff creation while evidence guardrails stay active
```

### Complex Task Orchestration (formerly /sc:task, /sc:spawn)
```
/sc:implement "enterprise authentication system" --orchestrate --strategy systematic --delegate
# Comprehensive task breakdown with multi-domain coordination
# Activates architect, security, backend, frontend personas
```

```
/sc:implement "migrate legacy monolith to microservices" --orchestrate --strategy adaptive
# Enterprise-scale operation with sophisticated orchestration
# Adaptive coordination based on operation characteristics
```

## Boundaries

**Will:**
- Implement features with intelligent persona activation and MCP coordination
- Apply framework-specific best practices and security validation
- Provide comprehensive implementation with testing and documentation integration
- Execute complex tasks with multi-agent coordination and intelligent delegation
- Provide hierarchical task breakdown with cross-session persistence
- Decompose complex multi-domain operations into coordinated task hierarchies

**Will Not:**
- Make architectural decisions without appropriate persona consultation
- Implement features conflicting with security policies or architectural constraints
- Override user-specified safety constraints or bypass quality gates
- Execute operations without proper dependency analysis and validation
