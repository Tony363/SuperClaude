# SuperClaude Framework

<p align="center">
  <img src="https://img.shields.io/badge/version-6.0.0--alpha-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="Python">
  <img src="https://img.shields.io/badge/agents-131-orange" alt="Agents">
  <img src="https://img.shields.io/badge/commands-13-purple" alt="Commands">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

**An intelligent AI orchestration framework for Claude Code that provides multi-model consensus, specialized agents, behavioral modes, and quality-driven execution with iterative improvement loops.**

SuperClaude transforms Claude Code into a powerful development platform with 131 specialized agents, multi-provider AI routing, MCP server integration, and sophisticated quality validation pipelines featuring deterministic safety grounding.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
  - [High-Level System Architecture](#high-level-system-architecture)
  - [Execution Routing (Skills vs Legacy)](#execution-routing-skills-vs-legacy)
  - [Request Flow](#request-flow)
- [The Agentic Loop (`--loop`)](#the-agentic-loop---loop)
  - [How It Works](#how-it-works)
  - [Termination Conditions](#termination-conditions)
  - [P0/P1 Safety Features](#p0p1-safety-features)
- [Core Components](#core-components)
  - [Agent System](#agent-system)
  - [Command System](#command-system)
  - [Model Router](#model-router)
  - [Quality Pipeline](#quality-pipeline)
  - [Worktree Isolation](#worktree-isolation)
- [MCP Integrations](#mcp-integrations)
  - [Rube MCP](#rube-mcp)
  - [PAL MCP](#pal-mcp)
  - [LinkUp Search](#linkup-search)
- [Behavioral Modes](#behavioral-modes)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)
- [Extensibility Guide](#extensibility-guide)
- [Troubleshooting](#troubleshooting)
- [CI/CD Pipeline](#cicd-pipeline)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

---

## Overview

SuperClaude is a sophisticated AI orchestration framework that enhances Claude Code with:

- **131 Specialized Agents**: 15 core + 116 extended agents across 10 categories
- **Multi-Model Consensus**: Route requests to GPT-5, Gemini 2.5 Pro, Claude, xAI Grok
- **13 Commands**: analyze, implement, test, design, document, and more
- **Agentic Loop**: Iterative improvement with PAL MCP code reviews (`--loop` flag)
- **Behavioral Modes**: Normal, Task Management, Token Efficiency
- **Quality Validation**: Multi-stage pipelines with deterministic safety grounding
- **MCP Integration**: Rube (500+ apps), PAL (consensus & code review), LinkUp (web search)

---

## Key Features

### Agentic Loop for Iterative Development

The `--loop` flag enables automatic iteration until quality thresholds are met:

```bash
/sc:implement --loop "Add user authentication"
```

Each iteration:
1. Executes the implementation
2. Runs PAL MCP code review (`mcp__pal__codereview`)
3. Evaluates quality across 9 dimensions
4. Re-delegates with feedback if score < threshold
5. Terminates on success, oscillation, or max iterations

### Deterministic Safety Grounding

Unlike pure LLM self-evaluation, SuperClaude grounds quality scores in **verifiable facts**:

- **Test failures** cap maximum score at 40-60%
- **Security vulnerabilities** cap score at 30%
- **Build failures** cap score at 45%
- **Clean signals** (tests pass, lint clean) add bonuses

This prevents the system from hallucinating success when real problems exist.

---

## Architecture

### High-Level System Architecture

```mermaid
graph TB
    subgraph "SuperClaude Framework v6.0.0"
        User[User Input] --> Parser[Command Parser]
        Parser --> Executor[Command Executor]

        Executor --> Facade[Execution Facade]
        Executor --> Router[Model Router]
        Executor --> Agents[Agent System<br/>131 Agents]
        Executor --> Modes[Behavioral Modes]

        Facade --> Skills[Skills Runtime]
        Facade --> Legacy[Legacy Executor]

        Router --> Anthropic[Claude Opus 4.1]
        Router --> OpenAI[GPT-5 / GPT-4.1]
        Router --> Google[Gemini 2.5 Pro]
        Router --> xAI[Grok 4]

        Agents --> Registry[Agent Registry<br/>LRU Cache]
        Registry --> CoreAgents[15 Core Agents]
        Registry --> ExtendedAgents[116 Extended Agents]

        Executor --> MCP[MCP Integrations]
        MCP --> Rube[Rube MCP<br/>500+ Apps]
        MCP --> PAL[PAL MCP<br/>Consensus]
        MCP --> LinkUp[LinkUp<br/>Web Search]

        Executor --> Quality[Quality Pipeline]
        Quality --> Validation[5 Validation Stages]
        Quality --> Signals[Deterministic Signals]
    end

    style User fill:#e1f5fe
    style Executor fill:#fff3e0
    style Facade fill:#e8f5e9
    style Router fill:#f3e5f5
    style Agents fill:#e8f5e9
    style MCP fill:#fce4ec
    style Quality fill:#fff9c4
```

### Execution Routing (Skills vs Legacy)

SuperClaude supports dual execution paths controlled by feature flags:

```mermaid
graph LR
    subgraph "Execution Facade"
        Input[Command Context] --> Facade[ExecutionFacade]
        Facade --> Check{SUPERCLAUDE_DECOMPOSED?}

        Check -->|enabled + allowlisted| Router{Routing Plan}
        Check -->|disabled| Legacy[Legacy Executor]

        Router -->|RuntimeMode.SKILLS| Skills[Skills Runtime]
        Router -->|RuntimeMode.LEGACY| Legacy

        Skills --> Output[Command Output]
        Legacy --> Output
    end
```

**Environment Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPERCLAUDE_DECOMPOSED` | Enable facade routing | `false` |
| `SUPERCLAUDE_DECOMPOSED_COMMANDS` | Comma-separated allowlist | `analyze` |

### Request Flow

```mermaid
sequenceDiagram
    participant User
    participant Parser as Command Parser
    participant Registry as Command Registry
    participant Executor as Command Executor
    participant Facade as Execution Facade
    participant Agent as Agent Selector
    participant Router as Model Router
    participant Quality as Quality Pipeline

    User->>Parser: /sc:command --flags
    Parser->>Registry: Lookup Command
    Registry-->>Parser: Command Metadata
    Parser->>Executor: ParsedCommand

    Executor->>Facade: Route Execution
    Facade-->>Executor: Skills or Legacy Path

    Executor->>Agent: Select Agent(context)
    Agent-->>Executor: Best Match Agent

    Executor->>Router: Route Request
    Router->>Router: Select Provider
    Router-->>Executor: Model Response

    Executor->>Quality: Validate Output
    Quality->>Quality: Apply Deterministic Signals
    Quality-->>Executor: QualityAssessment

    alt Score >= 90 (production_ready)
        Executor-->>User: Success Response
    else Score >= 75 (needs_attention)
        Executor-->>User: Success with Suggestions
    else Score < 75
        Executor->>Agent: Re-delegate with feedback
        Agent-->>Executor: Improved Result
        Executor-->>User: Iterated Response
    end
```

---

## The Agentic Loop (`--loop`)

The agentic loop is SuperClaude's core iterative improvement mechanism. When enabled via `--loop [n]`, the system automatically re-runs implementations until quality thresholds are met.

### How It Works

```mermaid
sequenceDiagram
    participant User
    participant Executor as Command Executor
    participant Agents as Expert Sub-Agents<br/>(quality-engineer,<br/>refactoring-expert)
    participant PAL as PAL MCP<br/>(mcp__pal__codereview)
    participant Quality as Quality Scorer
    participant Signals as Deterministic Signals

    User->>Executor: /sc:implement --loop [n]

    Note over Executor: --loop enables<br/>PAL review automatically

    loop Iteration 1..n (max capped at HARD_MAX_ITERATIONS=5)
        Executor->>Agents: Run agent pipeline
        Agents-->>Executor: Code changes + tests

        Executor->>PAL: mcp__pal__codereview(changed_files)
        PAL-->>Executor: Review findings

        Executor->>Quality: evaluate(output, context)
        Quality->>Signals: Apply test/lint/security signals
        Signals-->>Quality: Hard caps + bonuses
        Quality-->>Executor: QualityAssessment<br/>(score, band, improvements_needed)

        alt score >= 90 (QUALITY_MET)
            Executor-->>User: ✅ Success Response
        else score >= 75 AND iterations < max
            Note over Executor: Build feedback context:<br/>improvements_needed,<br/>PAL findings,<br/>current_score
            Executor->>Agents: Re-delegate with feedback
        else Oscillation/Stagnation detected
            Executor-->>User: ⚠️ Best result + warnings
        else Max iterations reached
            Executor-->>User: ⏹️ Best result + termination reason
        end
    end
```

### Termination Conditions

The agentic loop terminates when any of these conditions are met:

| Condition | Description | Trigger |
|-----------|-------------|---------|
| `QUALITY_MET` | Quality threshold achieved | Score >= 90 (production_ready) |
| `MAX_ITERATIONS` | Hard cap reached | Iterations >= HARD_MAX_ITERATIONS (5) |
| `INSUFFICIENT_IMPROVEMENT` | Progress stalled | Improvement < MIN_IMPROVEMENT (5.0) |
| `OSCILLATION` | Scores alternating | Pattern like [65, 72, 65, 71] detected |
| `STAGNATION` | Scores flat | All recent scores within 2.0 points |
| `ERROR` | Improver function failed | Exception during iteration |
| `HUMAN_ESCALATION` | Requires manual review | Complex issues needing human judgment |

### P0/P1 Safety Features

SuperClaude implements layered safety to prevent runaway loops and inflated scores:

#### P0 Safety: Hard Iteration Limits

```python
# From quality_scorer.py
MAX_ITERATIONS = 3        # Default iterations
HARD_MAX_ITERATIONS = 5   # Absolute ceiling, CANNOT be overridden
OSCILLATION_WINDOW = 3    # Scores checked for oscillation
STAGNATION_THRESHOLD = 2.0  # Minimum score difference
```

**Key guarantee**: Even if you pass `max_iterations=100`, the loop caps at 5.

#### P1 Safety: Deterministic Signal Grounding

Unlike pure LLM self-evaluation, quality scores are grounded in verifiable facts:

```mermaid
graph TB
    subgraph "Deterministic Signals"
        Base[Base LLM Score] --> Check{Hard Failures?}

        Check -->|Security Critical| Cap30[Cap at 30%]
        Check -->|Tests Failing >50%| Cap40[Cap at 40%]
        Check -->|Tests Failing >20%| Cap50[Cap at 50%]
        Check -->|Build Errors| Cap45[Cap at 45%]
        Check -->|Security High| Cap65[Cap at 65%]
        Check -->|No Failures| Bonus[Apply Bonuses]

        Bonus --> Coverage{Coverage >= 80%?}
        Coverage -->|Yes| Add10[+10 points]
        Coverage -->|No| Lint{Lint Clean?}

        Lint -->|Yes| Add5[+5 points]
        Lint -->|No| Final[Final Score]

        Add10 --> Final
        Add5 --> Final
        Cap30 --> Final
        Cap40 --> Final
        Cap50 --> Final
        Cap45 --> Final
        Cap65 --> Final
    end
```

**Bonus Points (max +25):**
- Test coverage >= 80%: +10 points
- Clean lint: +5 points
- Clean type check: +5 points
- All tests passing: +5 points
- Security scan passed: +5 points

---

## Core Components

### Agent System

SuperClaude features **131 specialized agents** organized into 10 categories:

```mermaid
mindmap
  root((131 Agents))
    Core Agents
      15 agents
      general-purpose
      root-cause-analyst
      refactoring-expert
      security-engineer
      system-architect
      quality-engineer
      python-expert
    01-Core Development
      11 agents
      fullstack-developer
      frontend-developer
      backend-developer
      api-designer
    02-Language Specialists
      23 agents
      python-pro
      typescript-pro
      rust-engineer
      golang-pro
      java-architect
    03-Infrastructure
      12 agents
      cloud-architect
      kubernetes-specialist
      terraform-engineer
      devops-engineer
    04-Quality Security
      12 agents
      code-reviewer
      penetration-tester
      qa-expert
      security-auditor
    05-Data AI
      12 agents
      ml-engineer
      data-scientist
      llm-architect
      prompt-engineer
    06-Developer Experience
      10 agents
      technical-writer
      cli-developer
      documentation-engineer
    07-Specialized Domains
      11 agents
      domain experts
    08-Business Product
      11 agents
      product-manager
      business-analyst
    09-Meta Orchestration
      8 agents
      coordinators
    10-Research Analysis
      6 agents
      researchers
```

#### Agent Selection Algorithm

Agents are selected using a weighted scoring algorithm:

```mermaid
flowchart TB
    Context[Task Context] --> Domain{Domain Match?}

    Domain -->|Yes +30%| DomainScore[Domain Score]
    Domain -->|No| Keyword

    DomainScore --> Keyword{Keyword Match?}
    Keyword -->|Yes +20%| KeywordScore[Keyword Score]
    Keyword -->|No| FilePattern

    KeywordScore --> FilePattern{File Pattern?}
    FilePattern -->|Yes +20%| PatternScore[Pattern Score]
    FilePattern -->|No| Language

    PatternScore --> Language{Language Match?}
    Language -->|Yes +15%| LangScore[Language Score]
    Language -->|No| Framework

    LangScore --> Framework{Framework Match?}
    Framework -->|Yes +15%| FrameScore[Framework Score]
    Framework -->|No| Calculate

    FrameScore --> Calculate[Calculate Total]
    Calculate --> Threshold{Score >= 0.6?}
    Threshold -->|Yes| Select[Select Agent]
    Threshold -->|No| Default[Use general-purpose]
```

#### Agent Coordination Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **Hierarchical** | Top-down task delegation | Complex multi-step tasks |
| **Consensus** | Multi-agent voting via PAL MCP | Critical decisions |
| **Pipeline** | Sequential processing | Data transformation |
| **Parallel** | Concurrent execution | Independent subtasks |
| **Adaptive** | Dynamic strategy selection | Uncertain requirements |
| **Swarm** | Emergent coordination | Large-scale analysis |

### Command System

13 commands available via `/sc:` syntax:

```mermaid
graph TB
    subgraph "Command System"
        Parser[Command Parser<br/>YAML Frontmatter]
        Registry[Command Registry<br/>Auto-discovery]
        Executor[Command Executor]

        Parser --> Registry
        Registry --> Executor

        subgraph "Sub-Executors"
            AO[agent_orchestration.py]
            CS[consensus.py]
            GO[git_operations.py]
            CM[change_management.py]
            TE[testing.py]
            QU[quality.py]
            AS[ast_analysis.py]
        end

        Executor --> AO
        Executor --> CS
        Executor --> GO
        Executor --> CM
        Executor --> TE
        Executor --> QU
        Executor --> AS
    end
```

| Command | Purpose | Key Flags |
|---------|---------|-----------|
| `/sc:analyze` | Code analysis, quality assessment | `--deep`, `--agent` |
| `/sc:implement` | Feature/code implementation | `--persona`, `--loop [n]` |
| `/sc:test` | Test execution with coverage | `--coverage`, `--watch` |
| `/sc:design` | Architecture and system design | `--diagram`, `--adr` |
| `/sc:document` | Documentation generation | `--api`, `--readme` |
| `/sc:brainstorm` | Creative ideation | `--divergent`, `--converge` |
| `/sc:build` | Project building and compilation | `--target`, `--optimize` |
| `/sc:estimate` | Effort and resource estimation | `--breakdown`, `--risk` |
| `/sc:explain` | Code/concept explanation | `--depth`, `--audience` |
| `/sc:improve` | Code enhancement | `--refactor`, `--optimize` |
| `/sc:workflow` | Multi-step workflow management | `--steps`, `--parallel` |
| `/sc:git` | Git operations | `--commit`, `--pr` |
| `/sc:index` | Search and indexing | `--rebuild`, `--query` |

### Model Router

The Model Router intelligently distributes requests across multiple AI providers:

```mermaid
graph LR
    subgraph "Model Router"
        Input[Request] --> Selector[Provider Selector]

        Selector --> |deep_thinking| GPT5[GPT-5<br/>400K context]
        Selector --> |long_context| Gemini[Gemini 2.5 Pro<br/>2M context]
        Selector --> |fallback| Claude[Claude Opus 4.1<br/>200K context]
        Selector --> |fast_iteration| Grok[Grok 4<br/>256K context]

        GPT5 --> Consensus[Consensus Engine]
        Gemini --> Consensus
        Claude --> Consensus
        Grok --> Consensus

        Consensus --> Output[Final Response]
    end
```

#### Supported Models

| Provider | Model | Context | Features | Priority |
|----------|-------|---------|----------|----------|
| **OpenAI** | GPT-5 | 400K | Thinking, Vision | 1 |
| **OpenAI** | GPT-4.1 | 1M | Large context | 3 |
| **OpenAI** | GPT-4o | 128K | Fast, Cost-effective | 4 |
| **Google** | Gemini 2.5 Pro | **2M** | Thinking, Vision | 1 |
| **Anthropic** | Claude Opus 4.1 | 200K | Fallback, Validation | 2 |
| **xAI** | Grok 4 | 256K | Thinking, Fast | 2 |

### Quality Pipeline

The validation pipeline enforces layered quality checks with short-circuit behavior:

```mermaid
flowchart TB
    subgraph "Validation Pipeline"
        Input[Context] --> Syntax[Syntax Stage<br/>Required]

        Syntax -->|passed| Security[Security Stage<br/>Required]
        Syntax -->|fatal| Skip1[Skip All]

        Security -->|passed| Style[Style Stage<br/>Optional]
        Security -->|fatal| Skip2[Skip All]

        Style --> Tests[Tests Stage<br/>Required]

        Tests -->|passed| Perf[Performance Stage<br/>Optional]
        Tests -->|fatal| Skip3[Skip All]

        Perf --> Signals[Apply Deterministic Signals]
        Skip1 --> Signals
        Skip2 --> Signals
        Skip3 --> Signals

        Signals --> Results[Aggregate Results]
        Results --> Evidence[Write Evidence<br/>JSON files]
    end
```

#### Quality Dimensions (9 Total)

```mermaid
pie title Quality Score Weights
    "Correctness" : 25
    "Completeness" : 20
    "Performance" : 10
    "Maintainability" : 10
    "Security" : 10
    "Scalability" : 10
    "Testability" : 10
    "PAL Review" : 10
    "Usability" : 5
```

| Dimension | Weight | Metrics |
|-----------|--------|---------|
| **Correctness** | 25% | Tests pass, no runtime errors, output validation |
| **Completeness** | 20% | Feature coverage, edge cases, documentation |
| **Performance** | 10% | Time/space complexity, resource usage |
| **Maintainability** | 10% | Readability, modularity, naming |
| **Security** | 10% | Input validation, authentication, data protection |
| **Scalability** | 10% | Architecture, database design, caching |
| **Testability** | 10% | Unit tests, integration tests, test quality |
| **PAL Review** | 10% | External code review via `mcp__pal__codereview` |
| **Usability** | 5% | UI consistency, error messages, accessibility |

#### Quality Thresholds & Actions

| Score Range | Band | Action |
|-------------|------|--------|
| 90-100 | `production_ready` | Auto-approve, fast-track |
| 75-89 | `needs_attention` | Accept with improvement suggestions |
| 50-74 | `iterate` | Iterate with feedback (max 5 iterations) |
| < 50 | `iterate` | Delegate to quality-engineer, escalate |

### Worktree Isolation

SuperClaude uses git worktrees to safely isolate file modifications:

```mermaid
graph LR
    subgraph "Worktree Management"
        Main[Main Branch] --> WT[.worktrees/]
        WT --> WT1[worktree-1<br/>Feature A]
        WT --> WT2[worktree-2<br/>Feature B]
        WT --> WTN[worktree-n<br/>Feature N]

        WT1 --> Validate{Validation<br/>Passed?}
        Validate -->|Yes| Merge[Merge to Main]
        Validate -->|No| Fix[Fix & Retry]
    end
```

**Configuration** (from `superclaud.yaml`):

```yaml
worktree:
  enabled: true
  base_dir: .worktrees
  max_worktrees: 10
  cleanup_age_days: 7
  integration_branch: integration

  validation:
    run_tests: true
    check_conflicts: true
    require_clean: true
```

**Benefits:**
- Prevents destructive changes to main branch
- Enables parallel feature development
- Automatic cleanup of stale worktrees
- Conflict checking before merge

---

## MCP Integrations

SuperClaude integrates with Model Context Protocol (MCP) servers via Claude Code's native tools.

```mermaid
graph TB
    subgraph "MCP Architecture"
        Executor[Command Executor]

        Executor --> RubeInt[Rube MCP]
        Executor --> PALInt[PAL MCP]
        Executor --> LinkUpInt[LinkUp Search]

        subgraph "Rube MCP - 500+ Apps"
            RubeInt --> Search[RUBE_SEARCH_TOOLS]
            RubeInt --> Execute[RUBE_MULTI_EXECUTE_TOOL]
            RubeInt --> Plan[RUBE_CREATE_PLAN]
            RubeInt --> Connect[RUBE_MANAGE_CONNECTIONS]

            Execute --> Slack[Slack]
            Execute --> GitHub[GitHub]
            Execute --> Gmail[Gmail]
            Execute --> Sheets[Google Sheets]
        end

        subgraph "PAL MCP - Consensus & Analysis"
            PALInt --> Chat[chat]
            PALInt --> Think[thinkdeep]
            PALInt --> Plan2[planner]
            PALInt --> Consensus[consensus]
            PALInt --> CodeRev[codereview]
            PALInt --> PreCommit[precommit]
            PALInt --> Debug[debug]
        end

        subgraph "LinkUp - Web Search"
            LinkUpInt --> WebSearch[LINKUP_SEARCH]
        end
    end
```

### Rube MCP

Connects to 500+ apps for cross-application automation:

| Tool | Purpose |
|------|---------|
| `RUBE_SEARCH_TOOLS` | Discover available app integrations |
| `RUBE_MULTI_EXECUTE_TOOL` | Execute up to 50 tools in parallel |
| `RUBE_CREATE_PLAN` | Create workflow execution plans |
| `RUBE_MANAGE_CONNECTIONS` | Manage OAuth/API connections |
| `RUBE_REMOTE_WORKBENCH` | Execute Python in sandbox |
| `RUBE_CREATE_UPDATE_RECIPE` | Create reusable automation recipes |

**Supported Apps:** Slack, GitHub, Gmail, Google Sheets, Jira, Notion, Teams, and 500+ more.

### PAL MCP

Provides multi-model consensus and analysis via meta-prompting:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__pal__chat` | Collaborative thinking | General queries with specific model |
| `mcp__pal__thinkdeep` | Multi-stage investigation | Complex analysis, architecture decisions |
| `mcp__pal__planner` | Sequential planning | Implementation planning, task breakdown |
| `mcp__pal__consensus` | Multi-model consensus | Critical decisions, architectural choices |
| `mcp__pal__codereview` | Systematic code review | PR reviews, security audits (used by `--loop`) |
| `mcp__pal__precommit` | Git change validation | Pre-commit checks, change impact |
| `mcp__pal__debug` | Root cause analysis | Complex bugs, systematic debugging |

### LinkUp Search

Web search integration for current information:

```python
# Example: Search via Rube MCP
{
  "tools": [{
    "tool_slug": "LINKUP_SEARCH",
    "arguments": {
      "query": "latest Python 3.12 features",
      "depth": "deep",
      "output_type": "sourcedAnswer"
    }
  }]
}
```

---

## Behavioral Modes

SuperClaude supports multiple behavioral modes that change how the framework operates:

```mermaid
stateDiagram-v2
    [*] --> Normal

    Normal --> TaskManagement: >3 steps or complex deps
    Normal --> TokenEfficiency: --uc flag

    TaskManagement --> Normal: complete
    TokenEfficiency --> Normal: complete

    TaskManagement --> TokenEfficiency: context > 75%

    state TaskManagement {
        [*] --> Plan
        Plan --> Track
        Track --> Execute
        Execute --> Evaluate
        Evaluate --> Iterate
        Iterate --> [*]
    }
```

| Mode | Trigger | Features | Use Case |
|------|---------|----------|----------|
| **Normal** | default | Balanced verbosity, standard flow | Day-to-day development |
| **Task Management** | >3 steps, complex deps | TodoWrite tracking, hierarchical breakdown | Multi-step operations |
| **Token Efficiency** | `--uc` flag | Compressed symbols, minimal verbosity | Context/cost constraints |

### Token Efficiency Symbols

```
Status:  ✅ Done  ❌ Failed  ⚠️ Warning  🔄 Progress  ⏳ Pending
Domain:  ⚡ Perf  🔍 Analysis  🛡️ Security  📦 Deploy  🏗️ Arch
Logic:   → Leads to  ⇒ Transforms  ∴ Therefore  » Sequence
```

**Example:**
```
Standard: "The authentication system has a security vulnerability"
Token Efficient: "auth.js:45 → 🛡️ sec risk in user val()"
```

---

## Installation

### Requirements

- Python 3.10+
- pip or poetry
- Claude Code CLI

### Install from Source

```bash
# Clone the repository
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install in development mode
pip install -e .[dev]

# Verify installation
SuperClaude --help
```

---

## Quick Start

### Basic Usage with Claude Code

```bash
# Start Claude Code
claude

# Use SuperClaude commands
/sc:analyze --deep src/auth.py
/sc:implement --agent=backend-developer "Add user authentication"
/sc:implement --loop 3 "Add rate limiting middleware"  # Iterate up to 3 times
/sc:test --coverage tests/
/sc:design --diagram "microservices architecture"
```

### Using the Agentic Loop

```bash
# Basic loop (uses default MAX_ITERATIONS=3)
/sc:implement --loop "Add input validation"

# Specify max iterations (capped at HARD_MAX=5)
/sc:implement --loop 5 "Refactor authentication module"

# Loop with specific agent
/sc:implement --loop --agent=security-engineer "Add CSRF protection"
```

### Programmatic Usage

```python
from SuperClaude.Commands.command_executor import CommandExecutor
from SuperClaude.Agents.registry import AgentRegistry

# Initialize
registry = AgentRegistry()
executor = CommandExecutor()

# Execute command
result = await executor.execute("/sc:analyze --agent=root-cause-analyst src/bug.py")

if result.success:
    print(f"Analysis complete: {result.output}")
    print(f"Quality score: {result.quality_score}")
    print(f"Band: {result.band}")  # production_ready, needs_attention, or iterate
else:
    print(f"Errors: {result.errors}")
```

---

## Configuration

### CLAUDE.md Integration

SuperClaude integrates with Claude Code via `CLAUDE.md` configuration files:

```markdown
# ~/.claude/CLAUDE.md (Global)

# SuperClaude Entry Point
@AGENTS.md
@CLAUDE_CORE.md
@FLAGS.md
@PRINCIPLES.md
@TOOLS.md

# Behavioral Modes
@MODE_Normal.md
@MODE_Task_Management.md
@MODE_Token_Efficiency.md

# MCP Documentation
@MCP_Rube.md
@MCP_Pal.md
@MCP_LinkUp.md
```

### Configuration Files (YAML)

| File | Purpose |
|------|---------|
| `config/superclaud.yaml` | Main framework config, modes, quality settings |
| `config/models.yaml` | Model routing, provider settings |
| `config/quality.yaml` | Quality scoring, thresholds, gates |

### Key Configuration Options

```yaml
# From superclaud.yaml

# Quality scoring
quality:
  enabled: true
  default_threshold: 70.0
  max_iterations: 5

# Agent system
agents:
  max_delegation_depth: 5
  parallel_execution: true
  default_timeout: 300

# Token optimization
token_optimization:
  enabled: true
  compression_level: medium
  budgets:
    analysis: 10000
    implementation: 20000
    documentation: 5000
    testing: 15000

# Dynamic loading
dynamic_loading:
  enabled: true
  max_cache_size: 10
  load_time_target: 0.1
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| **API Keys** | | |
| `ANTHROPIC_API_KEY` | Claude API key | Required |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `GOOGLE_API_KEY` | Google/Gemini API key | Optional |
| `XAI_API_KEY` | xAI/Grok API key | Optional |
| **Framework** | | |
| `SUPERCLAUDE_DECOMPOSED` | Enable Skills/Legacy routing | `false` |
| `SUPERCLAUDE_DECOMPOSED_COMMANDS` | Allowlisted commands | `analyze` |
| `SUPERCLAUDE_OFFLINE_MODE` | Disable network for testing | `false` |
| `SUPERCLAUDE_REPO_ROOT` | Repository root path | Auto-detected |
| `SUPERCLAUDE_SKIP_BOOTSTRAP` | Skip auto-install | `false` |
| **Telemetry** | | |
| `SUPERCLAUDE_TELEMETRY_ENABLED` | Enable telemetry | `true` |
| `SUPERCLAUDE_METRICS_DIR` | Metrics directory | `.superclaude_metrics` |

---

## Extensibility Guide

### Adding a New Agent

1. **Create markdown file** in appropriate `SuperClaude/Agents/Extended/` category:

```markdown
---
name: my-custom-agent
category: 01-core-development
description: Expert at custom task
triggers:
  - custom
  - special
  - my-task
tools:
  - Read
  - Write
  - Bash
domains:
  - backend
  - api
languages:
  - python
  - typescript
---

# My Custom Agent

## Capabilities
- Specialized capability 1
- Specialized capability 2

## Approach
1. Step one
2. Step two
```

2. **Run agent discovery** to verify registration:

```python
from SuperClaude.Agents.registry import AgentRegistry

registry = AgentRegistry()
registry.discover_agents(force=True)
print(registry.get_agent_config("my-custom-agent"))
```

### Adding a New Command

1. **Create markdown file** in `SuperClaude/Commands/`:

```markdown
---
name: mycommand
description: Does something useful
category: workflow
complexity: medium
triggers:
  - mycommand
  - my-action
parameters:
  - name: target
    type: string
    required: true
    description: Target file or directory
flags:
  - name: verbose
    short: v
    description: Enable verbose output
---

# /sc:mycommand

## Usage
/sc:mycommand [target] --verbose
```

2. **Implement handler** in `SuperClaude/Commands/executor/` if needed.

### Adding a Model Provider

1. **Create client** in `SuperClaude/APIClients/`:

```python
from .base_client import BaseAPIClient

class MyProviderClient(BaseAPIClient):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.myprovider.com/v1"

    async def complete(self, prompt: str, **kwargs) -> str:
        # Implementation
        pass
```

2. **Register in router** in `SuperClaude/ModelRouter/router.py`.

---

## Troubleshooting

### Common Issues

#### Loop Terminates Early

**Symptom:** `--loop` stops before quality threshold is met.

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Oscillation detected | Scores alternating (e.g., 65→72→65). Review feedback to find conflicting improvements. |
| Stagnation detected | Scores not changing. Add more specific requirements or change approach. |
| Insufficient improvement | Score improved < 5 points. Provide more detailed feedback. |
| Hard cap reached | Hit HARD_MAX_ITERATIONS=5. This is intentional; refine requirements. |

#### Low Quality Score

**Symptom:** Score below expected threshold.

**Check deterministic signals:**

```bash
# View quality assessment details
cat .superclaude_metrics/quality_assessment_*.json
```

**Common caps:**
- Score capped at 30%? Check for critical security issues.
- Score capped at 40-60%? Check test failures.
- Score capped at 45%? Check build errors.

#### MCP Connection Issues

**Symptom:** MCP tools not responding or timing out.

**Solutions:**

1. **Check API keys:**
   ```bash
   echo $ANTHROPIC_API_KEY
   echo $OPENAI_API_KEY
   ```

2. **Verify MCP server status:**
   ```bash
   # Check Rube MCP
   curl https://api.composio.dev/health

   # Check PAL MCP
   mcp__pal__listmodels
   ```

3. **Increase timeout** in `superclaud.yaml`:
   ```yaml
   mcp_servers:
     timeout: 600  # Increase from 300
   ```

#### Agent Not Selected

**Symptom:** Wrong agent handling task.

**Solutions:**

1. **Force specific agent:**
   ```bash
   /sc:implement --agent=security-engineer "Add auth"
   ```

2. **Check agent triggers:**
   ```python
   registry = AgentRegistry()
   config = registry.get_agent_config("security-engineer")
   print(config["triggers"])
   ```

3. **Lower selection threshold** (advanced):
   ```yaml
   agents:
     selection_threshold: 0.3  # Default is 0.6
   ```

### Debug Mode

Enable verbose logging:

```bash
export SUPERCLAUD_LOG_LEVEL=DEBUG
```

View execution traces:

```bash
cat .superclaude_metrics/execution_*.jsonl
```

---

## CI/CD Pipeline

SuperClaude uses GitHub Actions for continuous integration and deployment.

```mermaid
flowchart LR
    subgraph "CI Pipeline"
        Q[Quality Gate] --> T[Test Matrix<br/>Python 3.10]
        T --> C[Coverage Gate<br/>35% min]
        C --> B[Build Check]
        B --> BM[Benchmark Smoke]
    end

    subgraph "Security Pipeline"
        CQ[CodeQL] --> PA[pip-audit]
        PA --> BA[Bandit]
    end

    subgraph "Review Pipeline"
        AI[PAL MCP<br/>Consensus Review]
    end

    subgraph "Deploy Pipeline"
        PY[PyPI Publish]
    end
```

| Workflow | Trigger | Checks |
|----------|---------|--------|
| **CI** | Push/PR | Ruff lint, Ruff format, MyPy, Tests, Coverage (35%), Build |
| **Security** | Push/PR + Weekly | CodeQL, pip-audit, Bandit |
| **AI Review** | PR opened | PAL MCP Consensus Code Review |
| **Publish** | Release | Build, version check, PyPI upload |

---

## Project Structure

```
SuperClaude/
├── SuperClaude/
│   ├── Agents/
│   │   ├── Extended/              # 116 extended agents
│   │   │   ├── 01-core-development/
│   │   │   ├── 02-language-specialists/
│   │   │   ├── 03-infrastructure/
│   │   │   ├── 04-quality-security/
│   │   │   ├── 05-data-ai/
│   │   │   ├── 06-developer-experience/
│   │   │   ├── 07-specialized-domains/
│   │   │   ├── 08-business-product/
│   │   │   ├── 09-meta-orchestration/
│   │   │   └── 10-research-analysis/
│   │   ├── core/                  # 15 core agent implementations
│   │   ├── base.py                # BaseAgent ABC
│   │   ├── registry.py            # Agent discovery & catalog
│   │   └── selector.py            # Intelligent selection
│   │
│   ├── Commands/
│   │   ├── execution/             # Execution routing
│   │   │   ├── facade.py          # Skills/Legacy router
│   │   │   ├── routing.py         # Command router
│   │   │   └── context.py         # Execution context
│   │   ├── executor/              # Sub-executors
│   │   │   ├── agent_orchestration.py
│   │   │   ├── consensus.py
│   │   │   ├── git_operations.py
│   │   │   ├── testing.py
│   │   │   └── quality.py
│   │   ├── command_executor.py    # Main executor
│   │   ├── parser.py              # Command parsing
│   │   └── registry.py            # Command catalog
│   │
│   ├── Quality/
│   │   ├── quality_scorer.py      # 9-dimension scoring + agentic loop
│   │   └── validation_pipeline.py # 5-stage validation
│   │
│   ├── Telemetry/
│   │   ├── factory.py             # Telemetry factory
│   │   ├── jsonl.py               # JSONL storage
│   │   └── interfaces.py          # Client interfaces
│   │
│   ├── Modes/                     # Behavioral modes
│   ├── Skills/                    # Skills runtime
│   └── Core/                      # Core utilities
│
├── config/                        # YAML configurations
├── setup/                         # Installation system
├── tests/                         # Test suites
├── Docs/                          # User & developer guides
├── scripts/                       # Build scripts
├── benchmarks/                    # Performance tests
├── .github/workflows/             # CI/CD pipelines
├── pyproject.toml                 # Package config
└── README.md                      # This file
```

---

## Contributing

### Development Setup

```bash
# Clone and setup
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Run tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -m "not slow" tests/

# Run linting
ruff check .
ruff format --check .
mypy SuperClaude --ignore-missing-imports
```

### Commit Guidelines

- Use concise, imperative subjects
- Reference issues/specs in body
- Include test results for significant changes
- Co-authored-by: Claude for AI-assisted commits

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- **Anthropic** for Claude and Claude Code
- **OpenAI** for GPT-5 API
- **Google** for Gemini API
- **xAI** for Grok API
- **Composio** for Rube MCP
- **PAL MCP** for consensus tools

---

<p align="center">
  <strong>SuperClaude v6.0.0-alpha</strong><br/>
  Intelligent AI Orchestration for Claude Code<br/>
  <em>131 Agents • 13 Commands • 9 Quality Dimensions • 3 Modes</em><br/>
  <em>Iterative Development with Deterministic Safety Grounding</em>
</p>
