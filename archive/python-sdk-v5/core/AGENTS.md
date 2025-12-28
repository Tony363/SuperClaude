# SuperClaude Agent Framework

## Core Concept
Task agents are specialized sub-agents for complex operations. Use `--delegate` for automatic selection from ALL 131 agents (core + extended) or specify directly with `Task(agent-name)`.

## Unified Agent Registry
- **131 Total Agents**: 15 core + 116 extended specialists
- **Smart Selection**: `--delegate` searches ALL agents based on context
- **Registry Location**: `agent_registry.yaml`

## Quality-Driven Execution
Every Task output gets a quality score (0-100):
- **90-100**: Production-ready → Accept
- **70-89**: Acceptable → Review notes
- **<70**: Needs improvement → Auto-iterate with specialist suggestion

---

## Agent Discovery & Selection

### Discovery Flags
| Flag | Purpose |
|------|---------|
| `--delegate` | Auto-select best agent from all 131 |
| `--suggest-agents` | Show top 5 relevant agents for context |
| `--agent-search [keyword]` | Search agents by capability |
| `--delegate-extended` | Prefer specialists over generalists |
| `--why` | Explain agent selection reasoning |
| `--stick-to-core` | Use only core agents |

### Automatic Context Detection
| Context | Auto-Selected Agent |
|---------|-------------------|
| `.rs` file | rust-engineer |
| `.tsx` with React imports | react-specialist |
| `Dockerfile` present | devops-architect |
| `.sol` smart contract | blockchain-developer |
| ML notebook `.ipynb` | ml-engineer |
| `terraform.tf` files | terraform-engineer |
| API performance issues | performance-engineer |
| Security vulnerabilities | security-auditor |

---

## Core Agents (15)

### Most Used (Priority 1)
| Agent | Use For |
|-------|---------|
| **general-purpose** | Unknown scope, exploration |
| **root-cause-analyst** | Debugging, error investigation |
| **refactoring-expert** | Code improvements, cleanup |
| **quality-engineer** | Test coverage, quality metrics |
| **technical-writer** | Documentation generation |
| **frontend-architect** | UI/UX, React, Vue, Angular |
| **backend-architect** | APIs, servers, databases |
| **security-engineer** | Vulnerability assessment |
| **performance-engineer** | Optimization, bottlenecks |
| **python-expert** | Python ecosystem mastery |

### Additional Core Agents
- **system-architect** - System design, scalability
- **requirements-analyst** - Feature analysis, PRD breakdown
- **socratic-mentor** - Teaching through questions
- **learning-guide** - Tutorials, educational content
- **devops-architect** - Infrastructure, CI/CD

---

## Extended Agent Library (116)

### Categories Overview

| Category | Count | Focus |
|----------|-------|-------|
| **01-core-development** | 14 | APIs, mobile, microservices, UI/UX |
| **02-language-specialists** | 26 | TypeScript, Rust, Go, React, Vue, Angular |
| **03-infrastructure** | 12 | K8s, Terraform, Cloud, SRE, DevOps |
| **04-quality-security** | 12 | Security audit, QA, performance, accessibility |
| **05-data-ai** | 12 | ML, LLM, data pipelines, databases |
| **06-developer-experience** | 10 | Build tools, CLI, refactoring, legacy code |
| **07-specialized-domains** | 11 | Blockchain, gaming, IoT, fintech |
| **08-business-product** | 10 | Product management, UX research, docs |
| **09-meta-orchestration** | 8 | Multi-agent coordination, workflows |
| **10-research-analysis** | 6 | Market research, competitive analysis |

### Top 20 Extended Agents
1. **typescript-pro** - Advanced TypeScript patterns
2. **python-pro** - Python ecosystem expert
3. **react-specialist** - Modern React patterns
4. **kubernetes-specialist** - K8s orchestration
5. **rust-engineer** - Systems programming
6. **golang-pro** - Go concurrency
7. **ml-engineer** - Machine learning
8. **cloud-architect** - Multi-cloud design
9. **security-auditor** - Security assessment
10. **nextjs-developer** - Full-stack Next.js
11. **vue-expert** - Vue 3 expertise
12. **terraform-engineer** - IaC expert
13. **blockchain-developer** - Web3 development
14. **qa-expert** - Test automation
15. **devops-engineer** - CI/CD pipelines
16. **database-optimizer** - Query optimization
17. **api-designer** - REST/GraphQL APIs
18. **mobile-developer** - Cross-platform mobile
19. **microservices-architect** - Distributed systems
20. **technical-writer** - Documentation expert

---

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
# Core agent
Task(refactoring-expert)

# Extended agent (auto-resolved from registry)
Task(rust-engineer)           # No need for full path!
Task(kubernetes-specialist)   # Framework finds it

# Or use full path if preferred
Task(Extended/02-language-specialists/rust-engineer)
```

### Quality-Based Escalation
```
Initial: Task(general-purpose)
Quality: 65/100
Auto-suggest: "Try rust-engineer for Rust expertise"
Retry: Task(rust-engineer)
Quality: 92/100 ✅
```

---

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

## Integration with Flags

| Flag | Effect on Agents |
|------|------------------|
| `--delegate` | Auto-select best agent |
| `--loop [n]` | Set max iterations |
| `--think [1-3]` | Analysis depth |
| `--safe-mode` | Conservative execution |

## Best Practices

### DO
- Use `--delegate` for automatic selection
- Evaluate quality scores on every output
- Preserve context across iterations
- Use specialist agents over general-purpose when domain-specific

### DON'T
- Accept outputs with score < 70
- Lose context between delegations
- Exceed iteration limits without permission
