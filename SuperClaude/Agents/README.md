# SuperClaude Agent System

## Overview

The SuperClaude Agent System provides a comprehensive 141-agent framework for specialized task execution with intelligent selection, lazy loading, and performance optimization.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent System                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Registry   │───▶│   Selector   │───▶│    Loader    │ │
│  │              │    │              │    │              │ │
│  │  - Discovery │    │  - Scoring   │    │  - Caching   │ │
│  │  - Catalog   │    │  - Matching  │    │  - Loading   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         ExtendedAgentLoader (141 agents)             │  │
│  │                                                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐   │  │
│  │  │  Metadata  │  │  LRU Cache │  │  Selection │   │  │
│  │  │   Index    │  │  (20 max)  │  │   Engine   │   │  │
│  │  └────────────┘  └────────────┘  └────────────┘   │  │
│  │                                                      │  │
│  │  • 10 categories                                    │  │
│  │  • Multi-criteria scoring                           │  │
│  │  • Access pattern tracking                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Base Agent (`base.py`)
Abstract base class defining the agent interface.

```python
from SuperClaude.Agents import BaseAgent

class CustomAgent(BaseAgent):
    def initialize(self) -> bool:
        # Setup logic
        return True

    def execute(self, context: dict):
        # Execution logic
        return {"result": "success"}
```

### 2. Agent Registry (`registry.py`)
Discovers and catalogs agents from markdown definitions.

```python
from SuperClaude.Agents import AgentRegistry

registry = AgentRegistry()
registry.discover_agents()

# Get agent configuration
config = registry.get_agent_config('python-expert')
```

### 3. Agent Selector (`selector.py`)
Intelligent agent selection based on context.

```python
from SuperClaude.Agents import AgentSelector

selector = AgentSelector()
best_agent, confidence = selector.find_best_match(
    context="Debug Python API performance issue",
    category_hint="debugging"
)
```

### 4. Agent Loader (`loader.py`)
Basic agent loading with LRU caching.

```python
from SuperClaude.Agents import AgentLoader

loader = AgentLoader(cache_size=10)
agent = loader.load_agent('root-cause-analyst')
```

### 5. Extended Agent Loader (`extended_loader.py`)
**PRIMARY INTERFACE** - Advanced loader for 141-agent system.

```python
from SuperClaude.Agents import ExtendedAgentLoader, AgentCategory

loader = ExtendedAgentLoader(cache_size=20, ttl_seconds=1800)

# Intelligent selection
context = {
    'task': 'Build REST API with authentication',
    'files': ['api.py', 'auth.py'],
    'languages': ['python'],
    'domains': ['api', 'backend'],
    'keywords': ['rest', 'authentication']
}

matches = loader.select_agent(context, top_n=5)
best = matches[0]

# Load and execute
agent = loader.load_agent(best.agent_id)
result = agent.execute(context)
```

## Agent Categories

| Category | Count | Focus Area |
|----------|-------|------------|
| **01-core-development** | ~10 | APIs, mobile, microservices |
| **02-language-specialists** | ~22 | Language experts (TS, Rust, Go, etc.) |
| **03-infrastructure** | ~12 | DevOps, cloud, Kubernetes |
| **04-quality-security** | ~12 | Testing, security, code review |
| **05-data-ai** | ~12 | ML, data engineering, LLMs |
| **06-developer-experience** | ~10 | DX, tooling, refactoring |
| **07-specialized-domains** | ~11 | Blockchain, gaming, IoT, fintech |
| **08-business-product** | ~11 | Business analysis, PM |
| **09-meta-orchestration** | ~8 | Multi-agent coordination |
| **10-research-analysis** | ~6 | Research, competitive analysis |

## Quick Start

### Basic Usage

```python
from SuperClaude.Agents import ExtendedAgentLoader

# Initialize
loader = ExtendedAgentLoader()

# Load specific agent
agent = loader.load_agent('typescript-pro')

# Execute task
result = agent.execute({
    'task': 'Refactor to use TypeScript generics',
    'code': '...'
})
```

### Intelligent Selection

```python
# Define rich context
context = {
    'task': 'Optimize database queries and add indexes',
    'files': ['models.py', 'migrations/001_add_indexes.sql'],
    'languages': ['python', 'sql'],
    'domains': ['database', 'performance'],
    'keywords': ['optimize', 'query', 'index'],
    'imports': ['sqlalchemy', 'django.db']
}

# Get suggestions
matches = loader.select_agent(context, top_n=5)

# Use best match
best = matches[0]
print(f"Selected: {best.agent_id}")
print(f"Confidence: {best.confidence}")
print(f"Score: {best.total_score:.3f}")

agent = loader.load_agent(best.agent_id)
```

### Category Filtering

```python
from SuperClaude.Agents import AgentCategory

# Infrastructure-only
matches = loader.select_agent(
    context,
    category_hint=AgentCategory.INFRASTRUCTURE,
    top_n=3
)
```

### Search and Discovery

```python
# Search by keyword
results = loader.search_agents('react')

# List category
agents = loader.get_agents_by_category(AgentCategory.DATA_AI)

# Show categories
categories = loader.list_categories()
```

## CLI Interface

### Installation

```bash
# Make executable
chmod +x SuperClaude/Agents/cli.py

# Run commands
python -m SuperClaude.Agents.cli --help
```

### Commands

```bash
# List all agents
python -m SuperClaude.Agents.cli list

# Filter by category
python -m SuperClaude.Agents.cli list --category 02-language-specialists

# Search
python -m SuperClaude.Agents.cli search "kubernetes"

# Select best agent
python -m SuperClaude.Agents.cli select \
  --task "Build GraphQL API" \
  --languages python graphql \
  --domains api backend \
  --top 5

# Show agent info
python -m SuperClaude.Agents.cli info api-designer

# Statistics
python -m SuperClaude.Agents.cli stats

# Category tree
python -m SuperClaude.Agents.cli tree
```

## Performance

### Characteristics

```
Metadata Load:    ~50ms (one-time)
Agent Load:       ~10-50ms (cold)
Cache Hit:        <1ms
Memory per Agent: ~50-100KB
20-agent cache:   ~1-2MB
```

### Optimization

```python
# Preload frequently used agents
loader.preload_top_agents(count=10)

# Optimize cache based on patterns
loader.optimize_cache()

# Monitor performance
stats = loader.get_statistics()
print(f"Hit rate: {stats['cache_hit_rate']:.1%}")
print(f"Avg load: {stats['avg_load_time']:.3f}s")
```

## Scoring Algorithm

### Multi-Criteria Matching

```
Total Score = (Keywords × 30%)
            + (Domains × 25%)
            + (Languages × 20%)
            + (File Patterns × 15%)
            + (Import Patterns × 10%)
            + (Priority Bonus: up to 10%)
```

### Confidence Levels

- **Excellent** (≥80%): Very strong match
- **High** (60-79%): Strong match
- **Medium** (40-59%): Moderate match
- **Low** (<40%): Weak match

## Examples

See [`examples/extended_agent_usage.py`](../../examples/extended_agent_usage.py) for comprehensive examples:

1. Basic agent loading
2. Intelligent selection
3. Category filtering
4. Search and discovery
5. Detailed explanations
6. Performance optimization
7. Multi-agent workflows
8. Category exploration

## Testing

```bash
# Run tests
python -m pytest tests/test_extended_loader.py -v

# With coverage
python -m pytest tests/test_extended_loader.py --cov=SuperClaude.Agents --cov-report=html
```

## Documentation

- [Extended Agent System Guide](../../docs/EXTENDED_AGENT_SYSTEM.md) - Comprehensive documentation
- [Agent Registry YAML](../Core/agent_registry.yaml) - Agent definitions
- [Usage Examples](../../examples/extended_agent_usage.py) - Code examples

## Integration

### With Task Management

```python
class TaskManager:
    def __init__(self):
        self.loader = ExtendedAgentLoader()

    def execute(self, task: str, context: dict):
        full_context = {'task': task, **context}
        matches = self.loader.select_agent(full_context, top_n=1)

        if matches:
            agent = self.loader.load_agent(matches[0].agent_id)
            return agent.execute(full_context)
```

### With Orchestration

```python
class Orchestrator:
    def __init__(self):
        self.loader = ExtendedAgentLoader(cache_size=30)

    def multi_step(self, steps: list):
        results = []
        for step in steps:
            matches = self.loader.select_agent(step['context'])
            agent = self.loader.load_agent(matches[0].agent_id)
            results.append(agent.execute(step['context']))
        return results
```

## Best Practices

### 1. Rich Context

```python
# Good
context = {
    'task': 'Clear task description',
    'files': ['relevant', 'files'],
    'languages': ['used', 'languages'],
    'domains': ['relevant', 'domains'],
    'keywords': ['specific', 'keywords'],
    'imports': ['library', 'names']
}

# Less optimal
context = {'task': 'Do something'}
```

### 2. Cache Configuration

```python
# Development
loader = ExtendedAgentLoader(cache_size=5, ttl_seconds=300)

# Production
loader = ExtendedAgentLoader(cache_size=30, ttl_seconds=3600)
```

### 3. Monitoring

```python
import logging
logging.getLogger('agent.extended_loader').setLevel(logging.DEBUG)

stats = loader.get_statistics()
if stats['cache_hit_rate'] < 0.5:
    logger.warning("Low cache hit rate")
```

## Troubleshooting

### Agent Not Found

```python
agent = loader.load_agent('nonexistent')
# Returns None

# Check existence
if 'nonexistent' in loader._agent_metadata:
    print("Exists but failed to load")
```

### Poor Selection

```python
# Enable debug logging
import logging
logging.getLogger('agent').setLevel(logging.DEBUG)

# Get explanation
explanation = loader.explain_selection(agent_id, context)
print(explanation)
```

### Memory Issues

```python
# Reduce cache
loader.cache_size = 10

# Clear cache
loader.clear_cache()
```

## Contributing

To add a new agent:

1. Create markdown file in appropriate Extended category directory
2. Include YAML frontmatter with agent metadata
3. Add to `agent_registry.yaml`
4. Run tests to validate

Example:

```markdown
---
name: custom-agent
description: Brief description
tools: Read, Write, Bash
---

You are a specialized agent...

## Triggers
- trigger keywords
- activation phrases

## Focus Areas
- **Area 1**: Description
- **Area 2**: Description
```

## License

MIT License - See [LICENSE](../../LICENSE) for details.

## Support

- Issues: [GitHub Issues](https://github.com/superclaud/framework/issues)
- Documentation: [Extended Agent System Guide](../../docs/EXTENDED_AGENT_SYSTEM.md)
- Examples: [Usage Examples](../../examples/extended_agent_usage.py)
