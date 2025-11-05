# Installation Guide

Follow this quick procedure to set up the SuperClaude Framework on a fresh
machine. All commands assume a POSIX shell.

## 1. Prerequisites

- Python 3.11+ with `pip` available on your PATH
- Node.js 18+ (for CLI shim linting and optional tooling)
- Git

## 2. Clone the Repository

```bash
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework.git
cd SuperClaude_Framework
```

## 3. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## 4. Install Python Dependencies

```bash
pip install -e .[dev]
```

This installs the core framework, test dependencies, and tooling such as
Black/Ruff.

## 5. Install Node Tooling (Optional)

```bash
npm install
```

The Node dependencies power linting for the CLI wrapper and any TypeScript
artefacts that commands generate.

## 6. Verify the Installation

```bash
python -m SuperClaude --help
python benchmarks/run_benchmarks.py --suite smoke
```

The first command confirms the CLI entrypoint is wired; the second executes the
smoke benchmark suite and prints timing information.

## 7. Configure API Keys (Optional)

To enable live consensus with provider models, export the relevant keys before
running commands:

```bash
export OPENAI_API_KEY=...         # required for GPT models
export ANTHROPIC_API_KEY=...      # required for Claude models
export GOOGLE_API_KEY=...         # required for Gemini models
export XAI_API_KEY=...            # required for Grok models
```

Without these keys the consensus layer will return explicit errors so you know
additional configuration is required.

You are now ready to run `/sc:*` commands locally.
