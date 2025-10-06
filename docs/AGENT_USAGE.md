# SuperClaude Agent System Usage Guide

## Overview

The SuperClaude Agent System (v5.0.0-alpha) provides a modular framework for specialized task execution with intelligent agent selection and delegation capabilities.

## Current Status (60% Complete)

### ✅ Implemented
- Core infrastructure (BaseAgent, Registry, Selector, Loader)
- Agent discovery from 141 markdown definitions
- Context-based selection with multi-factor scoring
- Dynamic loading with LRU cache
- Generic markdown agent execution
- 5 core Python agents
- CLI integration with --delegate flag

### 🚧 In Progress
- Full CLI UI for agent selection
- Agent coordination features
- Execution history tracking

## Quick Start

### Using the CLI

```bash
# List all available agents
SuperClaude agent list

# List agents by category
SuperClaude agent list --category core

# Get info about a specific agent
SuperClaude agent info root-cause-analyst

# Auto-select and run best agent for task
SuperClaude agent run --delegate "Debug why my app crashes"

# Run specific agent
SuperClaude agent run --name performance-engineer "Optimize database queries"

# See agent suggestions without running
SuperClaude agent run --suggest "Refactor this code"
```

### Using in Code

```python
from SuperClaude.Agents import AgentRegistry, AgentSelector, AgentLoader

# Initialize system
registry = AgentRegistry()
selector = AgentSelector(registry)
loader = AgentLoader(registry)

# Auto-select best agent
context = {"task": "Debug authentication failure"}
scores = selector.select_agent(context)
best_agent_name = scores[0][0] if scores else None

# Load and execute agent
if best_agent_name:
    agent = loader.load_agent(best_agent_name)
    result = agent.execute(context)
    print(result['output'])
```

## Available Agents

### Core Agents (5 Implemented)
1. **general-purpose** - Default agent with delegation capabilities
2. **root-cause-analyst** - Systematic debugging and investigation
3. **refactoring-expert** - Code quality improvement
4. **technical-writer** - Documentation generation
5. **performance-engineer** - Performance optimization

### Extended Agents (126 Available)
- system-architect
- backend-architect
- frontend-architect
- security-engineer
- devops-architect
- python-expert
- quality-engineer
- requirements-analyst
- socratic-mentor
- learning-guide
- ... and 116 more specialized agents

## Agent Selection

The system uses multi-factor scoring:
- **Triggers (40%)** - Keyword matching
- **Category (20%)** - Domain alignment
- **Description (15%)** - Task relevance
- **Tools (15%)** - Required capabilities
- **Focus Areas (10%)** - Specialization match

## Context Format

Agents accept context as either string or dictionary:

```python
# String context
context = "Debug authentication failure in login.py"

# Dictionary context (recommended)
context = {
    "task": "Debug authentication failure",
    "files": ["login.py", "auth.py"],
    "description": "Users can't login after deployment"
}
```

## Custom Agent Creation

### 1. Create Markdown Definition

Create `SuperClaude/Agents/my-agent.md`:

```markdown
---
name: my-agent
description: Agent for specific task
category: custom
tools:
  - Read
  - Write
  - Bash
triggers:
  - "my keyword"
  - "specific task"
---

## My Agent

### Behavioral Mindset
How the agent should think...

### Focus Areas
- Area 1: Description
- Area 2: Description

### Key Actions
1. First action
2. Second action
```

### 2. Optional: Create Python Implementation

For complex logic, create `SuperClaude/Agents/core/my_agent.py`:

```python
from ..base import BaseAgent

class MyAgent(BaseAgent):
    def execute(self, context):
        # Custom implementation
        return {
            'success': True,
            'output': 'Result',
            'actions_taken': ['Action 1', 'Action 2']
        }
```

## Delegation Pattern

The general-purpose agent can delegate to specialists:

```python
class GeneralPurposeAgent(BaseAgent):
    def execute(self, context):
        # Check if delegation needed
        if self._should_delegate(context):
            specialist = self._select_specialist(context)
            return specialist.execute(context)

        # Otherwise handle directly
        return self._execute_task(context)
```

## Cache Management

The loader uses LRU cache (10 agents, 1hr TTL):

```python
# Get cache statistics
stats = loader.get_cache_stats()
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")

# Clear cache if needed
loader.clear_cache()
```

## Testing

Run agent tests:
```bash
pytest tests/test_agents.py -v
```

## Troubleshooting

### Agent Not Found
- Check agent name matches markdown filename
- Ensure markdown has proper frontmatter
- Run registry discovery: `registry.discover_agents(force=True)`

### Low Selection Scores
- Add more specific triggers to agent markdown
- Ensure triggers match common keywords
- Check category alignment

### Encoding Errors
- Parser handles UTF-8 with latin-1 fallback
- Report persistent issues with specific files

## Future Enhancements (v5.0.0 Release)

- Visual agent selection UI
- Agent execution history
- Performance metrics tracking
- Advanced coordination patterns
- Agent capability evolution
- Real-time agent learning

## Support

For issues or questions:
- Check existing agents: `SuperClaude agent list`
- View agent details: `SuperClaude agent info <name>`
- Report issues: https://github.com/anthropics/superclaude/issues