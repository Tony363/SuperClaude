# SuperClaude Framework

> ⚠️ **IMPORTANT NOTICE**: This project is currently in **BETA** (v4.1.0). Agent system partially implemented. See [ROADMAP.md](ROADMAP.md) for planned features and timeline.

<div align="center">

![Version](https://img.shields.io/badge/version-4.1.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-purple)
![Status](https://img.shields.io/badge/status-beta-yellow)

**🚀 AI-Enhanced Development Framework for Claude Code**

**[Installation](#installation)** • **[Documentation](Docs/)** • **[Contributing](#contributing)**

</div>

---

## 📑 Table of Contents

- [Overview](#overview)
- [Current Features](#current-features)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Support](#support)

---

## Overview

SuperClaude is an AI-enhanced development framework for Claude Code that provides a modular architecture for building intelligent automation tools. This framework serves as a foundation for advanced Claude Desktop integrations.

## Current Features

### ✅ Implemented (v4.1.0)

- **📦 Python Package Structure** - Installable via pip with CLI entry point
- **🔧 Installation System** - Basic setup, update, uninstall, and backup commands
- **📁 Modular Architecture** - Organized structure for agent and MCP integrations
- **🖥️ CLI Framework** - Subcommand system with logging and configuration support
- **📝 Configuration Templates** - MCP server configurations for common services
- **🧪 Testing Framework** - pytest suite with 16+ passing tests
- **📊 Version Management** - Robust version handling with multiple fallbacks

### 🚧 In Development (v5.0.0-alpha)

These features are partially implemented:

- **🤖 Agent System** (60% complete):
  - ✅ Agent discovery from 135+ markdown definitions
  - ✅ Context-based agent selection with scoring
  - ✅ Generic agent execution for markdown configs
  - ✅ Dynamic loading with LRU cache
  - ⚠️ 1/5 core Python agents implemented
  - ⚠️ CLI integration pending
- **📋 Dynamic Loading**:
  - ✅ TRIGGERS.json configuration system
  - ⚠️ Not yet integrated with CLI
- **🔌 MCP Integration**: Templates ready, integration pending
- **📝 Command System**: Structure created, implementation pending

## Installation

### Requirements

- Python 3.8+
- pip package manager

### From PyPI

```bash
pip install SuperClaude
SuperClaude --version  # Should show 4.1.0
```

### From Source

```bash
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude_Framework
pip install -e ".[dev]"
```

## Usage

### Basic Commands

```bash
# Check version
SuperClaude --version

# Install framework components (limited functionality)
SuperClaude install

# Update installation
SuperClaude update

# Backup configuration
SuperClaude backup --create

# Uninstall
SuperClaude uninstall
```

### Command Options

- `--verbose, -v` - Enable verbose logging
- `--quiet, -q` - Suppress output except errors
- `--dry-run` - Simulate operation without changes
- `--force` - Skip confirmation prompts
- `--help` - Show help information

## Project Structure

```
SuperClaude_Framework/
├── SuperClaude/           # Main package
│   ├── __init__.py       # Package initialization
│   ├── __main__.py       # CLI entry point
│   ├── Agents/           # Agent system (planned)
│   ├── Commands/         # Command implementations (planned)
│   ├── Core/             # Core functionality (planned)
│   ├── MCP/              # MCP configurations (templates only)
│   │   └── configs/      # Server configuration files
│   └── Modes/            # Behavioral modes (planned)
├── setup/                 # Installation system
│   ├── cli/              # CLI command implementations
│   ├── components/       # Component installers
│   ├── data/             # Configuration data
│   ├── services/         # Service utilities
│   └── utils/            # Helper utilities
├── scripts/              # Utility scripts
├── Docs/                 # Documentation
├── pyproject.toml        # Package configuration
├── VERSION               # Version file (4.0.9)
└── README.md             # This file
```

## Roadmap

### Version 5.0 (Q1 2025)
- [ ] Basic agent system with 5-10 core agents
- [ ] Simple dynamic loading proof of concept
- [ ] MCP server integration helpers
- [ ] Improved CLI with more commands

### Version 6.0 (Q2 2025)
- [ ] Full agent system (14+ core agents)
- [ ] Advanced dynamic loading with caching
- [ ] Multi-model routing support
- [ ] Quality scoring system
- [ ] Behavioral modes

See [ROADMAP.md](ROADMAP.md) for detailed plans and progress tracking.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repository
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude_Framework

# Install in development mode
pip install -e ".[dev]"

# Run tests (when available)
pytest tests/
```

### Areas for Contribution

- **Implementation** - Help implement planned features
- **Documentation** - Improve docs and examples
- **Testing** - Add test coverage
- **Bug Fixes** - Fix issues and improve stability

## Support

- **Issues**: [GitHub Issues](https://github.com/SuperClaude-Org/SuperClaude_Framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SuperClaude-Org/SuperClaude_Framework/discussions)

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Maintainers

- **Anton Knoery** ([@NomenAK](https://github.com/NomenAK)) - Lead Developer
- **Mithun Gowda B** ([@mithun50](https://github.com/mithun50)) - Core Contributor

---

<div align="center">

**SuperClaude Framework v4.0.9**

*Building the future of AI-enhanced development*

</div>