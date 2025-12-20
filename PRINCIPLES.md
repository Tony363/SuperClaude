# SuperClaude Design Principles

These principles guide the development and operation of the SuperClaude framework.

## 1. Safety First

### Hard Limits Are Inviolable
- `HARD_MAX_ITERATIONS = 5` cannot be overridden
- Security-critical findings always cap quality scores
- Destructive operations require explicit confirmation

### Deterministic Grounding
Quality assessments are grounded in verifiable facts, not LLM self-evaluation:
- Test results directly impact scores
- Security scan findings enforce hard caps
- Build status gates production readiness

### Fail Safe
When uncertain:
- Default to safer options
- Ask for clarification rather than assume
- Preserve original state when changes fail

## 2. Transparency

### Visible Progress
- Use TodoWrite for complex tasks
- Report quality scores with explanations
- Show validation results

### Traceable Decisions
- Log execution paths
- Record quality assessments
- Preserve evidence in `.superclaude_metrics/`

### Honest Assessment
- Report actual test results, not expectations
- Acknowledge limitations
- Flag degraded modes clearly

## 3. Quality Over Speed

### Iterate Until Right
The `--loop` flag enables iteration until quality thresholds are met:
1. Execute implementation
2. Run validation
3. Score quality
4. Iterate if below threshold
5. Stop on success, oscillation, or max iterations

### Validation Gates
Every stage can halt the pipeline:
- Syntax errors are fatal
- Security critical/high issues are fatal
- Test failures are fatal

### Evidence-Based
Claims require backing:
- Generated code must be validated
- Quality scores must have evidence
- Recommendations must cite findings

## 4. Composability

### Agent Specialization
131 agents, each with focused expertise:
- Domain knowledge (backend, frontend, data, etc.)
- Language specialization (Python, TypeScript, Rust, etc.)
- Task type (analysis, implementation, testing)

### Command Orthogonality
Commands compose with flags:
```bash
/sc:implement --loop --pal-review --with-tests "feature"
```

### MCP Integration
External capabilities via MCP servers:
- PAL for consensus and review
- Rube for 500+ app integrations
- LinkUp for current information

## 5. Efficiency

### Lazy Loading
- Agents loaded on demand
- Commands discovered dynamically
- LRU caching for performance

### Parallel Execution
- Independent tasks run concurrently
- Worktrees enable isolated changes
- Batch operations where possible

### Token Awareness
- Token efficiency mode for context constraints
- Compressed output symbols
- Progressive detail levels

## 6. Extensibility

### File-Driven Configuration
- Agents defined in markdown
- Commands specified via YAML frontmatter
- Quality weights configurable

### Plugin Architecture
- Custom agents in `Agents/Extended/`
- Custom commands in `Commands/`
- Custom validation stages

### Open Integration
- MCP server support
- API client abstraction
- Provider-agnostic routing

## 7. Developer Experience

### Intuitive Commands
Clear `/sc:` prefix with predictable behavior:
- `/sc:implement` - make changes
- `/sc:test` - validate changes
- `/sc:analyze` - understand code
- `/sc:design` - plan architecture

### Helpful Defaults
Sensible defaults that can be overridden:
- MAX_ITERATIONS = 3 (can increase to 5)
- Quality threshold = 70 (configurable)
- Auto-detect test frameworks

### Clear Feedback
- Quality scores with band labels
- Termination reasons explained
- Improvement suggestions provided

## 8. Maintainability

### Single Source of Truth
Configuration should not drift:
- One definition per concept
- Generated docs from code
- Consistent naming

### Modular Architecture
Clear separation of concerns:
- Agents handle domain logic
- Commands orchestrate workflows
- Quality validates output
- Telemetry records evidence

### Test Coverage
Every feature should be testable:
- Unit tests for components
- Integration tests for workflows
- Benchmark suite for performance
