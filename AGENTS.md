# SuperClaude Agent Framework

## Core Concept
Task agents are specialized sub-agents for complex operations. Use `--delegate` for automatic selection or specify directly with `Task(agent-name)`.

## Quality-Driven Execution
Every Task output gets a quality score (0-100):
- **90-100**: Production-ready → Accept
- **70-89**: Acceptable → Review notes
- **<70**: Needs improvement → Auto-iterate

## Agent Quick Reference

See **TOOLS.md** for complete agent list and selection guide.

### Most Used Agents
- **general-purpose**: Unknown scope, exploration
- **root-cause-analyst**: Debugging, error investigation
- **refactoring-expert**: Code improvements, cleanup
- **quality-engineer**: Test coverage, quality metrics
- **technical-writer**: Documentation generation

## Extended Agent Library

For specialized needs beyond the 15 core agents:

### 📚 100+ Production-Ready Agents
- **Location**: `Agents/Extended/` directory
- **Organization**: 10 categories covering all development domains
- **Documentation**: See `AGENTS_EXTENDED.md` for quick discovery
- **Usage**: Same Task() interface, just specify path

### When to Use Extended Agents
- **Core agents** (15): Daily tasks, quick access, general purpose
- **Extended agents** (100+): Specialized expertise, specific technologies

### Quick Access Examples
```bash
# Core agent (simplified path)
Task(refactoring-expert)

# Extended agent (category path)
Task(Extended/02-language-specialists/rust-engineer)
Task(Extended/03-infrastructure/kubernetes-specialist)
```

### Popular Extended Categories
- `02-language-specialists/`: TypeScript, Rust, Go, Python experts
- `03-infrastructure/`: K8s, Terraform, Cloud, DevOps
- `05-data-ai/`: ML, LLM, Data Engineering
- `07-specialized-domains/`: Blockchain, IoT, FinTech

See **AGENTS_EXTENDED.md** for complete category guide and agent discovery.

## Context Package
Every delegation includes:
```yaml
context:
  goal: "What to achieve"
  constraints: ["limits", "requirements"]
  prior_work: {previous results}
  quality_criteria: {min_score: 70}
```

## Iteration Pattern
```
1. Delegate → Task(agent, context)
2. Evaluate → score = quality(output)  
3. Iterate → if score < 70: retry with feedback
4. Accept → when score ≥ 70
```

## Best Practices

### DO
- ✅ Always evaluate quality scores
- ✅ Preserve context across iterations
- ✅ Use specialist agents over general-purpose
- ✅ Let quality drive iterations

### DON'T
- ❌ Accept low-quality outputs
- ❌ Lose context between delegations
- ❌ Exceed iteration limits without permission

## Integration with Flags

| Flag | Effect on Agents |
|------|------------------|
| `--delegate` | Auto-select best agent |
| `--loop [n]` | Set max iterations |
| `--think [1-3]` | Analysis depth |
| `--safe-mode` | Conservative execution |

## Example Workflow

```bash
# Complex debugging
--think 2 --delegate
→ Uses root-cause-analyst
→ Quality: 65/100
→ Auto-iterates with feedback
→ Quality: 88/100 ✅

# Refactoring with safety
--delegate --safe-mode --loop 5
→ Uses refactoring-expert
→ Maximum validation
→ Up to 5 iterations
```