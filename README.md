# SuperClaude Framework v2.0 - Simplified & Enhanced

## 🚀 Overview

SuperClaude v2.0 introduces **55% reduction in complexity** while maintaining all powerful features. This streamlined version provides clearer decision paths, simplified flags, and consolidated documentation for enhanced developer experience.

### What's New in v2.0

#### 📉 **55% Smaller, 100% Powerful**
- Reduced from 50+ flags to **8 essential flags**
- Consolidated documentation from 10K to 4.5K words
- Unified tool reference in single `TOOLS.md` file
- Streamlined rules focusing on core workflow

#### ⚡ **Instant Decision Making**
- New **QUICKSTART.md** with practical scenarios
- **CHEATSHEET.md** for instant command reference
- Clear decision trees replacing complex rules
- Table-based documentation over verbose paragraphs

#### 🎯 **Quality-Driven Execution**
- Automatic quality evaluation (0-100 scoring)
- Auto-iteration when quality < 70
- Simplified thresholds: 90+ (accept), 70-89 (review), <70 (retry)

## 📋 Core Components

### Essential Files (Simplified v2.0)

```
SuperClaude/Core/
├── QUICKSTART.md      # Start here - practical scenarios
├── CHEATSHEET.md      # Instant command reference
├── FLAGS.md           # 8 essential flags only
├── PRINCIPLES.md      # Core engineering philosophy
├── RULES.md           # Streamlined workflow rules
├── TOOLS.md           # NEW: Unified tool/agent reference
└── AGENTS.md          # Quality-driven agent framework
```

### Behavioral Modes
- **Brainstorming**: Collaborative discovery (`--brainstorm`)
- **Task Management**: Multi-step operations (`--task-manage`)
- **Token Efficiency**: Context optimization (`--uc`)
- **Introspection**: Self-analysis (`--introspect`)
- **Orchestration**: Tool optimization (auto-activated)

## 🎯 Essential Flags (Only 8!)

| Flag | Purpose | When to Use |
|------|---------|-------------|
| `--brainstorm` | Explore requirements | Vague requests |
| `--task-manage` | Track multi-step work | >3 steps |
| `--think [1-3]` | Analysis depth | 1=quick, 3=deep |
| `--delegate` | Auto-select best agent | Unknown scope |
| `--loop` | Iterate until quality ≥70 | Improvements needed |
| `--safe-mode` | Production safety | Critical operations |
| `--uc` | Save tokens | High context usage |
| `--tools [name]` | Enable specific MCP | Tool-specific needs |

## 🚀 Quick Start Examples

### Most Common Scenarios

#### "I need to build something new"
```bash
--brainstorm                # Explore requirements
--task-manage              # Plan implementation  
--delegate                 # Auto-select best tools
```

#### "My code is broken"
```bash
--think 2                  # Analyze the issue
--delegate                 # Uses root-cause-analyst
--test                     # Verify fixes
```

#### "I need a UI component"
```bash
--tools magic              # Or use /ui command
# Creates modern, accessible components
```

#### "I want to improve code"
```bash
--delegate                 # Uses refactoring-expert
--loop                     # Iterate until quality ≥70
```

## 🛠️ Unified Tool Reference

### Task Agents (Auto-Selected with `--delegate`)

| Agent | Use Case |
|-------|----------|
| **general-purpose** | Unknown scope, exploration |
| **root-cause-analyst** | Debugging, error investigation |
| **refactoring-expert** | Code improvements, cleanup |
| **quality-engineer** | Test coverage, quality metrics |
| **technical-writer** | Documentation generation |
| **performance-engineer** | Optimization, bottlenecks |
| **frontend-architect** | UI/UX implementation |
| **backend-architect** | API design, server patterns |
| **security-engineer** | Security audits, compliance |

### MCP Servers (Enable with `--tools [name]`)

| Server | Purpose |
|--------|---------|
| **magic** | UI components from 21st.dev |
| **deepwiki** | Framework documentation |
| **sequential** | Complex analysis & reasoning |
| **serena** | Symbol operations, project memory |
| **morphllm** | Pattern-based bulk edits |
| **playwright** | Browser testing & automation |

## 📊 Quality Scoring System

Every output is automatically evaluated:

| Score | Action | Description |
|-------|--------|-------------|
| **90-100** | ✅ Accept | Production-ready |
| **70-89** | ⚠️ Review | Acceptable with notes |
| **<70** | 🔄 Auto-retry | Automatic iteration |

Quality dimensions:
- **Correctness** (40%): Does it solve the problem?
- **Completeness** (30%): All requirements met?
- **Code Quality** (20%): Best practices followed?
- **Performance** (10%): Efficient implementation?

## 🔄 The 5-Step Workflow

```
1. Check     → git status (always start here)
2. Plan      → Use flags based on task type
3. Execute   → Tools auto-selected or use --delegate
4. Validate  → Quality score evaluated automatically
5. Iterate   → Auto-retry if quality < 70
```

## 💡 Power Combinations

```bash
# Maximum analysis
--think 3 --delegate

# Safe production changes
--safe-mode --loop

# Efficient large operations
--task-manage --uc

# Complete feature development
--brainstorm --task-manage --test
```

## 📖 Command Reference

### Core Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `/sc:analyze` | Code analysis | `/sc:analyze --focus security` |
| `/sc:document` | Generate docs | `/sc:document --type api` |
| `/sc:refactor` | Improve code | `/sc:refactor --preserve tests` |
| `/sc:test` | Run tests | `/sc:test --coverage 90` |
| `/sc:debug` | Debug issues | `/sc:debug --delegate` |

### UI/UX Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `/ui` | Create UI component | `/ui login-form` |
| `/21` | Search 21st.dev | `/21 data-table` |
| `/logo` | Get company logos | `/logo github --format svg` |

## ✅ Golden Rules

### Always Do
- ✅ Start with `git status`
- ✅ Use TodoWrite for >3 steps
- ✅ Work on feature branches
- ✅ Let quality scores guide iteration

### Never Do
- ❌ Work on main/master
- ❌ Skip failing tests
- ❌ Leave TODO comments
- ❌ Add features not requested

## 🎓 Getting Started

### Beginner Path
1. Start with `--brainstorm` for any new task
2. Use `--delegate` to auto-select tools
3. Let quality scores guide your work

### Intermediate Path
1. Learn the 8 essential flags
2. Understand Task agents and MCP servers
3. Use power combinations for efficiency

### Advanced Path
1. Master flag combinations
2. Optimize with `--uc` for large operations
3. Create custom workflows with command chaining

## 📁 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/SuperClaude_Framework.git

# Navigate to the directory
cd SuperClaude_Framework

# Copy core files to Claude directory
cp -r SuperClaude/Core/* ~/.claude/

# Update your CLAUDE.md
cat > ~/.claude/CLAUDE.md << 'EOF'
# SuperClaude Entry Point

# Quick Start
@QUICKSTART.md
@CHEATSHEET.md

# Core Framework
@FLAGS.md
@PRINCIPLES.md
@RULES.md

# Tool & Agent Reference
@TOOLS.md
@AGENTS.md

# Behavioral Modes
@MODE_Brainstorming.md
@MODE_Introspection.md
@MODE_Orchestration.md
@MODE_Task_Management.md
@MODE_Token_Efficiency.md
EOF
```

## 🔧 Customization

### Adjust Quality Thresholds
Edit quality scoring in `AGENTS.md`:
```yaml
quality_criteria:
  min_score: 70  # Change to 80 for higher standards
  auto_iterate: true
```

### Add Custom Flags
Extend `FLAGS.md` with your own:
```markdown
**--custom-flag**
- Trigger: Your specific needs
- Behavior: What it does
```

### Create New Modes
Add `MODE_YourMode.md` files for custom behaviors.

## 🆘 Getting Help

### Quick Help
- **Lost?** → Use `--brainstorm`
- **Complex task?** → Use `--task-manage`
- **Unknown files?** → Use `--delegate`
- **Need analysis?** → Use `--think 2`
- **High context?** → Use `--uc`

### Command Help
```bash
/help                    # General help
/help [command]         # Command-specific help
/feedback               # Report issues
```

## 📊 What's Been Simplified

### Before (v1.0)
- 50+ flags with complex formulas
- 10,000+ words of documentation
- Scattered agent information
- Redundant quality systems
- Complex mathematical triggers

### After (v2.0)
- 8 essential flags only
- 4,500 words total
- Unified TOOLS.md reference
- Single quality system
- Simple decision tables

## 🚦 Migration from v1.0

### Flag Changes
| Old | New |
|-----|-----|
| `--think`, `--think-hard`, `--ultrathink` | `--think [1-3]` |
| `--delegate-search`, `--delegate-debug`, etc. | `--delegate` (auto-selects) |
| 30+ MCP flags | `--tools [name]` |
| Complex triggers | Simple conditions |

### File Changes
- Multiple MCP docs → Single `TOOLS.md`
- Verbose `RULES.md` → Streamlined version
- Complex `FLAGS.md` → 8 essential flags
- Added `QUICKSTART.md` and `CHEATSHEET.md`

## 💾 Backup Your Configuration

```bash
# Backup current setup
cd ~/Desktop/SuperClaude_Framework
git checkout -b v2-simplified
git add .
git commit -m "feat: SuperClaude v2.0 simplified"
git push origin v2-simplified
```

## 📚 Learn More

- **QUICKSTART.md**: Practical scenarios and examples
- **CHEATSHEET.md**: Instant command reference
- **TOOLS.md**: Complete tool and agent catalog
- **PRINCIPLES.md**: Engineering philosophy
- **RULES.md**: Core workflow rules

## 🎉 Key Benefits of v2.0

1. **Faster Onboarding**: Start productive in minutes, not hours
2. **Clearer Decisions**: Simple tables and decision trees
3. **Less Cognitive Load**: 55% less to remember
4. **Same Power**: All features preserved, just simplified
5. **Better Performance**: Reduced token usage

---

*SuperClaude Framework v2.0 - Simplified for Clarity, Enhanced for Power*
*Last Updated: August 2025*

## Contributors

- Framework simplification and v2.0 enhancements
- Quality-driven execution system
- Unified documentation structure

## License

MIT License - See LICENSE file for details