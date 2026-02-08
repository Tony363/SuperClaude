# SuperClaude Skills Directory

This directory contains Claude Code skills that integrate with SuperClaude.

Skill files are located in subdirectories with a `SKILL.md` frontmatter format similar to agents.

## Structure

```
.claude/skills/
  agent-data-engineer/
    SKILL.md
  agent-fullstack-developer/
    SKILL.md
  sc-analyze/
    SKILL.md
  sc-implement/
    SKILL.md
    scripts/
      select_agent.py
      run_tests.py
      evidence_gate.py
      skill_learn.py
      loop_entry.py
  ...
```

Skills are automatically discovered by the dashboard inventory scanner.

## Skill Types

### Agent Skills (8)

Specialized personas mapped to agent prompts:
- agent-data-engineer
- agent-fullstack-developer
- agent-kubernetes-specialist
- agent-ml-engineer
- agent-performance-engineer
- agent-react-specialist
- agent-security-engineer
- agent-technical-writer

### Command Skills (19)

Workflow implementations for `/sc:` commands:
- sc-analyze
- sc-brainstorm
- sc-build
- sc-cicd-setup
- sc-design
- sc-document
- sc-estimate
- sc-explain
- sc-git
- sc-implement
- sc-improve
- sc-mcp
- sc-pr-fix
- sc-principles
- sc-readme
- sc-tdd
- sc-test
- sc-workflow
- sc-worktree

### Utility Skills (3)

User interaction and learning:
- ask - Single-select questions
- ask-multi - Multi-select questions
- learned - Auto-learned patterns from successful executions

## Skill Format

Each skill follows this structure:

```markdown
---
name: skill-name
description: Brief description of what the skill does
triggers: [keyword1, keyword2]
---

# Skill Name

[Skill prompt and instructions...]
```

## Adding New Skills

1. Create a new directory under `.claude/skills/`
2. Add a `SKILL.md` file with proper frontmatter
3. Optionally add `scripts/` directory for Python tools
4. Restart Claude Code to load the new skill

## Deprecated Skills

106 deprecated skills from previous versions are archived in `DEPRECATED/` directory.
