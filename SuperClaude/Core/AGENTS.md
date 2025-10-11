# SuperClaude Agent Framework

## Core Concept
Task agents are specialized sub-agents for complex operations. Use `--delegate` for automatic selection from ALL 131 agents (core + extended) or specify directly with `Task(agent-name)`.

## 🚀 NEW: Unified Agent Registry
All agents now searchable through single registry with intelligent selection:
- **131 Total Agents**: 15 core + 116 extended specialists
- **Smart Selection**: `--delegate` now searches ALL agents based on context
- **Discovery Features**: Use `--suggest-agents` to see relevant specialists
- **Registry Location**: `agent_registry.yaml` with metadata for all agents

## Quality-Driven Execution
Every Task output gets a quality score (0-100):
- **90-100**: Production-ready → Accept
- **70-89**: Acceptable → Review notes
- **<70**: Needs improvement → Auto-iterate with specialist suggestion

## Agent Discovery & Selection

### New Discovery Flags
- `--suggest-agents`: Show top 5 relevant agents for current context
- `--agent-search [keyword]`: Find agents by capability
- `--delegate-extended`: Prefer extended agents over core
- `--why`: Explain why an agent was selected

### Automatic Context Detection
The framework now detects context and suggests appropriate specialists:
- **File Extensions**: `.rs` → rust-engineer, `.sol` → blockchain-developer
- **Imports**: `tensorflow` → ml-engineer, `react` → react-specialist
- **Keywords**: "kubernetes" → kubernetes-specialist, "payment" → fintech-engineer
- **Quality Escalation**: Core agent scores <70 → suggests specialist

## Agent Quick Reference

### Most Used Core Agents (Priority 1)
- **general-purpose**: Unknown scope, exploration
- **root-cause-analyst**: Debugging, error investigation
- **refactoring-expert**: Code improvements, cleanup
- **quality-engineer**: Test coverage, quality metrics
- **technical-writer**: Documentation generation
- **frontend-architect**: UI/UX, React, Vue, Angular
- **backend-architect**: APIs, servers, databases
- **security-engineer**: Vulnerability assessment
- **performance-engineer**: Optimization, bottlenecks
- **python-expert**: Python ecosystem mastery

### Popular Extended Specialists (Priority 2)
- **typescript-pro**: Advanced TypeScript patterns
- **rust-engineer**: Systems programming
- **kubernetes-specialist**: K8s orchestration
- **ml-engineer**: Machine learning models
- **blockchain-developer**: Web3 and smart contracts
- **react-specialist**: Modern React patterns
- **terraform-engineer**: Infrastructure as Code

## Usage Examples

### Let Framework Choose (Recommended)
```bash
# Searches ALL 131 agents based on context
--delegate

# See what agents would be selected
--suggest-agents

# Prefer specialists over generalists
--delegate-extended
```

### Direct Agent Invocation
```bash
# Core agent (simplified path)
Task(refactoring-expert)

# Extended agent (auto-resolved from registry)
Task(rust-engineer)  # No need for full path!
Task(kubernetes-specialist)  # Framework finds it

# Or use full path if preferred
Task(Extended/02-language-specialists/rust-engineer)
```

### Context-Aware Selection
```bash
# Working on Rust file
# Framework auto-suggests: rust-engineer

# Editing Kubernetes manifests
# Framework auto-suggests: kubernetes-specialist, terraform-engineer

# Machine learning project
# Framework auto-suggests: ml-engineer, data-engineer, python-pro
```

## Extended Agent Categories

The 116 extended agents are organized into specialized domains:

- **01-core-development**: APIs, mobile, microservices, UI/UX
- **02-language-specialists**: TypeScript, Rust, Go, React, Vue, Angular
- **03-infrastructure**: K8s, Terraform, Cloud, SRE, DevOps
- **04-quality-security**: Security audit, QA, performance, accessibility
- **05-data-ai**: ML, LLM, data pipelines, databases
- **06-developer-experience**: Build tools, CLI, refactoring, legacy code
- **07-specialized-domains**: Blockchain, gaming, IoT, fintech
- **08-business-product**: Product management, UX research, documentation
- **09-meta-orchestration**: Multi-agent coordination, workflows
- **10-research-analysis**: Market research, competitive analysis

See **AGENTS_EXTENDED.md** for complete category details and **agent_registry.yaml** for full metadata.

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
