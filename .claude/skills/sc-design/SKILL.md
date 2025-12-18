---
name: sc-design
description: Design system architecture, APIs, and component interfaces with comprehensive specifications. Use when planning architecture, designing APIs, creating component interfaces, or modeling databases.
---

# System & Component Design Skill

Architecture planning and interface design with industry best practices.

## Quick Start

```bash
# Architecture design
/sc:design [target] --type architecture

# API specification
/sc:design payment-api --type api --format spec

# Database schema
/sc:design e-commerce --type database --format diagram
```

## Behavioral Flow

1. **Analyze** - Examine requirements and existing system context
2. **Plan** - Define design approach based on type and format
3. **Design** - Create specifications with best practices
4. **Validate** - Ensure maintainability and scalability
5. **Document** - Generate diagrams and specifications

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | string | architecture | architecture, api, component, database |
| `--format` | string | spec | diagram, spec, code |

## Evidence Requirements

This skill does NOT require hard evidence. Deliverables are:
- Design specifications and diagrams
- Interface definitions
- Schema documentation

## Design Types

### Architecture (`--type architecture`)
- System structure and component relationships
- Scalability and reliability patterns
- Service boundaries and communication

### API (`--type api`)
- RESTful/GraphQL endpoint design
- Request/response schemas
- Authentication and versioning

### Component (`--type component`)
- Interface contracts and dependencies
- State management patterns
- Integration points

### Database (`--type database`)
- Entity relationships and constraints
- Normalization and indexing
- Performance considerations

## Output Formats

### Diagram (`--format diagram`)
- ASCII or Mermaid diagrams
- Component relationship visualization
- Data flow representation

### Specification (`--format spec`)
- OpenAPI/Swagger for APIs
- Detailed interface documentation
- Technical requirements

### Code (`--format code`)
- Interface definitions
- Type declarations
- Skeleton implementations

## Examples

### System Architecture
```
/sc:design user-management --type architecture --format diagram
# Component relationships, data flow, scalability patterns
```

### API Design
```
/sc:design payment-api --type api --format spec
# OpenAPI spec with endpoints, schemas, auth patterns
```

### Component Interface
```
/sc:design notification-service --type component --format code
# TypeScript/Python interfaces with clear contracts
```

### Database Schema
```
/sc:design inventory-db --type database --format diagram
# ER diagrams with relationships and constraints
```

## Tool Coordination

- **Read** - Requirements analysis
- **Grep/Glob** - Pattern analysis
- **Write** - Design documentation
- **Bash** - External tool integration
