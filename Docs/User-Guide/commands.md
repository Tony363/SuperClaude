# Command Catalogue

The table below summarizes all 13 `/sc:*` commands available in SuperClaude v6.0.0.

## Complete Command Reference

| Command | Purpose | Key Artefacts |
|---------|---------|---------------|
| `/sc:analyze` | Perform static analysis and risk assessment | Risk summary, metrics, findings |
| `/sc:brainstorm` | Creative ideation and exploration | Ideas list, concept map |
| `/sc:build` | Project building and compilation | Build logs, artifacts |
| `/sc:design` | Architecture and system design | Diagrams, ADRs, design docs |
| `/sc:document` | Generate summaries, guides, or documentation | Markdown/MDX under `SuperClaude/Implementation/` |
| `/sc:estimate` | Effort and resource estimation | Breakdown, risk assessment |
| `/sc:explain` | Code/concept explanation | Detailed explanations |
| `/sc:git` | Git operations (commit, PR, branch) | Commits, PRs, branches |
| `/sc:implement` | Plan and apply code changes with guardrails | `SuperClaude/Implementation/`, metrics, diffs |
| `/sc:improve` | Refine existing modules (refactoring) | Updated files, plan summary |
| `/sc:index` | Search and indexing operations | Index data, search results |
| `/sc:test` | Run project tests with coverage | Test logs, metrics, exit status |
| `/sc:workflow` | Expand PRD/spec into actionable steps | Markdown plan under `SuperClaude/Implementation/` |

## Command Details

### `/sc:analyze`
Perform deep code analysis including complexity metrics, dependency analysis, and risk assessment.

**Flags:**
- `--deep`: Enable comprehensive analysis
- `--risk`: Focus on risk assessment
- `--dependencies`: Analyze dependency graph
- `--complexity`: Calculate complexity metrics
- `--agent <name>`: Use specific analysis agent

**Example:**
```bash
/sc:analyze --deep --risk src/auth/
```

### `/sc:brainstorm`
Creative ideation mode for exploring solutions and generating ideas.

**Flags:**
- `--divergent`: Maximize idea generation
- `--converge`: Focus on best options
- `--constraints <list>`: Apply constraints

**Example:**
```bash
/sc:brainstorm --divergent "API authentication approaches"
```

### `/sc:build`
Build and compile the project with configurable targets.

**Flags:**
- `--target <name>`: Specify build target
- `--optimize`: Enable optimizations
- `--clean`: Clean build (remove artifacts first)

**Example:**
```bash
/sc:build --optimize --target production
```

### `/sc:design`
Architecture and system design with optional diagram generation.

**Flags:**
- `--diagram`: Generate architecture diagram
- `--adr`: Create Architecture Decision Record
- `--constraints`: Document system constraints
- `--consensus`: Multi-model design review

**Example:**
```bash
/sc:design --diagram --adr "Microservices architecture"
```

### `/sc:document`
Generate documentation including API docs, READMEs, and inline comments.

**Flags:**
- `--api`: Generate API documentation
- `--readme`: Generate/update README
- `--inline`: Add inline code comments
- `--format <type>`: Output format (markdown, mdx, rst)

**Example:**
```bash
/sc:document --api --readme src/
```

### `/sc:estimate`
Estimate effort, resources, and timeline for tasks.

**Flags:**
- `--breakdown`: Provide detailed breakdown
- `--risk`: Include risk assessment
- `--confidence`: Show confidence intervals

**Example:**
```bash
/sc:estimate --breakdown --risk "Implement OAuth2"
```

### `/sc:explain`
Generate detailed explanations of code or concepts.

**Flags:**
- `--depth <1-3>`: Explanation depth
- `--audience <level>`: Target audience (beginner, intermediate, expert)

**Example:**
```bash
/sc:explain --depth 3 src/complex_algorithm.py
```

### `/sc:git`
Git operations including commits and pull requests.

**Flags:**
- `--commit`: Create commit
- `--pr`: Create pull request
- `--branch <name>`: Specify branch

**Example:**
```bash
/sc:git --commit --pr "Add user authentication"
```

### `/sc:implement`
Core implementation command with quality guardrails.

**Flags:**
- `--agent <name>`: Use specific agent
- `--persona <name>`: Alternative to --agent
- `--loop [n]`: Enable iterative improvement (max 5)
- `--pal-review`: Request PAL code review
- `--with-tests`: Auto-generate tests
- `--safe`: Enable strict guardrails
- `--orchestrate`: Multi-agent orchestration
- `--strategy <type>`: Orchestration strategy

**Example:**
```bash
/sc:implement --loop 3 --pal-review --with-tests "Add rate limiting"
```

### `/sc:improve`
Refine and improve existing code modules.

**Flags:**
- `--refactor`: Focus on refactoring
- `--optimize`: Focus on optimization
- `--readability`: Improve readability

**Example:**
```bash
/sc:improve --refactor --readability src/legacy_module.py
```

### `/sc:index`
Build and query codebase indexes.

**Flags:**
- `--rebuild`: Force rebuild index
- `--query <term>`: Search the index

**Example:**
```bash
/sc:index --rebuild src/
/sc:index --query "authentication"
```

### `/sc:test`
Run tests with coverage and reporting.

**Flags:**
- `--coverage`: Enable coverage measurement
- `--watch`: Watch mode for continuous testing
- `--framework <name>`: Specify test framework
- `--markers <expr>`: Pytest marker expression
- `--fail-fast`: Stop on first failure

**Example:**
```bash
/sc:test --coverage --framework pytest tests/
```

### `/sc:workflow`
Multi-step workflow orchestration.

**Flags:**
- `--steps`: Define workflow steps
- `--parallel`: Enable parallel execution
- `--checkpoint`: Save state at checkpoints

**Example:**
```bash
/sc:workflow --steps "analyze,implement,test,document"
```

## Flags Common to Most Commands

| Flag | Short | Description |
|------|-------|-------------|
| `--think <1-3>` | `-t` | Controls reasoning depth |
| `--consensus` | `-c` | Force multi-model consensus |
| `--safe` | `-s` | Enable strict guardrails |
| `--delegate <agent>` | `-d` | Pin to specific agent |
| `--loop [n]` | `-l` | Enable iterative improvement |
| `--pal-review` | | Request PAL code review |
| `--verbose` | `-v` | Enable detailed output |
| `--quiet` | `-q` | Minimize output |
| `--uc` | | Ultra-compressed (token efficient) |

## PAL Review Integration

When the `--pal-review` flag is used, the executor signals that a code review
should be performed. The review is handled by Claude invoking the native MCP
tool `mcp__pal__codereview` after the Python executor completes.

**Workflow:**
1. Command executes with `--pal-review` flag
2. Executor applies changes and sets `pal_review_signal` in results
3. Claude reads the signal and invokes `mcp__pal__codereview`
4. Review feedback is incorporated before task completion

**Example:**
```bash
/sc:implement refactor auth module --pal-review
```

## Quality-Driven Execution

Commands that modify code integrate with the quality pipeline:

1. **Validation Stages**: syntax, security, style, tests, type_check, performance
2. **Deterministic Scoring**: Real tool output (pytest, ruff, bandit, mypy)
3. **Iterative Improvement**: `--loop` continues until quality threshold met
4. **Hard Limits**: HARD_MAX_ITERATIONS = 5 cannot be exceeded

See the individual command modules under `SuperClaude/Commands/` for extended
options and YAML front matter describing required context.
