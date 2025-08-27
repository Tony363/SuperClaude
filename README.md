# SuperClaude Framework - Complete Command Reference & Documentation

## 🚀 Overview

SuperClaude is an advanced framework for Claude Code that introduces **quality-driven agentic loops**, systematic task management, and intelligent agent delegation. This framework enhances Claude Code with specialized behaviors, commands, and multi-agent coordination capabilities.

### 🎯 Core Features

- **30+ Slash Commands**: Comprehensive command system for all development workflows
- **Quality Evaluation System**: Automatic 0-100 scoring with mandatory iteration when quality < 70
- **15+ Specialized Agents**: Domain experts for every aspect of development
- **MCP Server Integration**: 7 specialized servers for enhanced capabilities
- **Behavioral Modes**: 5 operational modes that adapt to context
- **Agentic Loop Implementation**: Execute → Evaluate → Iterate pattern with context preservation

### 📦 Framework Components

```
SuperClaude Framework
├── Commands (30+)      # /sc:* slash commands
├── Agents (15+)        # Specialized task agents
├── Modes (5)           # Behavioral modes
├── MCP Servers (7)     # Enhanced capabilities
├── Flags (20+)         # Behavior modifiers
└── Rules & Principles  # Core framework logic
```

## 📚 Complete Slash Commands Reference

The SuperClaude framework provides **30+ specialized slash commands** organized into categories. All commands follow the pattern `/sc:[command]` and support quality evaluation, automatic iteration, and flag combinations.

### 🛠️ Core Commands

#### `/sc:analyze` - Code Analysis & Quality Assessment
```bash
/sc:analyze [target] [--focus quality|security|performance|architecture] [--depth quick|deep] [--format text|json|report] [--delegate]

# Purpose: Comprehensive code analysis with quality evaluation
# MCP Servers: None (can use Sequential with --think flags)
# Quality: Auto-evaluates output quality 0-100, iterates if <70

# Examples:
/sc:analyze                                              # Full project analysis
/sc:analyze src/auth --focus security --depth deep       # Security audit
/sc:analyze --focus performance --delegate               # Delegate to performance-engineer
/sc:analyze backend/ --focus architecture --format report # Architecture review with report
/sc:analyze --think-hard --all-mcp                      # Deep analysis with all MCP tools
```

#### `/sc:explain` - Code & Concept Explanation
```bash
/sc:explain [target] [--level basic|intermediate|advanced] [--format text|examples|interactive] [--context domain]

# Purpose: Educational explanations tailored to audience level
# MCP Servers: Sequential, Context7
# Quality: Clarity and completeness scored, auto-enhanced if needed

# Examples:
/sc:explain authentication.js --level basic              # Beginner-friendly explanation
/sc:explain react-hooks --context react --format examples # Framework-specific with examples
/sc:explain jwt --context security                       # Security concept explanation
/sc:explain design-patterns --level advanced             # Advanced pattern discussion
```

#### `/sc:document` - Comprehensive Documentation Generation
```bash
/sc:document [target] [--type inline|external|api|guide|readme] [--style brief|detailed] [--format md|jsdoc|typedoc|openapi|swagger]

# Purpose: Generate all types of documentation with multi-format support
# MCP Servers: None (basic utility)
# Quality: Completeness and accuracy evaluated

# Examples:
/sc:document src/api --type api --format openapi         # OpenAPI 3.0 specification
/sc:document components/ --type external --style detailed # Component library docs
/sc:document payment --type guide --format md            # User guide in markdown
/sc:document . --type readme --style detailed            # Comprehensive README
/sc:document src/auth --type inline --format jsdoc       # JSDoc inline comments
```

**Documentation Types:**
- `inline`: Add comments directly in code (JSDoc, docstrings)
- `external`: Separate documentation files (markdown, HTML)
- `api`: API reference documentation (OpenAPI, Swagger)
- `guide`: User guides and tutorials
- `readme`: Project README files

#### `/sc:load` - Load Project Context & Session State
```bash
/sc:load [project] [--type project|config|deps|checkpoint] [--memory all|recent|specific] [--refresh] [--analyze]

# Purpose: Load saved project context, memories, and session state
# MCP Servers: Serena (for memory persistence)
# Integration: Works with Serena MCP for cross-session persistence

# Examples:
/sc:load                                                  # Load current project
/sc:load auth-project --memory recent                    # Load project with recent memories
/sc:load --type checkpoint                               # Load last checkpoint
/sc:load myproject --refresh --analyze                   # Fresh load with analysis
```

#### `/sc:save` - Save Project Context & Session
```bash
/sc:save [--type session|learnings|context|all] [--checkpoint] [--compress] [--tag label] [--summarize]

# Purpose: Save current work state, memories, and context
# MCP Servers: Serena (for memory persistence)
# Quality: Validates completeness before saving

# Examples:
/sc:save                                                  # Standard save
/sc:save --checkpoint --tag "auth-complete"              # Tagged checkpoint
/sc:save --type learnings --summarize                    # Save key learnings
/sc:save --compress --type all                           # Compressed full save
```

### 📋 Task Management Commands

#### `/sc:brainstorm` - Interactive Requirements Discovery
```bash
/sc:brainstorm [topic] [--strategy systematic|agile|enterprise] [--depth shallow|normal|deep] [--mode explore|define|refine] [--parallel]

# Purpose: Collaborative discovery through Socratic dialogue
# MCP Servers: All 6 servers available (Sequential, Context7, Magic, Playwright, Morphllm, Serena)
# Personas: Activated based on discovery needs

# Examples:
/sc:brainstorm "user dashboard"                          # Explore dashboard ideas
/sc:brainstorm "api design" --strategy enterprise        # Enterprise API planning
/sc:brainstorm --mode define --depth deep                # Deep requirements definition
/sc:brainstorm "payment system" --parallel               # Parallel exploration paths
```

#### `/sc:task` - Execute Complex Tasks with Delegation
```bash
/sc:task [description] [--strategy systematic|agile|enterprise] [--parallel] [--delegate] [--quality threshold]

# Purpose: Complex task execution with intelligent workflow management
# MCP Servers: All 6 servers for comprehensive capability
# Quality: Each subtask evaluated, auto-iteration if <70

# Examples:
/sc:task "implement authentication" --strategy systematic # Systematic implementation
/sc:task "refactor codebase" --parallel --delegate       # Parallel refactoring
/sc:task "add feature" --quality 85                      # High quality requirement
/sc:task "debug api" --delegate root-cause-analyst       # Specific agent delegation
```

#### `/sc:workflow` - Generate Implementation Workflows
```bash
/sc:workflow [requirement] [--strategy systematic|agile|enterprise] [--depth shallow|normal|deep] [--parallel]

# Purpose: Generate structured workflows from PRDs and requirements
# MCP Servers: All 6 servers for comprehensive planning
# Output: Structured task hierarchy with dependencies

# Examples:
/sc:workflow "payment integration" --strategy agile      # Agile workflow generation
/sc:workflow prd.md --depth deep --parallel              # Deep PRD analysis
/sc:workflow "user management" --strategy enterprise     # Enterprise workflow
```

#### `/sc:spawn` - Meta-System Task Orchestration
```bash
/sc:spawn [meta-task] [--strategy sequential|parallel|adaptive] [--depth normal|deep]

# Purpose: Break down meta-tasks into coordinated subtasks
# MCP Servers: None (orchestration-focused)
# Behavior: Intelligent task breakdown and delegation

# Examples:
/sc:spawn "redesign architecture" --strategy adaptive    # Adaptive task breakdown
/sc:spawn "migrate to microservices" --depth deep        # Deep migration planning
/sc:spawn "optimize everything" --strategy parallel      # Parallel optimization
```

### 🔨 Development Commands

#### `/sc:implement` - Feature Implementation
```bash
/sc:implement [feature] [--type component|api|service|feature] [--framework react|vue|express|angular] [--safe] [--with-tests]

# Purpose: Feature implementation with persona activation
# MCP Servers: Context7, Sequential, Magic, Playwright
# Personas: architect, frontend, backend, security, qa-specialist

# Examples:
/sc:implement "user auth" --framework react --with-tests # React auth with tests
/sc:implement "REST API" --type api --safe               # Safe API implementation
/sc:implement "dashboard" --type component               # Component implementation
/sc:implement "payment" --framework express --safe       # Secure payment service
```

#### `/sc:build` - Build & Compile Projects
```bash
/sc:build [target] [--type dev|prod|test] [--clean] [--optimize] [--verbose]

# Purpose: Build, compile, and package with error handling
# MCP Servers: Playwright (for validation)
# Features: Intelligent error resolution, optimization

# Examples:
/sc:build --type prod --optimize                         # Production build
/sc:build frontend --clean --verbose                     # Clean frontend build
/sc:build --type test                                    # Test build
/sc:build backend --type dev --verbose                   # Development build with details
```

#### `/sc:test` - Testing & Validation
```bash
/sc:test [target] [--type unit|integration|e2e|all] [--coverage target] [--watch] [--fix]

# Purpose: Execute tests with coverage analysis
# MCP Servers: Playwright (for browser testing)
# Quality: Coverage and test quality evaluated

# Examples:
/sc:test                                                  # Run all tests
/sc:test auth --type unit --coverage 90                  # Unit tests with 90% coverage
/sc:test --type e2e --watch                              # E2E tests with watch mode
/sc:test api --fix                                       # Fix test issues
```

#### `/sc:improve` - Code Improvement
```bash
/sc:improve [target] [--type quality|performance|maintainability|style] [--safe] [--interactive]

# Purpose: Systematic code improvements
# MCP Servers: Sequential, Context7
# Quality: Improvement impact measured and validated

# Examples:
/sc:improve src/ --type quality --safe                   # Safe quality improvements
/sc:improve database --type performance                  # Performance optimization
/sc:improve --type maintainability --interactive         # Interactive refactoring
/sc:improve styles --type style                          # Style improvements
```

### 🔍 Analysis & Debugging Commands

#### `/sc:troubleshoot` - Issue Diagnosis & Resolution
```bash
/sc:troubleshoot [issue] [--type bug|build|performance|deployment] [--trace] [--fix]

# Purpose: Diagnose and resolve various issues
# MCP Servers: None (uses native debugging)
# Approach: Systematic root cause analysis

# Examples:
/sc:troubleshoot "API returns 500" --type bug --trace    # Bug investigation
/sc:troubleshoot "build fails" --fix                     # Build issue with fix
/sc:troubleshoot "slow queries" --type performance       # Performance debugging
/sc:troubleshoot deployment --trace                      # Deployment investigation
```

#### `/sc:estimate` - Development Estimation
```bash
/sc:estimate [task] [--type time|effort|complexity] [--unit hours|days|weeks] [--breakdown]

# Purpose: Provide intelligent development estimates
# MCP Servers: Sequential, Context7
# Analysis: Complexity scoring and risk assessment

# Examples:
/sc:estimate "auth system" --type time --unit days       # Time estimate in days
/sc:estimate feature.md --breakdown                      # Detailed breakdown
/sc:estimate "refactoring" --type complexity             # Complexity assessment
/sc:estimate project --type effort --unit weeks          # Effort in weeks
```

#### `/sc:reflect` - Task Reflection & Validation
```bash
/sc:reflect [--type task|session|completion] [--analyze] [--validate]

# Purpose: Reflect on work and validate completeness
# MCP Servers: Serena (think_about_* tools)
# Output: Insights and validation results

# Examples:
/sc:reflect --type task --analyze                        # Analyze current task
/sc:reflect --type session --validate                    # Validate session work
/sc:reflect --type completion                            # Completion assessment
```

### 🧹 Utility Commands

#### `/sc:cleanup` - Code & Workspace Cleanup
```bash
/sc:cleanup [target] [--type code|imports|files|all] [--safe|--aggressive] [--interactive]

# Purpose: Clean up code, remove dead code, optimize structure
# MCP Servers: Sequential, Context7
# Safety: Multiple safety levels available

# Examples:
/sc:cleanup --type imports --safe                        # Safe import cleanup
/sc:cleanup src/ --type code --interactive               # Interactive code cleanup
/sc:cleanup --type all --aggressive                      # Aggressive full cleanup
/sc:cleanup tests --type files                           # File organization cleanup
```

#### `/sc:git` - Git Operations
```bash
/sc:git [operation] [args] [--smart-commit] [--interactive]

# Purpose: Git operations with intelligent commit messages
# MCP Servers: None (native git)
# Features: Smart commits, workflow optimization

# Examples:
/sc:git commit --smart-commit                            # Intelligent commit message
/sc:git status                                           # Enhanced status display
/sc:git branch feature/auth                              # Branch management
/sc:git push --interactive                               # Interactive push workflow
```

#### `/sc:design` - Design System Architecture
```bash
/sc:design [target] [--type architecture|api|component|database] [--format diagram|spec|code]

# Purpose: Design system architecture and interfaces
# MCP Servers: None (design-focused)
# Output: Comprehensive design specifications

# Examples:
/sc:design system --type architecture --format diagram   # Architecture diagram
/sc:design api --type api --format spec                  # API specification
/sc:design UserAuth --type component                     # Component design
/sc:design schema --type database --format code          # Database schema
```

### 🎓 Learning & Documentation Commands

#### `/sc:index` - Project Documentation Index
```bash
/sc:index [target] [--type docs|api|structure|readme] [--format md|json|yaml]

# Purpose: Generate comprehensive project documentation
# MCP Servers: Sequential, Context7
# Features: Intelligent organization, cross-referencing

# Examples:
/sc:index . --type structure --format md                 # Project structure docs
/sc:index src/api --type api --format json               # API documentation
/sc:index project --type readme                          # README generation
/sc:index --type docs --format yaml                      # Full documentation index
```

#### `/sc:select-tool` - Intelligent Tool Selection
```bash
/sc:select-tool [operation] [--analyze] [--explain]

# Purpose: Select optimal MCP tools for operations
# MCP Servers: Serena, Morphllm
# Analysis: Complexity scoring and tool matching

# Examples:
/sc:select-tool "refactor auth module" --analyze         # Analyze tool needs
/sc:select-tool "debug performance" --explain            # Explain tool choice
/sc:select-tool "implement UI" --analyze --explain       # Full analysis
```

## 🎯 Flag System

Flags modify command behavior and can be combined for enhanced functionality:

### Mode Activation Flags

| Flag | Purpose | Triggers | Example |
|------|---------|----------|---------|
| `--brainstorm` | Collaborative discovery | Vague requirements | `/sc:task --brainstorm` |
| `--introspect` | Self-analysis mode | Error recovery | `/sc:analyze --introspect` |
| `--task-manage` | Task management | Complex operations | `/sc:implement --task-manage` |
| `--orchestrate` | Tool optimization | Multi-tool ops | `/sc:build --orchestrate` |
| `--token-efficient` / `--uc` | Compressed output | High context usage | `/sc:explain --uc` |

### Quality & Iteration Flags

| Flag | Purpose | Default | Example |
|------|---------|---------|---------|
| `--loop` | Enable quality iteration | Off | `/sc:implement --loop` |
| `--iterations [n]` | Max iterations | 3 | `--iterations 5` |
| `--quality [n]` | Quality threshold | 70 | `--quality 85` |
| `--delegate` | Auto-delegation | Off | `/sc:task --delegate` |

### Analysis Depth Flags

| Flag | Token Usage | Use Case | Example |
|------|-------------|----------|---------|
| `--think` | ~4K tokens | Multi-component | `/sc:analyze --think` |
| `--think-hard` | ~10K tokens | Architecture | `/sc:design --think-hard` |
| `--ultrathink` | ~32K tokens | System redesign | `/sc:spawn --ultrathink` |

### MCP Server Control Flags

| Flag | Purpose | Server | Example |
|------|---------|--------|---------|
| `--dw` / `--deepwiki` | Documentation | Deepwiki | `/sc:explain --dw` |
| `--seq` / `--sequential` | Complex reasoning | Sequential | `/sc:analyze --seq` |
| `--magic` | UI components | Magic | `/sc:implement --magic` |
| `--morph` / `--morphllm` | Pattern edits | Morphllm | `/sc:improve --morph` |
| `--serena` | Symbol operations | Serena | `/sc:load --serena` |
| `--play` / `--playwright` | Browser testing | Playwright | `/sc:test --play` |
| `--all-mcp` | Enable all servers | All | `/sc:task --all-mcp` |
| `--no-mcp` | Disable all servers | None | `/sc:analyze --no-mcp` |

## 🤖 Task Agent Catalog

SuperClaude includes 15+ specialized agents for delegation:

### Discovery & Analysis Agents
- **general-purpose**: Unknown scope exploration, broad searches
- **root-cause-analyst**: Debugging, error investigation, performance bottlenecks

### Code Quality & Improvement Agents
- **refactoring-expert**: Technical debt reduction, code cleanup
- **quality-engineer**: Test coverage, edge case detection, quality metrics
- **performance-engineer**: Optimization, bottleneck identification

### Documentation & Planning Agents
- **technical-writer**: API docs, user guides, comprehensive documentation
- **requirements-analyst**: PRD analysis, feature scoping, requirement discovery
- **learning-guide**: Tutorial creation, educational content

### Architecture & Design Agents
- **system-architect**: System design, scalability planning, architecture decisions
- **backend-architect**: API design, database architecture, server patterns
- **frontend-architect**: UI/UX implementation, component architecture
- **python-expert**: Python-specific development expertise

### Specialized Operations Agents
- **security-engineer**: Security audits, vulnerability assessment
- **devops-architect**: Infrastructure, CI/CD, deployment strategies
- **socratic-mentor**: Teaching through questions, concept exploration

## 📊 Quality Evaluation System

All Task agent outputs are evaluated on a 0-100 scale:

### Scoring Dimensions
- **Correctness** (40%): Does it solve the stated problem?
- **Completeness** (30%): Are all requirements addressed?
- **Code Quality** (20%): Maintainability, readability, best practices
- **Performance** (10%): Efficiency and resource usage

### Action Thresholds
| Score Range | Action | Description |
|------------|--------|-------------|
| 90-100 | ✅ Accept | Production-ready |
| 70-89 | ⚠️ Review | Acceptable with notes |
| 50-69 | 🔄 Iterate | Auto-iteration required |
| 0-49 | ❌ Reject | Fundamental issues |

## 🔄 Agentic Loop Workflow

```
Task Request → Delegate to Agent → Execute Task → Evaluate Quality (0-100)
     ↑                                                      ↓
     ←── Enhance Context ← Generate Feedback ← If Quality < 70
```

## 💾 MCP Server Integration

SuperClaude integrates with 7 specialized MCP servers:

| Server | Purpose | Commands Using | Capabilities |
|--------|---------|---------------|--------------|
| **Sequential** | Complex reasoning | analyze, explain, task | Multi-step analysis, hypothesis testing |
| **Context7** | Framework patterns | implement, improve | React, Vue, Angular patterns |
| **Magic** | UI components | implement, UI commands | 21st.dev patterns, design systems |
| **Playwright** | Browser testing | test, build | E2E testing, browser automation |
| **Morphllm** | Pattern edits | improve, select-tool | Bulk edits, refactoring |
| **Serena** | Symbol operations | load, save, reflect | Code navigation, memory |
| **Deepwiki** | Documentation | explain, document | Library docs, examples |

## 🚀 Quick Start Examples

### Complete Feature Development Workflow
```bash
# 1. Discovery & Planning
/sc:brainstorm "user dashboard" --mode explore
/sc:workflow "dashboard requirements" --strategy agile

# 2. Implementation
/sc:implement "dashboard layout" --framework react --with-tests
/sc:implement "api endpoints" --type api --safe

# 3. Quality & Testing
/sc:test --type unit --coverage 90
/sc:analyze --focus security --depth deep

# 4. Documentation & Save
/sc:document . --type api --format openapi
/sc:save --checkpoint --tag "dashboard-v1"
```

### Debugging Workflow
```bash
# 1. Initial Investigation
/sc:troubleshoot "API errors" --type bug --trace

# 2. Deep Analysis
/sc:analyze api/ --focus performance --think-hard

# 3. Fix Implementation
/sc:improve api/ --type performance --safe

# 4. Validation
/sc:test api --type integration
/sc:reflect --type task --validate
```

### Learning & Documentation Flow
```bash
# 1. Understand Existing Code
/sc:explain src/services --level intermediate

# 2. Generate Documentation
/sc:document . --type guide --style detailed
/sc:index project --type structure

# 3. Create Learning Materials
/sc:explain "how to use API" --format examples
```

## 📁 File Structure

```
~/.claude/
├── CLAUDE.md              # Entry point (imports all components)
├── FLAGS.md               # Behavioral flags and triggers
├── RULES.md               # Enhanced with quality controls
├── PRINCIPLES.md          # Core engineering philosophy
├── MODE_*.md              # 5 Operational modes
├── MCP_*.md               # 7 MCP server configurations
└── AGENTS.md              # 15+ Agent specifications

/SuperClaude_Framework/
├── SuperClaude/
│   ├── Commands/         # 30+ command definitions
│   ├── Agents/          # Agent specifications
│   ├── Modes/           # Behavioral modes
│   └── MCP/             # MCP configurations
├── Docs/                # Documentation
└── setup/              # Installation tools
```

## 🔧 Installation & Setup

### Prerequisites
- Claude Code CLI installed
- Python 3.8+ (for framework installation)
- MCP servers configured (optional, for enhanced features)

### Installation
```bash
# Install SuperClaude framework
python3 -m pip install SuperClaude

# Or from source
git clone https://github.com/yourusername/SuperClaude_Framework
cd SuperClaude_Framework
python3 -m SuperClaude install

# Verify installation
python3 -m SuperClaude --version
```

### Testing Your Setup
```bash
# In Terminal - Verify installation
python3 -m SuperClaude --version

# In Claude Code - Test commands
/sc:brainstorm "test project"    # Should start discovery
/sc:analyze README.md            # Should provide analysis
/sc:help                        # Should list commands
```

## 🆘 Troubleshooting

### Common Issues

**Commands not working:**
- Verify installation: `python3 -m SuperClaude --version`
- Check Claude Code has access to ~/.claude directory
- Ensure command format is correct: `/sc:command` not `/sc command`

**Quality scores too low:**
- Check correct agent type selected
- Enhance context with more details
- Break complex tasks into subtasks
- Adjust threshold: `--quality 70`

**MCP servers not available:**
- Check server configuration in Claude Code settings
- Verify server installation
- Use `--no-mcp` flag as fallback

## 📚 Additional Resources

- **User Guide**: Detailed usage instructions for all commands
- **Developer Guide**: Contributing and extending the framework
- **API Reference**: Complete command and flag documentation
- **Examples Cookbook**: Real-world usage examples and patterns
- **Troubleshooting Guide**: Solutions to common issues

## 🤝 Contributing

SuperClaude is open source and welcomes contributions:
- Report issues: [GitHub Issues](https://github.com/anthropics/claude-code/issues)
- Submit PRs: Follow contribution guidelines
- Share feedback: `/feedback` command in Claude Code

## 📄 License

SuperClaude Framework is released under the MIT License.

---

*SuperClaude Framework - Enhanced Claude Code with Quality-Driven Development*
*Version: 4.0.8 | Last Updated: 2025*