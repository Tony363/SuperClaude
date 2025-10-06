# Extended Agent System Documentation

## Overview

The Extended Agent System provides dynamic loading and intelligent management of 141 specialized agents (14 core + 127 extended) with advanced capability matching and performance optimization.

## Architecture

### Component Hierarchy

```
ExtendedAgentLoader (Main Interface)
├── AgentMetadata Index (Lightweight, Always Loaded)
│   ├── 141 agent definitions
│   ├── 10 category indexes
│   └── Capability mappings
├── LRU Cache (Configurable Size)
│   ├── Recently used agents
│   ├── TTL-based expiration
│   └── Automatic eviction
└── Selection Engine
    ├── Multi-criteria scoring
    ├── Confidence classification
    └── Access pattern tracking
```

### Data Flow

```
User Request
    ↓
Context Analysis
    ↓
Agent Selection (Metadata Matching)
    ↓ (Top Candidates)
Lazy Loading (LRU Cache)
    ↓
Agent Initialization
    ↓
Execution
```

## Agent Categories

### 1. Core Development (01-core-development)
**Count:** ~10 agents
**Focus:** Fundamental development patterns, APIs, mobile, microservices

**Key Agents:**
- `api-designer` - REST/GraphQL API architecture
- `mobile-developer` - iOS, Android, React Native, Flutter
- `microservices-architect` - Distributed systems patterns
- `fullstack-developer` - End-to-end application development
- `ui-designer` - User interface and experience design

**Use When:** Building applications, designing APIs, mobile development

### 2. Language Specialists (02-language-specialists)
**Count:** ~22 agents
**Focus:** Language-specific expertise and frameworks

**Key Agents:**
- `typescript-pro` - Advanced TypeScript patterns
- `rust-engineer` - Memory-safe systems programming
- `golang-pro` - Concurrent Go programming
- `react-specialist` - Modern React patterns
- `vue-expert` - Vue 3 and Composition API
- `angular-architect` - Enterprise Angular patterns
- `spring-boot-engineer` - Java Spring Boot
- `django-developer` - Django web framework
- `dotnet-core-expert` - Modern .NET Core

**Use When:** Working with specific languages or frameworks

### 3. Infrastructure (03-infrastructure)
**Count:** ~12 agents
**Focus:** DevOps, cloud platforms, orchestration

**Key Agents:**
- `kubernetes-specialist` - K8s orchestration and Helm
- `terraform-engineer` - Infrastructure as Code
- `cloud-architect` - Multi-cloud solutions (AWS, GCP, Azure)
- `sre-engineer` - Site reliability and observability
- `devops-engineer` - CI/CD pipelines and automation

**Use When:** Infrastructure setup, cloud deployment, DevOps tasks

### 4. Quality & Security (04-quality-security)
**Count:** ~12 agents
**Focus:** Testing, security audits, code review, accessibility

**Key Agents:**
- `security-auditor` - Vulnerability assessment
- `qa-expert` - Test automation frameworks
- `code-reviewer` - Code quality analysis
- `accessibility-tester` - WCAG compliance
- `penetration-tester` - Security testing

**Use When:** Security audits, test automation, code reviews

### 5. Data & AI (05-data-ai)
**Count:** ~12 agents
**Focus:** Machine learning, data engineering, LLM architecture

**Key Agents:**
- `ml-engineer` - Machine learning model development
- `llm-architect` - Large language model systems
- `data-engineer` - Data pipeline architecture
- `database-optimizer` - Query performance optimization
- `mlops-engineer` - ML deployment and monitoring

**Use When:** ML projects, data pipelines, AI integration

### 6. Developer Experience (06-developer-experience)
**Count:** ~10 agents
**Focus:** DX optimization, tooling, refactoring, legacy modernization

**Key Agents:**
- `dx-optimizer` - Developer experience improvement
- `refactoring-specialist` - Code modernization
- `legacy-modernizer` - Legacy system updates
- `tooling-engineer` - Developer tools and automation
- `git-workflow-manager` - Git workflow optimization

**Use When:** Improving developer workflows, modernizing codebases

### 7. Specialized Domains (07-specialized-domains)
**Count:** ~11 agents
**Focus:** Domain-specific expertise (blockchain, gaming, IoT, fintech)

**Key Agents:**
- `blockchain-developer` - Smart contracts and DeFi
- `game-developer` - Game engines and physics
- `iot-engineer` - Embedded systems and sensors
- `fintech-engineer` - Financial systems and payments
- `embedded-systems` - Hardware integration

**Use When:** Specialized domain projects

### 8. Business & Product (08-business-product)
**Count:** ~11 agents
**Focus:** Business analysis, product management, content

**Key Agents:**
- `business-analyst` - Business requirements analysis
- `product-manager` - Product strategy and roadmaps
- `project-manager` - Project planning and execution
- `scrum-master` - Agile methodology
- `ux-researcher` - User research and testing

**Use When:** Business analysis, product planning, project management

### 9. Meta-Orchestration (09-meta-orchestration)
**Count:** ~8 agents
**Focus:** Multi-agent coordination, workflow orchestration

**Key Agents:**
- `multi-agent-coordinator` - Agent collaboration
- `workflow-orchestrator` - Complex workflow management
- `task-distributor` - Task delegation
- `context-manager` - Context preservation
- `performance-monitor` - System performance tracking

**Use When:** Complex multi-agent workflows, orchestration

### 10. Research & Analysis (10-research-analysis)
**Count:** ~6 agents
**Focus:** Research, competitive analysis, market intelligence

**Key Agents:**
- `research-analyst` - Technical research
- `competitive-analyst` - Competitive intelligence
- `market-researcher` - Market analysis
- `trend-analyst` - Industry trends
- `data-researcher` - Data-driven research

**Use When:** Research tasks, competitive analysis, market intelligence

## Usage Examples

### Basic Agent Loading

```python
from SuperClaude.Agents.extended_loader import ExtendedAgentLoader

# Initialize loader
loader = ExtendedAgentLoader(
    cache_size=20,  # Keep 20 agents in memory
    ttl_seconds=1800  # 30 minute TTL
)

# Load specific agent
agent = loader.load_agent('typescript-pro')

# Execute task
result = agent.execute({
    'task': 'Refactor this code to use TypeScript generics',
    'code': '...'
})
```

### Intelligent Agent Selection

```python
# Define task context
context = {
    'task': 'Build a REST API with authentication and rate limiting',
    'files': ['api.py', 'auth.py', 'models.py'],
    'languages': ['python'],
    'domains': ['api', 'backend', 'security'],
    'keywords': ['rest', 'authentication', 'rate-limit']
}

# Get top 5 agent suggestions
matches = loader.select_agent(context, top_n=5)

# Best match
best = matches[0]
print(f"Suggested: {best.agent_id}")
print(f"Confidence: {best.confidence}")
print(f"Score: {best.total_score:.3f}")

# Load and execute
agent = loader.load_agent(best.agent_id)
result = agent.execute(context)
```

### Category-Based Selection

```python
from SuperClaude.Agents.extended_loader import AgentCategory

# Filter to infrastructure agents
context = {
    'task': 'Set up Kubernetes deployment with Helm charts',
    'domains': ['kubernetes', 'devops'],
    'keywords': ['k8s', 'helm', 'deployment']
}

matches = loader.select_agent(
    context,
    category_hint=AgentCategory.INFRASTRUCTURE,
    top_n=3
)

# Will prioritize kubernetes-specialist, devops-engineer, etc.
```

### Search and Discovery

```python
# Search by keyword
results = loader.search_agents('graphql')
for agent in results:
    print(f"{agent.id}: {agent.name}")

# Get all agents in category
agents = loader.get_agents_by_category(AgentCategory.DATA_AI)
for agent in agents:
    print(f"{agent.name} - {agent.description}")

# List categories
categories = loader.list_categories()
for category, count in categories.items():
    print(f"{category.value}: {count} agents")
```

### Explanation and Debugging

```python
# Get detailed explanation of why an agent was selected
explanation = loader.explain_selection('react-specialist', context)

print(f"Agent: {explanation['agent_name']}")
print(f"Confidence: {explanation['confidence']}")
print(f"\nScore Breakdown:")
for component, score in explanation['breakdown'].items():
    print(f"  {component}: {score:.3f}")

print(f"\nMatched Criteria:")
for criterion in explanation['matched_criteria']:
    print(f"  • {criterion}")
```

### Performance Optimization

```python
# Preload frequently used agents
loader.preload_top_agents(count=10)

# Optimize cache based on access patterns
loader.optimize_cache()

# Get statistics
stats = loader.get_statistics()
print(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
print(f"Average load time: {stats['avg_load_time']:.3f}s")
print(f"Total agents: {stats['total_agents']}")
```

## CLI Interface

### Installation

```bash
# Make CLI executable
chmod +x SuperClaude/Agents/cli.py

# Create alias (optional)
alias agent-cli="python -m SuperClaude.Agents.cli"
```

### Commands

```bash
# List all agents
python -m SuperClaude.Agents.cli list

# List agents in specific category
python -m SuperClaude.Agents.cli list --category 02-language-specialists

# Show all categories
python -m SuperClaude.Agents.cli categories

# Search for agents
python -m SuperClaude.Agents.cli search "kubernetes"

# Select best agent for task
python -m SuperClaude.Agents.cli select \
  --task "Build GraphQL API with authentication" \
  --languages python graphql \
  --domains api backend \
  --files api.py schema.graphql \
  --top 5

# Show agent details
python -m SuperClaude.Agents.cli info api-designer

# Show statistics
python -m SuperClaude.Agents.cli stats

# Show category tree
python -m SuperClaude.Agents.cli tree
```

## Scoring Algorithm

### Multi-Criteria Matching

Agent selection uses weighted scoring across multiple dimensions:

```
Total Score = (Keywords × 30%)
            + (Domains × 25%)
            + (Languages × 20%)
            + (File Patterns × 15%)
            + (Import Patterns × 10%)
            + (Priority Bonus: up to 10%)
```

### Confidence Levels

- **Excellent** (≥80%): Very strong match across multiple criteria
- **High** (60-79%): Strong match with some criteria
- **Medium** (40-59%): Moderate match, suitable but not ideal
- **Low** (<40%): Weak match, consider alternatives

### Priority System

- **Priority 1** (Core Agents): +10% bonus - Always preferred for general tasks
- **Priority 2** (Common Extended): +6.67% bonus - Specialized but frequently used
- **Priority 3** (Specialized): +3.33% bonus - Domain-specific experts

## Performance Characteristics

### Memory Usage

```
Metadata Index:   ~500KB (always loaded)
Cached Agent:     ~50-100KB per agent
20-agent cache:   ~1-2MB total
```

### Load Times

```
Metadata Load:    ~50ms (one-time on initialization)
Agent Load:       ~10-50ms (cold load)
Cache Hit:        <1ms
```

### Cache Optimization

- **LRU Eviction**: Least recently used agents are evicted when cache is full
- **TTL Expiration**: Agents expire after TTL to ensure fresh loading
- **Access Tracking**: Monitors usage patterns for intelligent preloading
- **Automatic Optimization**: Adjusts cache based on access frequency

## Integration Patterns

### With Agent Registry

```python
from SuperClaude.Agents.registry import AgentRegistry
from SuperClaude.Agents.extended_loader import ExtendedAgentLoader

# Use custom registry
registry = AgentRegistry(agents_dir=Path('/custom/agents'))
loader = ExtendedAgentLoader(registry=registry)
```

### With Task Management

```python
class TaskManager:
    def __init__(self):
        self.loader = ExtendedAgentLoader()

    def execute_task(self, task_description: str, context: dict):
        # Enhance context
        full_context = {
            'task': task_description,
            **context
        }

        # Select best agent
        matches = self.loader.select_agent(full_context, top_n=1)
        if not matches:
            return None

        # Load and execute
        agent = self.loader.load_agent(matches[0].agent_id)
        return agent.execute(full_context)
```

### With Orchestration

```python
class AgentOrchestrator:
    def __init__(self):
        self.loader = ExtendedAgentLoader(cache_size=30)

    def multi_agent_task(self, subtasks: list):
        results = []

        for subtask in subtasks:
            # Select specialized agent for each subtask
            matches = self.loader.select_agent(subtask['context'])
            agent = self.loader.load_agent(matches[0].agent_id)
            result = agent.execute(subtask['context'])
            results.append(result)

        return self.synthesize_results(results)
```

## Best Practices

### 1. Context Design

Provide rich context for better matching:

```python
# Good - Rich context
context = {
    'task': 'Optimize database queries and add indexes',
    'files': ['models.py', 'migrations/001_add_indexes.sql'],
    'languages': ['python', 'sql'],
    'domains': ['database', 'performance'],
    'keywords': ['optimize', 'query', 'index', 'performance'],
    'imports': ['sqlalchemy', 'django.db']
}

# Less optimal - Minimal context
context = {
    'task': 'Fix database'
}
```

### 2. Cache Configuration

Adjust cache size based on your workload:

```python
# Development: Small cache for quick iterations
loader = ExtendedAgentLoader(cache_size=5, ttl_seconds=300)

# Production: Larger cache for performance
loader = ExtendedAgentLoader(cache_size=30, ttl_seconds=3600)

# High-throughput: Very large cache
loader = ExtendedAgentLoader(cache_size=50, ttl_seconds=7200)
```

### 3. Periodic Optimization

```python
# Optimize cache every hour
import schedule

def optimize():
    loader.optimize_cache()
    stats = loader.get_statistics()
    logger.info(f"Cache optimized. Hit rate: {stats['cache_hit_rate']:.1%}")

schedule.every(1).hour.do(optimize)
```

### 4. Monitoring

```python
# Track performance metrics
stats = loader.get_statistics()

if stats['cache_hit_rate'] < 0.5:
    logger.warning("Low cache hit rate. Consider increasing cache size.")

if stats['avg_load_time'] > 0.1:
    logger.warning("High average load time. Check agent initialization.")
```

## Troubleshooting

### Agent Not Found

```python
agent = loader.load_agent('nonexistent-agent')
# Returns None

# Check if agent exists in metadata
if 'nonexistent-agent' in loader._agent_metadata:
    print("Agent exists but failed to load")
else:
    print("Agent not in registry")
```

### Poor Selection Results

```python
# Enable debug logging
import logging
logging.getLogger('agent.extended_loader').setLevel(logging.DEBUG)

# Get detailed explanation
matches = loader.select_agent(context, top_n=5)
for match in matches:
    explanation = loader.explain_selection(match.agent_id, context)
    print(explanation)
```

### Memory Issues

```python
# Reduce cache size
loader.cache_size = 10

# Clear cache periodically
loader.clear_cache()

# Monitor memory
import psutil
process = psutil.Process()
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

## Advanced Topics

### Custom Scoring Weights

Modify `_calculate_match_score` to adjust component weights:

```python
# Example: Prioritize file patterns over keywords
breakdown['keywords'] = keyword_score * 0.20  # Reduced from 0.30
breakdown['file_patterns'] = file_pattern_score * 0.25  # Increased from 0.15
```

### Extension Points

1. **Custom Matchers**: Add new matching criteria
2. **Scoring Algorithms**: Implement alternative scoring methods
3. **Cache Strategies**: Replace LRU with custom eviction
4. **Preloading Rules**: Define custom preload strategies

### Performance Tuning

```python
# Batch loading
agent_ids = ['agent1', 'agent2', 'agent3']
agents = [loader.load_agent(aid) for aid in agent_ids]

# Async loading (with asyncio)
import asyncio

async def load_async(agent_id):
    return await asyncio.to_thread(loader.load_agent, agent_id)

agents = await asyncio.gather(*[load_async(aid) for aid in agent_ids])
```

## Future Enhancements

- [ ] Distributed caching with Redis
- [ ] Agent capability learning from usage patterns
- [ ] Multi-agent collaboration scoring
- [ ] Dynamic agent composition
- [ ] Context-aware preloading
- [ ] Performance profiling per agent
- [ ] A/B testing for selection algorithms

## References

- [Agent Registry YAML](../SuperClaude/Core/agent_registry.yaml)
- [Base Agent Interface](../SuperClaude/Agents/base.py)
- [Agent Parser](../SuperClaude/Agents/parser.py)
- [Test Suite](../tests/test_extended_loader.py)
