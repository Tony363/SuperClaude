# SuperClaude Tools Reference

## Task Agents
Quick selection guide for specialized agents.

### Analysis & Discovery
- **general-purpose**: Unknown scope, exploration, multi-step research
- **root-cause-analyst**: Debugging, error investigation, bottlenecks
- **requirements-analyst**: Feature analysis, PRD breakdown, scoping

### Code & Quality
- **refactoring-expert**: Technical debt, code cleanup, patterns
- **quality-engineer**: Test coverage, edge cases, quality metrics
- **performance-engineer**: Optimization, bottlenecks, efficiency

### Architecture & Design
- **system-architect**: System design, scalability, architecture
- **backend-architect**: API design, database, server patterns
- **frontend-architect**: UI/UX, components, accessibility
- **security-engineer**: Audits, vulnerabilities, compliance

### Documentation & Learning
- **technical-writer**: API docs, user guides, documentation
- **learning-guide**: Tutorials, educational content, explanations
- **socratic-mentor**: Teaching through questions, concept exploration

### Operations
- **devops-architect**: Infrastructure, CI/CD, deployment
- **python-expert**: Python-specific expertise and patterns

## MCP Servers
Specialized tools for enhanced capabilities.

### Core Development
- **Serena**: Symbol operations, LSP integration, project memory
  - Use for: Rename functions, find references, session persistence
  
- **Morphllm**: Pattern-based bulk edits, token-optimized
  - Use for: Style enforcement, multi-file replacements, framework updates

- **Sequential**: Multi-step reasoning, complex analysis
  - Use for: Debugging, architecture review, systematic problem solving

### UI & Documentation  
- **Magic**: Modern UI components from 21st.dev patterns
  - Use for: React/Vue/Angular components, accessible UI, design systems

- **Deepwiki**: Technical documentation, framework patterns
  - Use for: Library docs, API references, best practices

- **Playwright**: Browser automation, E2E testing
  - Use for: Visual testing, user flows, accessibility validation

## Quality Evaluation
Simple scoring system for all outputs:

| Score | Action | Description |
|-------|--------|-------------|
| 90-100 | ✅ Accept | Production-ready |
| 70-89 | ⚠️ Review | Acceptable with notes |
| < 70 | 🔄 Iterate | Auto-improve required |

Quality dimensions: Correctness (40%), Completeness (30%), Code Quality (20%), Performance (10%)

## Tool Selection Matrix

| Task | First Choice | Alternative |
|------|-------------|-------------|
| Find unknown code | Task(general-purpose) | Grep/Glob |
| Debug error | Task(root-cause-analyst) | Sequential |
| Refactor code | Task(refactoring-expert) | Morphllm |
| Create UI | Magic | Manual coding |
| Get docs | Deepwiki | WebSearch |
| Rename symbol | Serena | Manual search |
| Bulk edits | Morphllm | MultiEdit |
| Complex analysis | Sequential | Native reasoning |
| Browser test | Playwright | Unit tests |

## Decision Flow
```
Unknown scope? → Task(general-purpose)
Debugging? → Task(root-cause-analyst)
UI component? → Magic
Documentation? → Deepwiki
Symbol operation? → Serena
Bulk edits? → Morphllm
Complex reasoning? → Sequential
Browser testing? → Playwright
Quality < 70? → Auto-iterate with feedback
```