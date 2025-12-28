# SuperClaude Framework

<p align="center">
  <img src="https://img.shields.io/badge/version-6.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/agents-130-orange" alt="Agents">
  <img src="https://img.shields.io/badge/skills-127-green" alt="Skills">
  <img src="https://img.shields.io/badge/commands-13-purple" alt="Commands">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

**A config-first meta-framework for Claude Code that provides 130+ specialized agent personas, structured commands, and MCP integration guides.**

SuperClaude transforms Claude Code into a powerful development platform with specialized agent prompts that Claude Code loads and uses directly. The core interface is markdown and YAML configuration files, with optional Python orchestration for advanced workflows.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Agent System](#agent-system)
- [Command System](#command-system)
- [MCP Integrations](#mcp-integrations)
- [Skills System](#skills-system)
- [Configuration](#configuration)
- [Directory Structure](#directory-structure)
- [Creating Custom Agents](#creating-custom-agents)
- [Contributing](#contributing)

---

## Overview

SuperClaude is a meta-prompt framework that enhances Claude Code with:

- **130+ Specialized Agents**: 16 core + 114 extended agents across 10 categories
- **127 Claude Skills**: Agent personas and command workflows in `.claude/skills/`
- **13 Structured Commands**: analyze, implement, test, design, document, and more
- **MCP Integration Guides**: Rube (500+ apps), PAL (consensus & code review), LinkUp (web search)
- **Pure Config**: No Python runtime - Claude Code reads prompts directly
- **Easy Extension**: Add new agents by creating markdown files

---

## Key Features

### Config-First Architecture

SuperClaude v6.0.0 is a **config-first hybrid framework**:

- **Markdown Agent Personas**: Each agent is a self-contained markdown file
- **YAML Configuration**: Agent registry, command index, quality thresholds
- **Optional Python Orchestration**: Loop orchestration and quality gates for advanced workflows
- **Portable**: Works with any Claude Code instance
- **Extensible**: Add agents by creating markdown files

### Why Config-First?

| Benefit | Description |
|---------|-------------|
| **Simplicity** | Core interface is markdown/YAML files |
| **Portability** | Works with any Claude Code instance |
| **Extensibility** | Add agents by creating markdown files |
| **Maintainability** | Prompts are easy to refine and version |
| **Version Control** | Easy to diff and review prompt changes |
| **Optional Power** | Python orchestration available when needed |

### Specialized Agent System

130+ agents organized across 10 categories:

| Category | Count | Examples |
|----------|-------|----------|
| Core Development | 16 | Fullstack Developer, API Designer, Backend Developer |
| Language Specialists | 23 | Python Pro, TypeScript Pro, Rust Engineer |
| Infrastructure | 11 | Cloud Architect, Kubernetes Specialist, SRE Engineer |
| Quality & Security | 12 | Code Reviewer, Security Auditor, Chaos Engineer |
| Data & AI | 11 | Data Scientist, ML Engineer, LLM Architect |
| Developer Experience | 10 | CLI Developer, DX Optimizer, Git Workflow Manager |
| Specialized Domains | 11 | Blockchain Developer, IoT Engineer, Game Developer |
| Business & Product | 10 | Product Manager, Scrum Master, UX Researcher |
| Meta Orchestration | 8 | Agent Organizer, Context Manager, Workflow Coordinator |
| Research & Analysis | 8 | Data Researcher, Competitive Analyst, Tech Scout |

### Command System

13 structured commands with consistent patterns:

```
/sc:analyze    - Static analysis and risk assessment
/sc:implement  - Feature implementation with quality gates
/sc:test       - Test generation and coverage analysis
/sc:design     - Architecture and system design
/sc:document   - Documentation generation
/sc:brainstorm - Creative ideation and exploration
/sc:explain    - Educational explanations
/sc:improve    - Code improvement and optimization
/sc:build      - Build system and compilation
/sc:git        - Git operations and workflows
/sc:workflow   - Multi-step task orchestration
/sc:estimate   - Effort estimation and planning
```

---

## Architecture

### How SuperClaude Works

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code (Runtime)                     │
├─────────────────────────────────────────────────────────────┤
│  Loads CLAUDE.md → Reads agents/index.yaml → Selects Agent  │
│  Uses agent persona → Leverages MCP tools as needed          │
└─────────────────────────────────────────────────────────────┘
    │                           │                    │
    ▼                           ▼                    ▼
┌─────────┐              ┌──────────┐         ┌──────────────┐
│ agents/ │              │ commands/│         │     mcp/     │
│ *.md    │              │  *.md    │         │   guides     │
└─────────┘              └──────────┘         └──────────────┘
```

### File-Based Configuration

SuperClaude uses a simple file-based architecture:

1. **CLAUDE.md** - Master system prompt loaded by Claude Code
2. **agents/index.yaml** - Agent registry with triggers and categories
3. **agents/core/*.md** - Core agent persona prompts
4. **agents/extended/**/*.md** - Extended agent persona prompts
5. **commands/index.yaml** - Command registry
6. **commands/*.md** - Command templates
7. **config/*.yaml** - Configuration files
8. **mcp/*.md** - MCP integration guides

---

## Installation

### Option 1: Clone Repository

```bash
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude_Framework
```

### Option 2: Add as Git Submodule

```bash
git submodule add https://github.com/SuperClaude-Org/SuperClaude_Framework.git superclaud
```

### Setup Claude Code

Add to your project's `.claude/settings.json`:

```json
{
  "systemPromptFiles": ["superclaud/CLAUDE.md"]
}
```

Or copy `CLAUDE.md` to your project root.

---

## Quick Start

### 1. Basic Usage

Once configured, Claude Code automatically loads SuperClaude capabilities:

```
User: Help me debug this authentication issue
Claude: [Selects root-cause-analyst agent, applies debugging methodology]
```

### 2. Using Commands

```
User: /sc:analyze src/auth/
Claude: [Runs comprehensive static analysis, security review, quality assessment]
```

### 3. Specifying Agents

```
User: @python-expert Review this Flask application
Claude: [Uses Python expert persona with framework-specific knowledge]
```

### 4. Using MCP Tools

With PAL MCP configured:
```
User: Use PAL to review this code
Claude: [Invokes mcp__pal__codereview for multi-model code review]
```

---

## Agent System

### Core Agents (16)

High-priority generalists for common tasks:

| Agent | Triggers | Purpose |
|-------|----------|---------|
| general-purpose | help, assist, general | Versatile task handling |
| root-cause-analyst | debug, bug, error, crash | Deep debugging and investigation |
| refactoring-expert | refactor, clean, improve | Code quality improvement |
| technical-writer | document, docs, readme | Documentation generation |
| security-engineer | security, auth, vulnerability | Security analysis and hardening |
| performance-engineer | performance, optimize, slow | Performance optimization |
| quality-engineer | test, qa, coverage | Testing and quality assurance |
| python-expert | python, django, flask | Python development |
| system-architect | architecture, design, scalability | System design |
| backend-architect | backend, api, database | Backend systems |
| frontend-architect | frontend, ui, react | Frontend development |
| devops-architect | devops, ci/cd, kubernetes | Infrastructure automation |
| fullstack-developer | fullstack, end-to-end | Full-stack coordination |
| learning-guide | learn, teach, tutorial | Educational guidance |
| requirements-analyst | requirements, spec, user story | Requirements analysis |
| socratic-mentor | mentor, coach, why | Guided discovery learning |

### Extended Agents (114)

Specialized agents across 10 categories in `agents/extended/`:

- **01-core-development/** - API Designer, Mobile Developer, etc.
- **02-language-specialists/** - Language and framework experts
- **03-infrastructure/** - Cloud, Kubernetes, SRE specialists
- **04-quality-security/** - Testing, security, and compliance
- **05-data-ai/** - Data science and machine learning
- **06-developer-experience/** - Tooling and productivity
- **07-specialized-domains/** - Industry-specific specialists
- **08-business-product/** - Product and project management
- **09-meta-orchestration/** - Multi-agent coordination
- **10-research-analysis/** - Research and competitive analysis

### Agent Selection

Agents are selected based on weighted matching:

```yaml
selection:
  weights:
    trigger_match: 0.35      # Keyword triggers
    category_match: 0.25     # Category alignment
    description_match: 0.20  # Description relevance
    tool_match: 0.20         # Required tool availability
```

---

## Command System

Commands provide structured execution patterns. See `commands/index.yaml` for the full registry.

### Command Format

Each command is a markdown file with:

```markdown
---
name: implement
description: Feature implementation with quality gates
flags: [--loop, --tests, --docs]
---

# Implement Command

[Structured implementation methodology...]
```

### Available Commands

| Command | Description | Key Flags |
|---------|-------------|-----------|
| analyze | Static analysis and risk assessment | --security, --deep |
| implement | Feature implementation | --loop, --tests |
| test | Test generation and coverage | --coverage, --mutation |
| design | Architecture and system design | --adr, --diagrams |
| document | Documentation generation | --api, --user |
| brainstorm | Creative ideation | --diverge, --converge |
| explain | Educational explanations | --depth, --examples |
| improve | Code improvement | --perf, --readability |
| build | Build and compilation | --watch, --clean |
| git | Git operations | --conventional, --rebase |
| workflow | Multi-step orchestration | --parallel, --checkpoint |
| estimate | Effort estimation | --breakdown, --risks |

---

## MCP Integrations

SuperClaude includes integration guides for key MCP servers:

### PAL MCP

Multi-model consensus and code review:

- **chat** - General discussion with external models
- **codereview** - Systematic code review
- **consensus** - Multi-model decision making
- **debug** - Deep debugging analysis
- **precommit** - Pre-commit validation

### Rube MCP (Composio)

500+ app integrations:

- GitHub, GitLab, Bitbucket
- Slack, Discord, Teams
- Jira, Linear, Notion
- Gmail, Calendar, Drive
- And 490+ more

### LinkUp Search

Web search capabilities for current information.

---

## Skills System

SuperClaude includes 127 Claude Code skills in `.claude/skills/`:

### Skill Types

| Type | Count | Purpose |
|------|-------|---------|
| Agent Skills (`agent-*`) | 120+ | Specialized personas for different domains |
| Command Skills (`sc-*`) | 7 | Structured workflow implementations |

### Skill Architecture

Each skill follows a standard structure:

```
.claude/skills/agent-python-pro/
└── SKILL.md                 # AI-facing interface (what Claude reads)

.claude/skills/sc-implement/
├── SKILL.md                 # Command interface
└── scripts/                 # Optional tool implementations
    ├── run_tests.py         # Test execution tool
    └── evidence_gate.py     # Quality validation tool
```

**Important**: The Python scripts in `scripts/` are **tool implementations**, not skills themselves:
- `SKILL.md` = The interface Claude reads to understand when/how to invoke a tool
- `scripts/*.py` = Backend implementations executed by the host system

This follows standard agentic patterns. The config-first architecture means the AI-facing interface (`SKILL.md` files) is pure configuration, while optional Python orchestration handles complex workflows.

### Using Skills

Skills are invoked via:
1. **Semantic selection** - Claude automatically selects based on task context
2. **Direct reference** - `@agent-python-pro` or `/sc-implement`
3. **Skill tool** - `Skill("agent-python-pro")` for explicit invocation

---

## Configuration

### config/quality.yaml

Quality thresholds and scoring:

```yaml
quality:
  minimum_score: 0.7
  stages:
    - name: syntax
      weight: 0.2
    - name: security
      weight: 0.3
    - name: performance
      weight: 0.25
    - name: maintainability
      weight: 0.25
```

### config/models.yaml

Model routing configuration:

```yaml
models:
  default: claude-sonnet
  reasoning: claude-opus
  fast: claude-haiku
```

### config/agents.yaml

Agent selection tuning:

```yaml
selection:
  minimum_score: 0.6
  confidence_threshold: 0.8
  max_candidates: 5
```

---

## Directory Structure

```
SuperClaude/
├── CLAUDE.md              # Master system prompt
├── .claude/
│   └── skills/            # 127 Claude Code skills
│       ├── agent-*/       # Agent persona skills
│       │   └── SKILL.md   # Skill definition
│       └── sc-*/          # Command skills
│           ├── SKILL.md   # Command interface
│           └── scripts/   # Optional tool implementations
├── agents/
│   ├── index.yaml         # Agent registry
│   ├── core/              # 16 core agent prompts
│   │   ├── root-cause-analyst.md
│   │   ├── refactoring-expert.md
│   │   └── ...
│   └── extended/          # 114 extended agents
│       ├── 01-core-development/
│       ├── 02-language-specialists/
│       └── ...
├── commands/
│   ├── index.yaml         # Command registry
│   ├── analyze.md
│   ├── implement.md
│   └── ...
├── config/
│   ├── quality.yaml
│   ├── models.yaml
│   └── agents.yaml
├── mcp/
│   ├── MCP_Pal.md
│   ├── MCP_Rube.md
│   └── MCP_LinkUp.md
└── archive/               # Archived Python SDK (v5)
```

---

## Creating Custom Agents

### Agent Prompt Format

Create a new agent in `agents/extended/[category]/`:

```markdown
---
name: my-custom-agent
description: Brief description of the agent's purpose
category: custom
triggers: [keyword1, keyword2, keyword3]
tools: [Read, Write, Edit, Bash, Grep, Glob]
---

# My Custom Agent

You are an expert in [domain] specializing in [specialty].

## Focus Areas

- Area 1
- Area 2
- Area 3

## Approach

1. **Step 1**: Description
2. **Step 2**: Description
3. **Step 3**: Description

## Best Practices

- Practice 1
- Practice 2

## Checklist

- [ ] Item 1
- [ ] Item 2
```

### Register the Agent

Add to `agents/index.yaml`:

```yaml
extended:
  custom-category:
    description: "Custom agents"
    agents:
      - name: my-custom-agent
        file: extended/custom-category/my-custom-agent.md
        triggers: [keyword1, keyword2]
```

---

## Contributing

Contributions welcome! Key areas:

1. **New Agents**: Add specialized agent personas
2. **Command Templates**: Improve command structures
3. **MCP Guides**: Add integration documentation
4. **Configuration**: Tune selection algorithms

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Claude Code team at Anthropic
- MCP server developers (PAL, Rube/Composio, LinkUp)
- All contributors to the SuperClaude framework

---

<p align="center">
  <strong>SuperClaude v6.0.0</strong><br>
  Pure prompts. Maximum power.
</p>
