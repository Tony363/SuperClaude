---
name: sc-brainstorm
description: Interactive requirements discovery through Socratic dialogue and systematic exploration. Use when transforming ambiguous ideas into concrete specifications, validating concepts, or coordinating multi-persona analysis.
---

# Brainstorming & Requirements Discovery Skill

Transform ambiguous ideas into concrete specifications through structured exploration.

## Quick Start

```bash
# Basic brainstorm
/sc:brainstorm [topic]

# Deep systematic exploration
/sc:brainstorm "AI project management tool" --strategy systematic --depth deep

# Parallel exploration with multiple personas
/sc:brainstorm "real-time collaboration" --strategy agile --parallel
```

## Behavioral Flow

1. **Explore** - Transform ambiguous ideas through Socratic dialogue
2. **Analyze** - Coordinate multiple personas for domain expertise
3. **Validate** - Apply feasibility assessment across domains
4. **Specify** - Generate concrete specifications
5. **Handoff** - Create actionable briefs for implementation

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--strategy` | string | systematic | systematic, agile, enterprise |
| `--depth` | string | normal | shallow, normal, deep |
| `--parallel` | bool | false | Enable parallel exploration paths |
| `--validate` | bool | false | Include feasibility validation |

## Personas Activated

- **architect** - System design and technical feasibility
- **analyzer** - Requirements analysis and complexity assessment
- **frontend** - User experience and interface considerations
- **backend** - API and data architecture
- **security** - Security requirements and compliance
- **devops** - Infrastructure and deployment considerations
- **project-manager** - Timeline and resource planning

## MCP Integration

- **PAL MCP** - Consensus building for conflicting priorities
- **Rube MCP** - Cross-session persistence and memory management

## Evidence Requirements

This skill does NOT require hard evidence. Focus on:
- Documenting exploration paths and decisions
- Recording stakeholder input and priorities
- Capturing specifications and requirements

## Exploration Strategies

### Systematic (`--strategy systematic`)
- Structured question-driven discovery
- Comprehensive domain coverage
- Documentation-heavy approach

### Agile (`--strategy agile`)
- Rapid iteration cycles
- User story focused
- Minimal viable specification

### Enterprise (`--strategy enterprise`)
- Compliance and governance focus
- Stakeholder alignment
- Risk assessment integration

## Examples

### Product Discovery
```
/sc:brainstorm "AI-powered analytics dashboard" --strategy systematic --depth deep
# Multi-persona analysis with comprehensive feasibility
```

### Feature Exploration
```
/sc:brainstorm "real-time notifications" --strategy agile --parallel
# Parallel paths: frontend UX, backend architecture, security implications
```

### Enterprise Solution
```
/sc:brainstorm "enterprise data platform" --strategy enterprise --validate
# Compliance-aware exploration with security and devops input
```

## Tool Coordination

- **Read/Write** - Requirements documentation
- **TodoWrite** - Exploration progress tracking
- **Task** - Parallel exploration delegation
- **WebSearch** - Market research and technology validation
