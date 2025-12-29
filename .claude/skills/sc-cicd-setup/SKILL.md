# SC:CICD-Setup Skill

Bootstrap GitHub CI/CD workflows and pre-commit hooks for any project using battle-tested templates.

## When to Use

- Setting up a new project with CI/CD
- Adding GitHub Actions to an existing repository
- Standardizing CI/CD across multiple projects
- User requests: "set up CI", "add GitHub Actions", "configure pipelines"

## Invocation

```
/sc:cicd-setup [--lang <language>] [--yes] [--force] [--minimal|--full]
```

## Flags

| Flag | Description |
|------|-------------|
| `--lang` | Force project language: python, node, go, rust |
| `--yes` | Accept defaults, skip confirmation prompts |
| `--force` | Overwrite existing workflow files (backs up originals) |
| `--minimal` | Only essential CI workflow |
| `--full` | All workflows including publish/release |

## Supported Languages

### Python
- CI: ruff lint/format, mypy, pytest, coverage
- Security: CodeQL, pip-audit, Bandit
- AI Review: Claude-powered PR review
- Publish: PyPI release automation
- Pre-commit: ruff, mypy, bandit hooks

### Node.js
- CI: ESLint, tests, build
- Security: npm audit, CodeQL
- AI Review: Claude-powered PR review
- Publish: npm publish automation
- Pre-commit: ESLint, Prettier hooks

### Go
- CI: go vet, golangci-lint, tests, cross-compile
- Security: gosec, govulncheck, CodeQL
- AI Review: Claude-powered PR review
- Pre-commit: gofmt, golangci-lint hooks

### Rust
- CI: rustfmt, clippy, tests, cross-compile
- Security: cargo-audit, cargo-deny
- AI Review: Claude-powered PR review
- Publish: crates.io automation
- Pre-commit: rustfmt, clippy hooks

## Workflow

1. **Detect** project type from manifest files
2. **Configure** based on flags (minimal/full/default)
3. **Validate** check for existing files
4. **Present** summary of what will be created
5. **Confirm** (skip with `--yes`)
6. **Generate** workflow files from templates
7. **Report** next steps

## Examples

```bash
# Auto-detect and setup (interactive)
/sc:cicd-setup

# Python project, non-interactive
/sc:cicd-setup --lang python --yes

# Full suite with publish workflow
/sc:cicd-setup --full

# Minimal CI only
/sc:cicd-setup --minimal

# Force overwrite existing
/sc:cicd-setup --force
```

## Post-Setup

After running, you may need to:
1. Add `ANTHROPIC_API_KEY` secret for AI review
2. Run `pre-commit install` to enable hooks
3. Add `PYPI_API_TOKEN` / `NPM_TOKEN` / `CARGO_REGISTRY_TOKEN` for publishing
4. Add `CODECOV_TOKEN` for coverage reporting

## Template Location

Templates are in `templates/workflows/{python,node,go,rust}/`:
- `ci.yml.j2` - Main CI pipeline
- `security.yml.j2` - Security scanning
- `ai-review.yml.j2` - AI code review
- `publish.yml.j2` - Package publishing
- `pre-commit-config.yaml.j2` - Pre-commit hooks
