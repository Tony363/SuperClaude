# SuperClaude Quick Start Guide

Get up and running with SuperClaude in 5 minutes.

## Prerequisites

- Python 3.10+
- Claude Code CLI
- Git

## Installation

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

## Basic Usage

### Start Claude Code

```bash
claude
```

### Your First Command

Analyze a file:
```bash
/sc:analyze src/main.py
```

Implement a feature:
```bash
/sc:implement "Add input validation to the login function"
```

Run tests:
```bash
/sc:test --coverage
```

## Common Workflows

### Feature Development

```bash
# 1. Design the feature
/sc:design "User authentication system"

# 2. Implement with iteration
/sc:implement --loop "Add user login endpoint"

# 3. Test
/sc:test --coverage

# 4. Document
/sc:document --api
```

### Bug Fixing

```bash
# 1. Analyze the issue
/sc:analyze --deep src/problematic_module.py

# 2. Implement fix with PAL review
/sc:implement --pal-review "Fix null pointer in user validation"

# 3. Verify
/sc:test
```

### Code Quality

```bash
# 1. Analyze codebase
/sc:analyze --deep --risk src/

# 2. Improve code quality
/sc:improve --refactor src/legacy_module.py

# 3. Generate documentation
/sc:document --readme
```

## Key Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `/sc:implement` | Code implementation | `/sc:implement "Add caching"` |
| `/sc:test` | Run tests | `/sc:test --coverage` |
| `/sc:analyze` | Code analysis | `/sc:analyze --deep src/` |
| `/sc:design` | Architecture design | `/sc:design --diagram "API"` |
| `/sc:document` | Documentation | `/sc:document --api` |
| `/sc:improve` | Code enhancement | `/sc:improve --refactor` |
| `/sc:workflow` | Multi-step tasks | `/sc:workflow --steps` |
| `/sc:explain` | Code explanation | `/sc:explain src/complex.py` |

## Essential Flags

| Flag | Effect |
|------|--------|
| `--loop [n]` | Iterate until quality threshold (max 5) |
| `--pal-review` | Request code review from PAL MCP |
| `--safe` | Enable strict guardrails |
| `--think 3` | Deep reasoning mode |
| `--consensus` | Multi-model voting |

## Quality Thresholds

| Score | Band | Meaning |
|-------|------|---------|
| 90-100 | production_ready | Auto-approve |
| 75-89 | needs_attention | Accept with suggestions |
| 50-74 | iterate | Continue improving |
| < 50 | iterate | Needs significant work |

## Behavioral Modes

SuperClaude adapts its behavior based on context:

- **Normal**: Balanced output, standard workflows
- **Task Management**: Detailed tracking for complex tasks
- **Token Efficiency**: Compressed output when context is limited

Trigger token efficiency with `--uc` flag.

## Next Steps

1. **Read the full documentation**: See `Docs/User-Guide/`
2. **Explore agents**: Check `SuperClaude/Agents/Extended/`
3. **Customize commands**: Edit `SuperClaude/Commands/`
4. **Configure quality**: Adjust `config/superclaud.yaml`

## Getting Help

- Run `/sc:explain` for detailed explanations
- Check `Docs/` for comprehensive guides
- See `tests/` for usage examples
