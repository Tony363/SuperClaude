# SuperClaude Agent Framework

## Core Concept
Task agents are specialized sub-agents for complex operations. Use `--delegate` for automatic selection from ALL 131 agents (core + extended) or specify directly with `Task(agent-name)`.

## ⚠️ Critical Instructions

### Intelligence Maximization Rules
- Use parallel tool calls whenever possible to gather context quickly.
- Check dependencies first so you understand available libraries before coding.
- Follow existing patterns exactly to match established style and conventions.
- Consider edge cases, including error handling, null checks, and race conditions.
- Write testable code that can be exercised with unit tests.
- Never ship quick fixes or overengineering—prefer clean, maintainable solutions.

### Command Safety Rules
- Never run destructive or bulk-reset commands (`git checkout -- <path>`, `git reset --hard`, `git clean -fdx`, `rm -rf`, etc.) unless the user explicitly requests it for that path.
- Never use `git checkout`, `git restore`, or similar commands to revert tracked files unless explicitly directed for that file.
- Always consult `.claude/settings.json` before executing shell commands to honor any `denyList` or `askList` guardrails.
- Treat uncertainties as denials—ask the user if unsure whether a command is safe.
- Prefer targeted edits (e.g., `sed -n`, `apply_patch`) instead of repo-wide operations.
- Log potentially mutating commands in your reasoning so the safety rationale is clear.

### Current Context
- Current time: October 2025.
- Claude lacks real-time clock access; rely on explicit dates when relevant.

### Web Search Instructions (Critical)
- Built-in web search is disabled; use LinkUp via Rube MCP for all searches.
- Default to `depth: "deep"` and `output_type: "sourcedAnswer"`.
- Be proactive—look up library versions, API docs, security updates, error messages, and external service status when needed.

```json
// mcp__rube__RUBE_MULTI_EXECUTE_TOOL
{
  "tools": [{
    "tool_slug": "LINKUP_SEARCH",
    "arguments": {
      "query": "your search query here",
      "depth": "deep",
      "output_type": "sourcedAnswer"
    }
  }],
  "session_id": "WEB-SESSION-001",
  "memory": {},
  "sync_response_to_workbench": false,
  "thought": "Searching for [topic]",
  "current_step": "SEARCHING",
  "current_step_metric": {"completed": 0, "total": 1, "unit": "searches"},
  "next_step": "COMPLETE"
}
```

> Remember: your training data is static. LinkUp provides current information—use it liberally when details may have changed.

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

## CodeRabbit Review Loop
- **Signal blend**: SuperClaude correctness + completeness + test coverage are blended with CodeRabbit MCP scores (0.35/0.35/0.15/0.15 weights, auto-renormalised when CodeRabbit is missing).
- **Activation**: Export `CODERABBIT_REPO=org/name` and `CODERABBIT_PR_NUMBER=123` (or populate `context.results['coderabbit_repo|coderabbit_pr']`) to let the executor fetch reviews automatically. Secrets stay in `CODERABBIT_API_KEY` per `Config/coderabbit.yaml`.
- **Loop order**: Execute command → SuperClaude scoring → CodeRabbit review fetch → telemetry merge → blended score + thresholds → if below **production_ready** reroute fixes to specialists.
- **Degraded mode**: When CodeRabbit is down or missing config, telemetry records `coderabbit_status=degraded` and weights renormalise so SuperClaude signals still gate the run—no silent approvals.

### Taxonomy → Specialist Mapping
- **security** (`security`, `vulnerability`, `injection`) → `security-engineer`
- **performance** (`performance`, `latency`, `throughput`) → `performance-engineer`
- **style** (`style`, `formatting`, `lint`) → `refactoring-expert`
- **logic** (`logic`, `bug`, `correctness`) → `root-cause-analyst`

The executor aggregates CodeRabbit findings per taxonomy, builds improvement briefs (title, severity, file/line), and surfaces them in `context.results['coderabbit_briefs']`. Delegation heuristics read these briefs to auto-assign remediation Tasks before the command re-runs.

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
