# SuperClaude Framework

<div align="center">

![Version](https://img.shields.io/badge/version-4.0.9-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-purple)
![Framework](https://img.shields.io/badge/framework-AI--Enhanced-orange)

**🚀 AI-Enhanced Development Framework for Claude Code**

*Intelligent Agents • Dynamic Loading • Quality-Driven Iteration • Token Optimized*

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [What's New](#-whats-new-in-409)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Core Components](#-core-components)
- [Installation](#-installation)
- [Agent System](#-agent-system)
- [MCP Servers](#-mcp-servers)
- [Behavioral Modes](#-behavioral-modes)
- [Command Reference](#-command-reference)
- [Agentic Loop](#-agentic-loop)
- [Flags & Options](#-flags--options)
- [Usage Examples](#-usage-examples)
- [Performance](#-performance--optimization)
- [Zen MCP Multi-Model](#-zen-mcp-multi-model-orchestration)
- [Development Guide](#-development-guide)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [Support](#-support)

---

## 🎯 Overview

SuperClaude is a comprehensive AI-enhanced development framework designed specifically for Claude Code, featuring intelligent component loading, automatic update checking, and a powerful agentic loop system for quality-driven development.

### Key Capabilities

- **🤖 14 Core Agents + 100+ Extended Agents** - Specialized domain experts for every development need
- **🎭 5 Behavioral Modes** - Intelligent workflow adaptation based on task context
- **🛠️ 7 MCP Server Integrations** - Advanced capabilities including multi-model orchestration
- **💻 21 Slash Commands** - Comprehensive workflow coverage with `/sc:` namespace
- **🔄 Agentic Loop Pattern** - Automatic quality-driven iteration (0-100 scoring)
- **⚡ 67% Token Reduction** - Optimized from 30K to 10K tokens through conditional loading
- **📦 Multi-Platform Support** - PyPI, pipx, npm, and yarn installation methods

---

## ✨ What's New in 4.0.9

### 🎯 Zen MCP Multi-Model Orchestration (NEW)
- **Multi-Model Consensus** - Coordinate decisions across multiple AI models
- **Production Validation** - `--zen-review` for critical deployment verification
- **Deep Analysis** - `--thinkdeep` for multi-angle problem solving
- **API Key Management** - Automated setup script for multiple model providers
- **Integration Testing** - Comprehensive validation script for Zen MCP setup

### 🔧 MCP Installer Improvements
- Fixed critical bugs in MCP installation and update process
- Corrected npm package names and custom installation methods
- Added `claude` CLI as formal prerequisite for MCP management
- Enhanced reliability for server installations

### 🚀 Previous Major Features (4.0.7-4.0.8)
- **Automatic Update System** - Smart PyPI/NPM version checking
- **True Conditional Loading** - 67% token reduction achieved
- **Command Namespace** - All commands use `/sc:` prefix to prevent conflicts
- **14-Agent Architecture** - Specialized agents replacing legacy persona system
- **Quality Scoring** - Automatic 0-100 evaluation with iteration

---

## 🚀 Quick Start

### 2-Minute Installation

```bash
# Method 1: From PyPI (Recommended)
pip install SuperClaude
SuperClaude install

# Method 2: From Source
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude_Framework
pip install -e ".[dev]"
SuperClaude install
```

### Verify Installation

```bash
# Check version
SuperClaude --version  # Should show 4.0.9

# In Claude Code, test commands
--brainstorm           # Activates brainstorming mode
--delegate             # Auto-selects best agent
/sc:analyze            # Analysis command available
```

### Essential First Commands

| Task | Command |
|------|---------|
| Explore ideas | `--brainstorm` |
| Complex task | `--task-manage` |
| Find code | `--delegate` |
| Deep analysis | `--think 3` |
| Save tokens | `--uc` |

---

## 🏗️ Architecture

### Component Architecture

```
┌─────────────────────────────────────────────────────┐
│                   SuperClaude Core                   │
│                    (~3KB baseline)                   │
├─────────────────────────────────────────────────────┤
│                  Conditional Loading                 │
│         Components load only when triggered          │
├──────────┬──────────┬──────────┬──────────┬────────┤
│  Agents  │   MCP    │  Modes   │ Commands │ Flags  │
│   (14)   │   (6)    │   (5)    │   (21)   │  (8)   │
├──────────┴──────────┴──────────┴──────────┴────────┤
│                  Agentic Loop Engine                 │
│         Quality Scoring & Auto-Iteration             │
└─────────────────────────────────────────────────────┘
```

### Loading Strategy

| Component | Trigger | Token Cost |
|-----------|---------|------------|
| Baseline | Always | ~3,000 |
| Agents | `--delegate` or `Task()` | +1,500 |
| MCP Servers | Server usage | +500 each |
| Modes | Flag usage | +300 each |
| Full Framework | All features | ~15,000 |

---

## 📦 Core Components

### Framework Structure

```
SuperClaude_Framework/
├── SuperClaude/                # Python package
│   ├── Agents/                 # 14 core + 100+ extended agents
│   ├── Commands/               # 21 slash commands
│   ├── Core/                   # Framework essentials
│   ├── MCP/                    # Server configurations
│   └── Modes/                  # Behavioral modes
├── setup/                      # Installation system
│   ├── cli/                    # Command-line interface
│   ├── components/             # Component installers
│   └── utils/                  # Utilities & updater
├── Docs/                       # Documentation
└── ~/.claude/                  # Installed location
    ├── CLAUDE.md               # Entry point
    ├── CLAUDE_MINIMAL.md       # Core components
    ├── commands/sc/            # Command files
    └── *.md                    # Component files
```

---

## 🤖 Agent System

### 14 Core Specialized Agents

| Agent | Domain | Use Case |
|-------|--------|----------|
| **general-purpose** | Multi-domain | Unknown scope, exploration |
| **backend-architect** | Server Architecture | APIs, databases, scalability |
| **frontend-architect** | UI/UX Development | Components, accessibility |
| **python-expert** | Python Development | Advanced patterns, best practices |
| **security-engineer** | Security | Vulnerability assessment, OWASP |
| **performance-engineer** | Optimization | Bottlenecks, profiling |
| **quality-engineer** | Testing & QA | Coverage, edge cases |
| **devops-architect** | Infrastructure | CI/CD, deployment |
| **refactoring-expert** | Code Quality | Technical debt, cleanup |
| **root-cause-analyst** | Debugging | Error investigation |
| **requirements-analyst** | Planning | PRD analysis, scope |
| **technical-writer** | Documentation | API docs, guides |
| **learning-guide** | Education | Tutorials, mentoring |
| **socratic-mentor** | Teaching | Interactive learning |

### Extended Agent Categories (100+ Agents)

1. **Core Development** - UI, mobile, microservices, GraphQL
2. **Language Specialists** - Python, JS, Rust, Go, etc.
3. **Infrastructure** - Cloud, Kubernetes, Terraform
4. **Quality & Security** - Testing, auditing, compliance
5. **Data & AI** - ML, data engineering, LLM architecture
6. **Developer Experience** - Tooling, CLI, refactoring
7. **Specialized Domains** - Blockchain, IoT, FinTech
8. **Business & Product** - PM, technical writing, UX
9. **Meta-Orchestration** - Multi-agent coordination
10. **Research & Analysis** - Market research, competitive analysis

### Using Agents

```bash
# Auto-select best agent
--delegate

# Specific agent selection
Task(refactoring-expert)

# Multiple agents in parallel
--delegate --concurrency 3
```

---

## 🛠️ MCP Servers

### Available Servers

| Server | Purpose | When to Use |
|--------|---------|-------------|
| **filesystem** | Secure file operations | File management, I/O operations |
| **fetch** | Web content retrieval | Documentation, API data |
| **deepwiki** | Framework documentation | Library patterns, best practices |
| **sequential** | Complex reasoning | Multi-step analysis, debugging |
| **playwright** | Browser automation | E2E testing, UI validation |
| **serena** | Semantic analysis | Code understanding, memory |
| **zen** | Multi-model orchestration | Consensus decisions, production validation |

### MCP Configuration

```bash
# Enable specific server
--tools sequential

# Multiple servers
--tools "sequential,playwright"

# Zen MCP multi-model orchestration
--zen                    # Enable multi-model coordination
--consensus              # Multi-model consensus decisions
--zen-review             # Production validation with multiple models
--thinkdeep              # Deep multi-angle analysis

# All servers
--all-mcp

# Disable MCP
--no-mcp
```

---

## 🎭 Behavioral Modes

### 5 Intelligent Modes

| Mode | Flag | Purpose | Triggers |
|------|------|---------|----------|
| **Brainstorming** | `--brainstorm` | Collaborative discovery | Vague requests, exploration |
| **Task Management** | `--task-manage` | Multi-step coordination | >3 steps, complex scope |
| **Token Efficiency** | `--uc` | Context optimization | High usage, large operations |
| **Introspection** | `--introspect` | Self-analysis | Error recovery, reflection |
| **Orchestration** | Auto | Tool optimization | Multi-tool operations |

### Mode Examples

```bash
# Explore requirements
--brainstorm

# Complex project management
--task-manage --delegate

# Compressed output
--uc --loop

# Deep self-analysis
--introspect --think 3
```

---

## 💻 Command Reference

### 21 Slash Commands

#### Core Development
- `/sc:analyze` - Code analysis and review
- `/sc:build` - Build and compile operations
- `/sc:implement` - Feature implementation
- `/sc:refactor` - Code improvement
- `/sc:test` - Testing and validation

#### Documentation & Design
- `/sc:document` - Generate documentation
- `/sc:explain` - Code explanation
- `/sc:design` - Architecture design
- `/sc:estimate` - Time/effort estimation

#### Workflow Management
- `/sc:task` - Task management
- `/sc:spawn` - Parallel execution
- `/sc:brainstorm` - Interactive discovery
- `/sc:load` - Session loading
- `/sc:save` - Session saving

#### Quality & Maintenance
- `/sc:cleanup` - Code cleanup
- `/sc:improve` - Enhancement
- `/sc:troubleshoot` - Problem solving
- `/sc:git` - Version control

#### Utilities
- `/sc:index` - Code indexing
- `/sc:select-tool` - Tool selection
- `/sc:reflect` - Self-reflection

---

## 🔄 Agentic Loop

### Quality-Driven Iteration Pattern

The Agentic Loop implements automatic quality improvement through three-agent architecture:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │────▶│  Specialist  │────▶│  Evaluator   │
│   (Atlas)    │     │  (Mercury)   │     │   (Apollo)   │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                           │
       │                                           │
       └───────────── Iterate if <70 ─────────────┘
```

### Quality Scoring

| Score | Action | Description |
|-------|--------|-------------|
| **90-100** | ✅ Accept | Production-ready |
| **70-89** | ⚠️ Review | Acceptable with notes |
| **<70** | 🔄 Auto-retry | Automatic iteration |

### Using the Loop

```bash
# Basic iteration
--loop                    # Iterate until ≥70

# Custom threshold
--loop --quality 90       # Iterate until ≥90

# Limited iterations
--loop --iterations 5     # Max 5 attempts
```

### Quality Dimensions
- **Correctness** (40%) - Solves the problem
- **Completeness** (30%) - All requirements met
- **Code Quality** (20%) - Best practices
- **Performance** (10%) - Efficiency

---

## 🚩 Flags & Options

### Essential Flags

| Flag | Purpose | Usage |
|------|---------|-------|
| `--brainstorm` | Explore requirements | Vague requests |
| `--task-manage` | Track multi-step work | Complex tasks |
| `--think [1-3]` | Analysis depth | 1=quick, 3=deep |
| `--delegate` | Auto-select agent | Unknown scope |
| `--loop` | Quality iteration | Improvements |
| `--safe-mode` | Production safety | Critical ops |
| `--uc` | Token efficiency | Save context |
| `--tools [name]` | Enable MCP | Specific tools |
| `--zen` | Multi-model orchestration | Complex decisions |
| `--consensus` | Multi-model agreement | Critical choices |
| `--zen-review` | Production validation | Deployment safety |
| `--thinkdeep` | Multi-angle analysis | Complex problems |

### Advanced Options

```bash
# Parallel execution
--concurrency 3

# Analysis depth
--think-hard         # Deep analysis (~10K tokens)
--ultrathink         # Maximum depth (~32K tokens)

# Validation
--validate           # Pre-execution checks
--test               # Run tests after

# Update control
--auto-update        # Automatic updates
--no-update-check    # Skip update checks
```

---

## 📚 Usage Examples

### Common Workflows

#### New Feature Development
```bash
# Complete feature workflow
--brainstorm                # Explore requirements
--task-manage              # Plan implementation
--delegate                 # Find existing code
--test                     # Validate everything
```

#### Debug Complex Issue
```bash
# Deep debugging
--think 3 --delegate       # Analyze and investigate
--loop                     # Iterate until fixed
--test                     # Verify solution
```

#### Refactor Legacy Code
```bash
# Safe refactoring
--delegate                 # Use refactoring-expert
--safe-mode               # Maximum safety
--loop --quality 85       # High quality threshold
```

#### UI Component Creation
```bash
# Modern UI development
--tools fetch            # Or use /ui command
--delegate               # Frontend-architect
--test                   # Validate accessibility
```

#### Critical Decision Making
```bash
# Multi-model consensus for important choices
--consensus              # Get agreement from multiple models
--think 3                # Deep analysis first
--zen-review             # Production-grade validation
```

#### Production Deployment Validation
```bash
# Comprehensive production safety checks
--zen-review             # Multi-model validation
--safe-mode              # Maximum safety protocols
--test                   # Run all tests
```

### Power Combinations

```bash
# Maximum analysis
--think 3 --delegate --loop

# Safe production changes  
--safe-mode --loop --validate

# Efficient large operations
--task-manage --uc --delegate

# Complete feature with quality
--brainstorm --task-manage --loop --test

# Multi-model consensus for critical decisions
--consensus --think 3 --zen

# Production deployment validation
--zen-review --safe-mode --test

# Complex debugging with multi-model analysis
--thinkdeep --delegate --loop
```

---

## ⚡ Performance & Optimization

### Token Usage Optimization

| Scenario | Before | After | Reduction |
|----------|--------|-------|-----------|
| Baseline | 30,000 | 3,000 | 90% |
| With flags | 30,000 | 8,000 | 73% |
| Full framework | 30,000 | 15,000 | 50% |

### Loading Performance

- **Startup**: 67% faster initialization
- **Memory**: 67% reduction in baseline usage
- **Context**: More room for actual work
- **Efficiency**: True conditional loading

### Resource Zones

- **🟢 Green (0-75%)** - Full capabilities
- **🟡 Yellow (75-85%)** - Efficiency mode
- **🔴 Red (85%+)** - Essential only

---

## 🎯 Zen MCP Multi-Model Orchestration

### Overview

Zen MCP enables coordination across multiple AI models for enhanced decision-making, consensus building, and production validation. Perfect for critical decisions requiring multiple perspectives.

### Supported Models

| Provider | Models | API Key Required |
|----------|--------|------------------|
| **OpenAI** | GPT-4, GPT-3.5 | `OPENAI_API_KEY` |
| **Anthropic** | Claude-3 family | `ANTHROPIC_API_KEY` |
| **Google** | Gemini Pro/Ultra | `GEMINI_API_KEY` |
| **X.AI** | Grok models | `GROK_API_KEY` |
| **OpenRouter** | Multiple models | `OPENROUTER_API_KEY` |

### Quick Setup

```bash
# 1. Run the automated setup script
./scripts/setup_zen_api_keys.sh

# 2. Test the integration
./scripts/test_zen_integration.sh

# 3. Restart Claude Desktop

# 4. Test in Claude Code
--zen "Analyze this architecture decision"
```

### API Key Configuration

The setup script automatically configures your environment:

```bash
# Option 1: Interactive setup (recommended)
./scripts/setup_zen_api_keys.sh

# Option 2: Manual setup
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"  
export GEMINI_API_KEY="your-key-here"
export GROK_API_KEY="your-key-here"
export OPENROUTER_API_KEY="your-key-here"
```

### Usage Patterns

#### Multi-Model Consensus
```bash
# Get agreement from multiple models on critical decisions
--consensus "Should we migrate to microservices architecture?"

# Deep analysis with multiple perspectives  
--thinkdeep "Why is our system experiencing latency issues?"
```

#### Production Validation
```bash
# Validate deployment readiness with multiple models
--zen-review "Review this production deployment checklist"

# Architecture review with consensus
--consensus --think 3 "Evaluate this database schema design"
```

#### Enhanced Problem Solving
```bash
# Complex debugging with multi-model coordination
--thinkdeep --delegate "Debug this intermittent connection issue"

# Strategic planning with consensus
--consensus --brainstorm "Plan our technical debt reduction strategy"
```

### Integration Validation

Run the test script to verify your setup:

```bash
./scripts/test_zen_integration.sh
```

Expected output:
- ✅ Configuration files present
- ✅ API keys configured (minimum: OpenAI + Gemini)
- ✅ Zen MCP server installed
- ✅ SuperClaude Framework integration

### Troubleshooting

| Issue | Solution |
|-------|----------|
| API keys not found | Run `./scripts/setup_zen_api_keys.sh` |
| Zen flags not working | Restart Claude Desktop, check installation |
| Models not responding | Verify API keys are valid and have credits |
| Integration test fails | Check Claude Desktop config and restart |

---

## 🔧 Installation

### Requirements

- Python 3.8+
- Claude Code Desktop
- Internet connection for MCP servers

### Installation Methods

#### PyPI (Recommended)
```bash
pip install SuperClaude
SuperClaude install
```

#### From Source
```bash
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude_Framework
pip install -e ".[dev]"
SuperClaude install
```

#### Installation Profiles

```bash
# Quick installation (essentials only)
SuperClaude install --profile quick

# Developer installation (all features)
SuperClaude install --profile dev

# Custom components
SuperClaude install --components core,agents,mcp

# Preview installation
SuperClaude install --dry-run
```

### Update Management

```bash
# Check for updates
SuperClaude update --check

# Interactive update
SuperClaude update

# Automatic update
SuperClaude update --auto-update

# Backup before update
SuperClaude update --backup
```

### Environment Variables

```bash
# Enable automatic updates
export SUPERCLAUDE_AUTO_UPDATE=true

# Skip update checks
export SUPERCLAUDE_NO_UPDATE_CHECK=true
```

---

## 👨‍💻 Development Guide

### Creating Custom Agents

```markdown
# custom-agent.md
Agent: custom-specialist
Domain: Your Domain
Expertise: Specific skills

## Capabilities
- Capability 1
- Capability 2

## Tools
- Preferred tools
```

### Adding Custom Commands

```markdown
# ~/.claude/commands/sc/custom.md
Command: /sc:custom
Purpose: Your command purpose

## Usage
/sc:custom [options]

## Examples
/sc:custom --flag value
```

### Custom Behavioral Modes

```markdown
# MODE_Custom.md
# Custom Mode

## Activation Triggers
- Specific keywords
- Flag: --custom

## Behavioral Changes
- Changed behavior 1
- Changed behavior 2
```

### Framework Extension

```python
# Custom component installer
from setup.components import BaseComponent

class CustomComponent(BaseComponent):
    def install(self):
        # Installation logic
        pass
```

---

## 🔍 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `SuperClaude command not found` | Run `pip install -e ".[dev]"` again |
| Framework not loading | Check `ls ~/.claude/*.md` |
| Commands not working | Verify `/sc:` commands in `~/.claude/commands/sc/` |
| Update checks failing | Check internet and PyPI access |
| MCP servers not working | Run `SuperClaude install --components mcp` |
| Zen MCP not working | Run `./scripts/setup_zen_api_keys.sh` and restart Claude Desktop |
| Multi-model flags not recognized | Check Zen MCP installation with `./scripts/test_zen_integration.sh` |

### Diagnostic Commands

```bash
# Check installation
SuperClaude install --check

# Verify components
SuperClaude --version

# Test framework (in Claude Code)
--brainstorm
--delegate
/sc:analyze

# Check MCP servers
SuperClaude install --check-mcp

# Test Zen MCP integration
./scripts/test_zen_integration.sh
```

### Performance Issues

```bash
# High token usage
--uc                    # Enable compression
--safe-mode            # Conservative mode

# Slow responses
--no-mcp              # Disable MCP servers
--concurrency 1       # Reduce parallelism
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repository
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude_Framework

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Check code quality
ruff check .
black --check .
```

### Areas for Contribution

- 🤖 New specialized agents
- 🛠️ MCP server integrations
- 📚 Documentation improvements
- 🐛 Bug fixes and optimizations
- 🌍 Internationalization
- 🧪 Test coverage

---

## 💬 Support

### Getting Help

- **Documentation**: `Docs/` directory
- **Issues**: [GitHub Issues](https://github.com/SuperClaude-Org/SuperClaude_Framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SuperClaude-Org/SuperClaude_Framework/discussions)
- **Quick Help**: Use `--brainstorm` in Claude Code

### Resources

- [Installation Guide](Docs/Getting-Started/installation.md)
- [User Guide](Docs/User-Guide/README.md)
- [Developer Guide](Docs/Developer-Guide/README.md)
- [API Reference](Docs/Reference/README.md)
- [Examples Cookbook](Docs/Reference/examples-cookbook.md)

---

## 📊 Project Information

### Statistics

- **Current Version**: 4.0.9 (January 2025)
- **License**: MIT
- **Language**: Python 3.8+
- **Installation Time**: < 2 minutes
- **Memory Usage**: ~3KB baseline (67% reduction)
- **Commits**: 600+
- **Agents**: 14 core + 100+ extended
- **Commands**: 21 specialized
- **MCP Servers**: 7 integrated (including Zen multi-model)

### Maintainers

- **Anton Knoery** ([@NomenAK](https://github.com/NomenAK)) - Lead Developer
- **Mithun Gowda B** ([@mithun50](https://github.com/mithun50)) - Core Contributor

### Links

- **Repository**: [GitHub](https://github.com/SuperClaude-Org/SuperClaude_Framework)
- **PyPI Package**: [SuperClaude](https://pypi.org/project/SuperClaude/)
- **Documentation**: [Docs](https://github.com/SuperClaude-Org/SuperClaude_Framework/tree/main/Docs)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

### Acknowledgments

- **Claude Code Team** - Amazing development environment
- **Anthropic** - Claude AI capabilities
- **MCP Community** - Server integrations
- **Open Source Contributors** - Ideas and feedback
- **21st.dev** - UI component patterns

---

<div align="center">

**SuperClaude Framework v4.0.9**

*AI-Enhanced Development for Claude Code*

*Powered by Intelligent Agents • Dynamic Loading • Quality-Driven Iteration*

**Copyright © 2025 SuperClaude-Org • MIT License**

Made with ❤️ for developers

</div>