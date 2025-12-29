---
name: cicd-setup
description: "Set up GitHub CI/CD workflows and pre-commit hooks for any project"
category: utility
complexity: standard
mcp-servers: []
personas: [devops-engineer, build-engineer]
requires_evidence: false
aliases: [cicd-init, pipeline-setup, actions-setup]
flags:
  - name: lang
    description: Force project language (auto-detected if not specified)
    type: string
    options: [python, node, go, rust]
  - name: yes
    description: Accept defaults, skip confirmation prompts
    type: boolean
    default: false
  - name: force
    description: Overwrite existing workflow files (backs up originals)
    type: boolean
    default: false
  - name: minimal
    description: Only essential CI workflow (no security, AI review)
    type: boolean
    default: false
  - name: full
    description: All workflows including publish/release automation
    type: boolean
    default: false
---

# /sc:cicd-setup - CI/CD Setup

Bootstrap GitHub CI/CD workflows and pre-commit hooks for any project using battle-tested templates from SuperClaude.

## Triggers
- Setting up a new project with CI/CD
- Adding GitHub Actions to an existing repository
- Standardizing CI/CD across multiple projects
- Requests for "set up CI", "add GitHub Actions", "configure pipelines"

## Usage
```
/sc:cicd-setup [--lang <language>] [--yes] [--force] [--minimal|--full]
```

## Behavioral Flow

1. **Detect**: Identify project type from manifest files
   - `pyproject.toml` / `requirements.txt` → Python
   - `package.json` → Node.js
   - `go.mod` → Go
   - `Cargo.toml` → Rust

2. **Configure**: Determine what to generate
   - Default: CI + Security + AI Review + Pre-commit
   - `--minimal`: CI only
   - `--full`: Add publish/release workflows

3. **Validate**: Check for existing files
   - List conflicts if workflows exist
   - Require `--force` to overwrite (creates backups)

4. **Present**: Show summary of what will be created
   - File paths and purposes
   - Configuration values (versions, branches, thresholds)

5. **Confirm**: Ask for user approval (skip with `--yes`)

6. **Generate**: Create workflow files from templates
   - Render Jinja2 templates with project-specific values
   - Create `.github/workflows/` directory if needed
   - Create `.pre-commit-config.yaml` in project root

7. **Report**: Summarize what was created
   - List created files
   - Next steps (e.g., add secrets, install pre-commit)

## Tool Coordination
- **Read**: Detect project type, read existing configs
- **Write**: Generate workflow files
- **Bash**: Create directories, backup existing files
- **Glob**: Find existing workflow files

## What Gets Created

### Python Projects
| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Quality gates (ruff, mypy), tests, coverage |
| `.github/workflows/security.yml` | CodeQL, pip-audit, Bandit |
| `.github/workflows/ai-review.yml` | Claude-powered PR review |
| `.github/workflows/publish.yml` | PyPI release (with `--full`) |
| `.pre-commit-config.yaml` | Local linting hooks |

### Node.js Projects
| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | ESLint, tests, build |
| `.github/workflows/security.yml` | npm audit, CodeQL |
| `.github/workflows/ai-review.yml` | Claude-powered PR review |
| `.github/workflows/publish.yml` | npm publish (with `--full`) |
| `.pre-commit-config.yaml` | ESLint, Prettier hooks |

### Go Projects
| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | go vet, tests, build |
| `.github/workflows/security.yml` | gosec, CodeQL |
| `.github/workflows/ai-review.yml` | Claude-powered PR review |
| `.pre-commit-config.yaml` | gofmt, golangci-lint |

### Rust Projects
| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | clippy, tests, build |
| `.github/workflows/security.yml` | cargo-audit, CodeQL |
| `.github/workflows/ai-review.yml` | Claude-powered PR review |
| `.github/workflows/publish.yml` | crates.io publish (with `--full`) |
| `.pre-commit-config.yaml` | rustfmt, clippy |

## Configuration Defaults

### Python
- Python versions: 3.10, 3.11, 3.12
- Coverage threshold: 90%
- Linting: ruff (lint + format)
- Type checking: mypy

### Node.js
- Node versions: 18, 20, 22
- Package manager: auto-detected (npm/yarn/pnpm)
- Linting: ESLint + Prettier

### Go
- Go versions: 1.21, 1.22
- Linting: golangci-lint

### Rust
- Channel: stable
- MSRV: 1.70
- Linting: clippy

## Examples

### Auto-detect and Setup (Interactive)
```
/sc:cicd-setup
```

### Python Project (Non-interactive)
```
/sc:cicd-setup --lang python --yes
```

### Full Suite with Publish Workflow
```
/sc:cicd-setup --full
```

### Minimal CI Only
```
/sc:cicd-setup --minimal
```

### Force Overwrite Existing
```
/sc:cicd-setup --force
```

## Post-Setup Steps

After running `/sc:cicd-setup`, you may need to:

1. **For AI Review**: Add `ANTHROPIC_API_KEY` secret to repository settings
2. **For Pre-commit**: Run `pre-commit install` to enable hooks
3. **For Publish** (Python): Add `PYPI_API_TOKEN` secret
4. **For Publish** (npm): Add `NPM_TOKEN` secret
5. **For Codecov**: Add `CODECOV_TOKEN` secret (optional)

## Boundaries

**Will:**
- Generate standardized CI/CD workflows from templates
- Detect project type automatically
- Back up existing files before overwriting
- Create necessary directories

**Will Not:**
- Configure repository secrets (security concern)
- Modify existing workflow files without `--force`
- Generate workflows for unsupported languages
- Execute generated workflows (that's GitHub's job)
